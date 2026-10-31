from datetime import date
from decimal import Decimal

import pytest

from src.domain.inventario import InventarioCategoria
from src.domain.renta import Renta
from src.domain.reservacion import Reservacion
from src.domain.valores import Dinero, EstadoFisico, PeriodoRenta, RequisitosEntrega
from src.domain.vehiculo import Vehiculo

D = date


@pytest.fixture
def periodo():
    return PeriodoRenta(D(2026, 11, 10), D(2026, 11, 15))


@pytest.fixture
def inventario():
    return InventarioCategoria("MTY-CENTRO", "ECONOMICO", 2)


@pytest.fixture
def checklist():
    return EstadoFisico(8, 1000, ("rayon puerta",))


@pytest.fixture
def requisitos_ok(checklist):
    return RequisitosEntrega(True, True, True, checklist)


@pytest.fixture
def vehiculo():
    return Vehiculo("V-001", "ECONOMICO", "MTY-CENTRO")


@pytest.fixture
def renta(periodo, inventario):
    r = Reservacion("F-001", "C-01", "MTY-CENTRO", "ECONOMICO", periodo, Dinero(Decimal(500)))
    r.confirmar(inventario)
    return Renta.desde_reservacion("R-001", r)
