class DominioError(Exception):
    """Base de los errores de negocio de NovaRent."""


class DatosInvalidos(DominioError):
    """Dato mal formado (fechas, montos, categorias)."""


class TransicionInvalida(DominioError):
    """El estado actual no permite la accion pedida."""


class ReglaNegocioViolada(DominioError):
    """Se incumple una regla del BRD."""


class SinDisponibilidad(ReglaNegocioViolada):
    """BR-02 / RN-03: no hay lugar en la categoria para esas fechas."""


class RequisitosIncompletos(ReglaNegocioViolada):
    """RN-02: faltan requisitos para entregar."""

    def __init__(self, faltantes):
        self.faltantes = list(faltantes)
        super().__init__("RN-02: " + "; ".join(self.faltantes))
