"""Tarifario y politicas. VALORES FICTICIOS de demostracion (el BRD no los incluye)."""
from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal


@dataclass(frozen=True)
class Tarifario:
    tarifa_diaria: dict = field(default_factory=lambda: {
        "ECONOMICO": Decimal(500), "COMPACTO": Decimal(650),
        "SUV": Decimal(900), "PREMIUM": Decimal(1400)})
    hora_limite_devolucion: time = time(12, 0)   # SUPUESTO
    cargo_por_hora_retraso: Decimal = Decimal(150)
    km_incluidos_por_dia: int = 200
    cargo_por_km_extra: Decimal = Decimal(4)
    precio_litro: Decimal = Decimal(30)
    litros_tanque: Decimal = Decimal(45)
    cargo_por_dano_nuevo: Decimal = Decimal(500)


TARIFARIO = Tarifario()
