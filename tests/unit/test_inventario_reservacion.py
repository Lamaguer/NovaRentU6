from datetime import date

import pytest

from src.domain.errores import DatosInvalidos, SinDisponibilidad, TransicionInvalida
from src.domain.inventario import InventarioCategoria
from src.domain.reservacion import Reservacion
from src.domain.valores import Dinero, PeriodoRenta

D = date


def res(folio, periodo, cat="ECONOMICO"):
    return Reservacion(folio, "C-01", "MTY-CENTRO", cat, periodo, Dinero(500))


def test_us02_us03_confirmar_genera_evento_y_bloquea_lugar(inventario, periodo):
    r = res("F-1", periodo)
    r.confirmar(inventario)
    assert r.estado == "CONFIRMADA"
    assert r.eventos[0].nombre == "ReservacionConfirmada"
    assert inventario.lugares_disponibles(D(2026, 11, 12)) == 1


def test_br02_sobreventa_rechazada():
    inv = InventarioCategoria("MTY-CENTRO", "ECONOMICO", 1)
    p = PeriodoRenta(D(2026, 11, 10), D(2026, 11, 15))
    res("F-1", p).confirmar(inv)
    with pytest.raises(SinDisponibilidad, match="BR-02"):
        res("F-2", p).confirmar(inv)


def test_br02_limite_reserva_que_empieza_el_dia_de_devolucion():
    inv = InventarioCategoria("MTY-CENTRO", "ECONOMICO", 1)
    res("F-1", PeriodoRenta(D(2026, 11, 10), D(2026, 11, 15))).confirmar(inv)
    res("F-2", PeriodoRenta(D(2026, 11, 15), D(2026, 11, 18))).confirmar(inv)


def test_br02_ocupacion_se_mide_dia_por_dia():
    inv = InventarioCategoria("MTY-CENTRO", "ECONOMICO", 2)
    res("A", PeriodoRenta(D(2026, 11, 10), D(2026, 11, 13))).confirmar(inv)
    res("B", PeriodoRenta(D(2026, 11, 13), D(2026, 11, 16))).confirmar(inv)
    res("C", PeriodoRenta(D(2026, 11, 11), D(2026, 11, 15))).confirmar(inv)  # traslapa con 2, nunca el mismo dia


def test_reservacion_no_se_confirma_dos_veces(inventario, periodo):
    r = res("F-1", periodo)
    r.confirmar(inventario)
    with pytest.raises(TransicionInvalida):
        r.confirmar(inventario)


def test_reservacion_rechaza_inventario_de_otra_categoria(periodo):
    with pytest.raises(DatosInvalidos):
        res("F-1", periodo, "SUV").confirmar(InventarioCategoria("MTY-CENTRO", "ECONOMICO", 1))


def test_inventario_validaciones_y_liberar(inventario, periodo):
    inventario.apartar("F-1", periodo)
    with pytest.raises(DatosInvalidos):
        inventario.apartar("F-1", periodo)
    with pytest.raises(DatosInvalidos):
        inventario.extender("NO-EXISTE", periodo)
    with pytest.raises(DatosInvalidos):
        InventarioCategoria("S", "ECONOMICO", -1)
    inventario.liberar("F-1")
    assert inventario.lugares_disponibles(D(2026, 11, 11)) == 2


def test_periodo_invalido_y_categoria_desconocida():
    with pytest.raises(DatosInvalidos):
        PeriodoRenta(D(2026, 11, 5), D(2026, 11, 5))
    with pytest.raises(DatosInvalidos):
        InventarioCategoria("S", "LIMUSINA", 1)
