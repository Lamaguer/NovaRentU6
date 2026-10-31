from datetime import date, datetime
from decimal import Decimal

import pytest

from src.domain.cargos import CalculadoraCargos
from src.domain.errores import DatosInvalidos, TransicionInvalida
from src.domain.valores import Dinero, EstadoFisico, PeriodoRenta, comparar_estados
from src.domain.vehiculo import Vehiculo

P = PeriodoRenta(date(2026, 11, 10), date(2026, 11, 15))  # 5 dias, limite 15-nov 12:00
C = CalculadoraCargos()


def test_us10_retraso_exacto_no_cobra_y_un_minuto_cobra_una_hora():
    assert C.por_retraso(P, datetime(2026, 11, 15, 12, 0))[0].monto == Decimal("0.00")
    assert C.por_retraso(P, datetime(2026, 11, 15, 12, 1))[0].monto == Decimal("150.00")
    assert C.por_retraso(P, datetime(2026, 11, 15, 14, 30))[1] == 3


def test_us10_kilometraje_limite_1000_incluidos():
    assert C.por_kilometraje(P, 1000)[0].monto == Decimal("0.00")
    assert C.por_kilometraje(P, 1001)[0].monto == Decimal("4.00")


def test_us11_combustible_octavo_es_168_75():
    assert C.por_combustible(1)[0].monto == Decimal("168.75")
    assert C.por_combustible(0)[0].monto == Decimal("0.00")


def test_us09_comparar_y_danos_nuevos():
    ini, fin = EstadoFisico(8, 100, ("a",)), EstadoFisico(7, 160, ("a", "b"))
    assert comparar_estados(ini, fin) == {
        "km_recorridos": 60, "octavos_faltantes": 1, "danos_nuevos": ("b",)}
    assert C.por_danos(("b",)).monto == Decimal("500.00")


def test_estado_fisico_y_dinero_invalidos():
    with pytest.raises(DatosInvalidos):
        EstadoFisico(9, 0)
    with pytest.raises(DatosInvalidos):
        Dinero(Decimal(-1))
    assert (Dinero(1) + Dinero(2)).monto == Decimal("3.00")


def test_us12_us13_ciclo_del_vehiculo():
    v = Vehiculo("V-1", "SUV", "S")
    v.rentar(); v.devolver()
    assert v.estado == "EN_LIMPIEZA"
    v.terminar_limpieza()
    assert v.estado == "DISPONIBLE"
    assert [e.nombre for e in v.eventos] == ["VehiculoEnLimpieza", "VehiculoDisponible"]


def test_vehiculo_transiciones_invalidas():
    v = Vehiculo("V-1", "SUV", "S")
    for accion in (v.devolver, v.terminar_limpieza):
        with pytest.raises(TransicionInvalida):
            accion()
    v.rentar()
    with pytest.raises(TransicionInvalida):
        v.rentar()
