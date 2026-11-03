"""Fixtures de integracion. Por defecto SQLite en memoria; con TEST_DATABASE_URL se prueba
contra PostgreSQL real (p. ej. el servicio `db` de docker compose)."""
import os

import pytest

from src.application.servicios import ServicioNovaRent
from src.infrastructure.db import (
    URL_PRUEBAS,
    Base,
    crear_engine,
    crear_session_factory,
    crear_tablas,
)
from src.infrastructure.seed import sembrar


@pytest.fixture
def engine():
    eng = crear_engine(os.getenv("TEST_DATABASE_URL", URL_PRUEBAS))
    Base.metadata.drop_all(eng)
    crear_tablas(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return crear_session_factory(engine)


@pytest.fixture
def servicio(session_factory):
    sembrar(session_factory, sucursales=("MTY-CENTRO",),
            capacidad={"ECONOMICO": 2, "COMPACTO": 1, "SUV": 1})
    return ServicioNovaRent(session_factory)
