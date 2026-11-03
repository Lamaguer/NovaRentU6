"""Tablas (SQLAlchemy 2.0). Los agregados del dominio NO dependen de estas clases."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InventarioRow(Base):
    __tablename__ = "inventarios"
    sucursal_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    categoria: Mapped[str] = mapped_column(String(20), primary_key=True)
    capacidad: Mapped[int] = mapped_column(Integer)


class ApartadoRow(Base):
    """Lugar apartado por un folio dentro de un inventario (intervalo [inicio, fin))."""
    __tablename__ = "apartados"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sucursal_id", "categoria"],
            ["inventarios.sucursal_id", "inventarios.categoria"],
        ),
    )
    folio: Mapped[str] = mapped_column(String(20), primary_key=True)
    sucursal_id: Mapped[str] = mapped_column(String(30))
    categoria: Mapped[str] = mapped_column(String(20))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)


class ReservacionRow(Base):
    __tablename__ = "reservaciones"
    folio: Mapped[str] = mapped_column(String(20), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(30))
    sucursal_id: Mapped[str] = mapped_column(String(30))
    categoria: Mapped[str] = mapped_column(String(20))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    tarifa_diaria: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    estado: Mapped[str] = mapped_column(String(20))


class VehiculoRow(Base):
    __tablename__ = "vehiculos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    categoria: Mapped[str] = mapped_column(String(20))
    sucursal_id: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(20))


class RentaRow(Base):
    __tablename__ = "rentas"
    id_renta: Mapped[str] = mapped_column(String(30), primary_key=True)
    folio: Mapped[str] = mapped_column(
        String(20), ForeignKey("reservaciones.folio"), unique=True)
    cliente_id: Mapped[str] = mapped_column(String(30))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    tarifa_diaria_original: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    categoria_reservada: Mapped[str] = mapped_column(String(20))
    categoria_asignada: Mapped[str] = mapped_column(String(20))
    vehiculo_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("vehiculos.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(20))
    # Checklist inicial (estado fisico a la entrega)
    ci_combustible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ci_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ci_danos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Estado final (a la devolucion)
    ef_combustible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ef_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ef_danos: Mapped[list | None] = mapped_column(JSON, nullable=True)


class CargoRow(Base):
    __tablename__ = "cargos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_renta: Mapped[str] = mapped_column(String(30), ForeignKey("rentas.id_renta"))
    concepto: Mapped[str] = mapped_column(String(20))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    detalle: Mapped[str] = mapped_column(String(200))


class EventoRow(Base):
    """Bitacora de Domain Events (base para KPIs y auditoria)."""
    __tablename__ = "eventos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agregado_id: Mapped[str] = mapped_column(String(40), index=True)
    nombre: Mapped[str] = mapped_column(String(50))
    datos: Mapped[dict] = mapped_column(JSON)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime)
