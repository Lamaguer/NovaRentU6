"""Specification (AND / OR / NOT) para las reglas RN-01, RN-02, RN-03 y BR-02."""
from dataclasses import dataclass
from functools import reduce

from src.domain.valores import nivel


class Specification:
    def is_satisfied_by(self, candidato):
        raise NotImplementedError

    def __and__(self, otra):
        return _Compuesta(lambda a, b: a and b, self, otra)

    def __or__(self, otra):
        return _Compuesta(lambda a, b: a or b, self, otra)

    def __invert__(self):
        return _Not(self)


class _Compuesta(Specification):
    def __init__(self, op, izq, der):
        self.op, self.izq, self.der = op, izq, der

    def is_satisfied_by(self, c):
        return self.op(self.izq.is_satisfied_by(c), self.der.is_satisfied_by(c))


class _Not(Specification):
    def __init__(self, spec):
        self.spec = spec

    def is_satisfied_by(self, c):
        return not self.spec.is_satisfied_by(c)


# ---- RN-02 requisitos de entrega (candidato: RequisitosEntrega) ----
class IdentificacionSpec(Specification):
    def is_satisfied_by(self, r):
        return r.identificacion_valida


class LicenciaSpec(Specification):
    def is_satisfied_by(self, r):
        return r.licencia_vigente


class PagoSpec(Specification):
    def is_satisfied_by(self, r):
        return r.pago_autorizado


class ChecklistSpec(Specification):
    def is_satisfied_by(self, r):
        return r.checklist is not None


_REQUISITOS = [
    (IdentificacionSpec(), "Falta la identificacion oficial"),
    (LicenciaSpec(), "Falta la licencia vigente"),
    (PagoSpec(), "Falta el pago / deposito autorizado"),
    (ChecklistSpec(), "Falta el checklist inicial del vehiculo"),
]
requisitos_completos = reduce(lambda a, b: a & b, [s for s, _ in _REQUISITOS])


def faltantes_entrega(requisitos):
    """US-07: lista legible de lo que falta."""
    return [msg for spec, msg in _REQUISITOS if not spec.is_satisfied_by(requisitos)]


# ---- RN-03 extension (candidato: SolicitudExtension) ----
@dataclass
class SolicitudExtension:
    folio: str
    periodo_actual: object
    nueva_fin: object
    inventario: object


class NuevaFechaPosteriorSpec(Specification):
    def is_satisfied_by(self, s):
        return s.nueva_fin > s.periodo_actual.fin


class SinConflictoSpec(Specification):
    def is_satisfied_by(self, s):
        nuevo = s.periodo_actual.extendido_a(s.nueva_fin)
        return s.inventario.hay_capacidad(nuevo, excluir=s.folio)


extension_permitida = NuevaFechaPosteriorSpec() & SinConflictoSpec()


# ---- RN-01 upgrade (candidato: SolicitudUpgrade) ----
@dataclass
class SolicitudUpgrade:
    categoria_reservada: str
    categoria_destino: str
    unidades_disponibles: int  # unidades fisicas libres en la categoria reservada


class SinUnidadesSpec(Specification):
    def is_satisfied_by(self, s):
        return s.unidades_disponibles == 0


class CategoriaSuperiorSpec(Specification):
    def is_satisfied_by(self, s):
        return nivel(s.categoria_destino) > nivel(s.categoria_reservada)


upgrade_permitido = SinUnidadesSpec() & CategoriaSuperiorSpec()
