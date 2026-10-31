from datetime import date, datetime
from decimal import Decimal

import pytest

from src.domain.errores import (
    DatosInvalidos,
    RequisitosIncompletos,
    SinDisponibilidad,
    TransicionInvalida,
)
from src.domain.valores import EstadoFisico, RequisitosEntrega
from src.domain.vehiculo import Vehiculo

D = date


def nombres(x):
    return [e.nombre for e in x.eventos]


# ---- RN-02 / US-04..US-07 ----
def test_us04_us07_entrega_completa(renta, requisitos_ok, vehiculo):
    renta.entregar(requisitos_ok, vehiculo)
    assert renta.estado == "ENTREGADO" and vehiculo.estado == "RENTADO"
    assert nombres(renta) == ["VehiculoEntregado"]
    assert renta.checklist_inicial.kilometraje == 1000


def test_rn02_entrega_bloqueada_informa_faltantes(renta, vehiculo):
    with pytest.raises(RequisitosIncompletos) as e:
        renta.entregar(RequisitosEntrega(True, False, True, None), vehiculo)
    assert len(e.value.faltantes) == 2
    assert renta.estado == "PENDIENTE" and vehiculo.estado == "DISPONIBLE"


def test_entrega_con_vehiculo_de_otra_categoria(renta, requisitos_ok):
    with pytest.raises(DatosInvalidos):
        renta.entregar(requisitos_ok, Vehiculo("V-9", "SUV", "MTY-CENTRO"))


def test_no_se_entrega_dos_veces(renta, requisitos_ok, vehiculo):
    renta.entregar(requisitos_ok, vehiculo)
    with pytest.raises(TransicionInvalida):
        renta.entregar(requisitos_ok, vehiculo)


# ---- RN-01 / US-14 ----
def test_us14_upgrade_conserva_tarifa_y_entrega_categoria_superior(renta, requisitos_ok):
    renta.aplicar_upgrade("SUV", unidades_disponibles=0)
    assert renta.categoria_asignada == "SUV"
    assert renta.tarifa_diaria_original.monto == Decimal("500.00")
    renta.entregar(requisitos_ok, Vehiculo("V-SUV", "SUV", "MTY-CENTRO"))
    assert nombres(renta) == ["UpgradeAplicado", "VehiculoEntregado"]
    assert renta.total_renta.monto == Decimal("2500.00")


def test_rn01_upgrade_rechazado_si_hay_unidades(renta):
    with pytest.raises(SinDisponibilidad, match="RN-01"):
        renta.aplicar_upgrade("SUV", unidades_disponibles=1)
    assert renta.categoria_asignada == "ECONOMICO"


def test_rn01_upgrade_a_categoria_inferior_o_igual(renta):
    for destino in ("ECONOMICO",):
        with pytest.raises(SinDisponibilidad):
            renta.aplicar_upgrade(destino, 0)


def test_rn01_upgrade_solo_antes_de_entregar(renta, requisitos_ok, vehiculo):
    renta.entregar(requisitos_ok, vehiculo)
    with pytest.raises(TransicionInvalida):
        renta.aplicar_upgrade("SUV", 0)


# ---- RN-03 / US-08 ----
def test_us08_extension_con_disponibilidad(renta, requisitos_ok, vehiculo, inventario):
    renta.entregar(requisitos_ok, vehiculo)
    renta.extender(D(2026, 11, 18), inventario)
    assert renta.periodo.fin == D(2026, 11, 18)
    assert inventario.apartados["F-001"].fin == D(2026, 11, 18)
    assert nombres(renta)[-1] == "RentaExtendida"


def test_rn03_extension_rechazada_sin_capacidad(renta, requisitos_ok, vehiculo, inventario):
    from src.domain.reservacion import Reservacion
    from src.domain.valores import Dinero, PeriodoRenta
    renta.entregar(requisitos_ok, vehiculo)
    for f in ("X", "Y"):
        Reservacion(f, "C-2", "MTY-CENTRO", "ECONOMICO",
                    PeriodoRenta(D(2026, 11, 15), D(2026, 11, 20)), Dinero(500)).confirmar(inventario)
    with pytest.raises(SinDisponibilidad, match="RN-03"):
        renta.extender(D(2026, 11, 16), inventario)
    assert renta.periodo.fin == D(2026, 11, 15)


def test_rn03_limite_otra_reserva_inicia_en_la_nueva_fecha_fin(renta, requisitos_ok, vehiculo, inventario):
    from src.domain.reservacion import Reservacion
    from src.domain.valores import Dinero, PeriodoRenta
    renta.entregar(requisitos_ok, vehiculo)
    for f in ("X", "Y"):
        Reservacion(f, "C-2", "MTY-CENTRO", "ECONOMICO",
                    PeriodoRenta(D(2026, 11, 17), D(2026, 11, 20)), Dinero(500)).confirmar(inventario)
    renta.extender(D(2026, 11, 17), inventario)  # termina justo cuando empiezan las otras


def test_rn03_extension_que_no_amplia_o_antes_de_entregar(renta, requisitos_ok, vehiculo, inventario):
    with pytest.raises(TransicionInvalida):
        renta.extender(D(2026, 11, 18), inventario)
    renta.entregar(requisitos_ok, vehiculo)
    with pytest.raises(DatosInvalidos):
        renta.extender(D(2026, 11, 15), inventario)


# ---- Devolucion / BR-03 / US-09..US-13 ----
def test_us10_us11_devolucion_con_cargos_y_limpieza(renta, requisitos_ok, vehiculo):
    renta.entregar(requisitos_ok, vehiculo)
    final = EstadoFisico(6, 2300, ("rayon puerta", "espejo roto"))
    cargos = renta.registrar_devolucion(final, datetime(2026, 11, 15, 14, 0), vehiculo)
    assert {c.concepto for c in cargos} == {"RETRASO", "KILOMETRAJE", "COMBUSTIBLE", "DANOS"}
    assert renta.estado == "DEVUELTO" and vehiculo.estado == "EN_LIMPIEZA"
    assert nombres(renta)[-2:] == ["VehiculoDevuelto", "CargoGenerado"]
    assert vehiculo.eventos[0].nombre == "VehiculoEnLimpieza"


def test_devolucion_sin_cargos_no_genera_evento_de_cargo(renta, requisitos_ok, vehiculo):
    renta.entregar(requisitos_ok, vehiculo)
    cargos = renta.registrar_devolucion(EstadoFisico(8, 1500, ("rayon puerta",)),
                                        datetime(2026, 11, 15, 11, 0), vehiculo)
    assert cargos == [] and "CargoGenerado" not in nombres(renta)


def test_devolucion_validaciones(renta, requisitos_ok, vehiculo):
    with pytest.raises(TransicionInvalida):
        renta.registrar_devolucion(EstadoFisico(8, 1500), datetime(2026, 11, 15, 11), vehiculo)
    renta.entregar(requisitos_ok, vehiculo)
    with pytest.raises(DatosInvalidos):
        renta.registrar_devolucion(EstadoFisico(8, 900), datetime(2026, 11, 15, 11), vehiculo)
