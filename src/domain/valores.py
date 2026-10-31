from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from src.domain.errores import DatosInvalidos

CATEGORIAS = ("ECONOMICO", "COMPACTO", "SUV", "PREMIUM")  # de menor a mayor


def nivel(categoria):
    if categoria not in CATEGORIAS:
        raise DatosInvalidos(f"Categoria desconocida: {categoria}")
    return CATEGORIAS.index(categoria)


@dataclass(frozen=True)
class Dinero:
    monto: Decimal
    moneda: str = "MXN"

    def __post_init__(self):
        m = Decimal(self.monto)
        if not m.is_finite() or m < 0:
            raise DatosInvalidos("Monto invalido")
        object.__setattr__(self, "monto", m.quantize(Decimal("0.01"), ROUND_HALF_UP))

    @classmethod
    def cero(cls):
        return cls(Decimal(0))

    def __add__(self, otro):
        return Dinero(self.monto + otro.monto, self.moneda)

    def por(self, factor):
        return Dinero(self.monto * Decimal(factor), self.moneda)


@dataclass(frozen=True)
class PeriodoRenta:
    inicio: date
    fin: date  # intervalo semiabierto [inicio, fin)

    def __post_init__(self):
        if self.fin <= self.inicio:
            raise DatosInvalidos("La fecha fin debe ser posterior al inicio")

    @property
    def dias(self):
        return (self.fin - self.inicio).days

    def dias_cubiertos(self):
        return [self.inicio + timedelta(days=i) for i in range(self.dias)]

    def extendido_a(self, nueva_fin):
        return PeriodoRenta(self.inicio, nueva_fin)


@dataclass(frozen=True)
class EstadoFisico:
    """Estado inicial / final del vehiculo (glosario D011, D012)."""
    combustible_octavos: int
    kilometraje: int
    danos: tuple = ()

    def __post_init__(self):
        if not 0 <= self.combustible_octavos <= 8 or self.kilometraje < 0:
            raise DatosInvalidos("Estado fisico invalido")


def comparar_estados(inicial, final):
    """US-09: contraste entre entrega y devolucion."""
    return {
        "km_recorridos": final.kilometraje - inicial.kilometraje,
        "octavos_faltantes": max(0, inicial.combustible_octavos - final.combustible_octavos),
        "danos_nuevos": tuple(d for d in final.danos if d not in inicial.danos),
    }


@dataclass(frozen=True)
class RequisitosEntrega:
    """Glosario D023: identificacion, licencia, pago y checklist inicial."""
    identificacion_valida: bool = False
    licencia_vigente: bool = False
    pago_autorizado: bool = False
    checklist: EstadoFisico | None = None
