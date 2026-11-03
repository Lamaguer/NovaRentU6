"""Conexion a la base de datos (PostgreSQL en produccion, SQLite en memoria en pruebas)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.models import Base

URL_PRUEBAS = "sqlite+pysqlite:///:memory:"


def normalizar_url(url):
    """Los proveedores de hosting entregan postgres:// o postgresql://; usamos psycopg 3."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


def crear_engine(url=None):
    url = normalizar_url(url or os.getenv("DATABASE_URL", URL_PRUEBAS))
    if url.startswith("sqlite") and (":memory:" in url or url == "sqlite://"):
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def crear_tablas(engine):
    Base.metadata.create_all(engine)


def crear_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
