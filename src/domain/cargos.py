import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.politicas import TARIFARIO
from src.domain.valores import Dinero, comparar_estados


@dataclass(frozen=True)
class Cargo:
    concepto: str
    monto: Dinero
    detalle: str


class CalculadoraCargos:
    """BR-03 Motor de cargos (US-10, US-11)."""

    def __init__(self, tarifario=TARIFARIO):
        self.t = tarifario

    def por_retraso(self, periodo, retorno):
        limite = datetime.combine(periodo.fin, self.t.hora_limite_devolucion)
        if retorno <= limite:
            return Dinero.cero(), 0
        horas = math.ceil((retorno - limite).total_seconds() / 3600)
        return Dinero(self.t.cargo_por_hora_retraso).por(horas), horas

    def por_kilometraje(self, periodo, km):
        extra = max(0, km - self.t.km_incluidos_por_dia * periodo.dias)
        return Dinero(self.t.cargo_por_km_extra).por(extra), extra

    def por_combustible(self, octavos):
        litros = Decimal(octavos) * self.t.litros_tanque / 8
        return Dinero(litros * self.t.precio_litro), litros

    def por_danos(self, nuevos):
        return Dinero(self.t.cargo_por_dano_nuevo).por(len(nuevos))

    def calcular(self, periodo, inicial, final, retorno):
        c = comparar_estados(inicial, final)
        cargos = []
        monto, h = self.por_retraso(periodo, retorno)
        if h:
            cargos.append(Cargo("RETRASO", monto, f"{h} h de retraso"))
        monto, extra = self.por_kilometraje(periodo, c["km_recorridos"])
        if extra:
            cargos.append(Cargo("KILOMETRAJE", monto, f"{extra} km excedidos"))
        monto, litros = self.por_combustible(c["octavos_faltantes"])
        if litros:
            cargos.append(Cargo("COMBUSTIBLE", monto, f"{litros} L faltantes"))
        if c["danos_nuevos"]:
            cargos.append(Cargo("DANOS", self.por_danos(c["danos_nuevos"]),
                                ", ".join(c["danos_nuevos"])))
        return cargos
