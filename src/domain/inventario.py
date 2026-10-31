from src.domain.errores import DatosInvalidos, SinDisponibilidad
from src.domain.valores import nivel


class InventarioCategoria:
    """Glosario D022: capacidad de una categoria en una sucursal y lugares apartados por dia."""

    def __init__(self, sucursal_id, categoria, capacidad):
        nivel(categoria)
        if capacidad < 0:
            raise DatosInvalidos("Capacidad invalida")
        self.sucursal_id, self.categoria, self.capacidad = sucursal_id, categoria, capacidad
        self.apartados = {}  # folio -> PeriodoRenta

    def ocupacion(self, dia, excluir=None):
        return sum(1 for f, p in self.apartados.items()
                   if f != excluir and p.inicio <= dia < p.fin)

    def lugares_disponibles(self, dia):
        return self.capacidad - self.ocupacion(dia)

    def hay_capacidad(self, periodo, excluir=None):
        return all(self.ocupacion(d, excluir) < self.capacidad for d in periodo.dias_cubiertos())

    def apartar(self, folio, periodo):  # US-03 / BR-02
        if folio in self.apartados:
            raise DatosInvalidos("El folio ya aparto lugar")
        if not self.hay_capacidad(periodo):
            raise SinDisponibilidad("BR-02: la categoria no tiene disponibilidad")
        self.apartados[folio] = periodo

    def extender(self, folio, nuevo_periodo):  # RN-03
        if folio not in self.apartados:
            raise DatosInvalidos("Folio sin lugar apartado")
        if not self.hay_capacidad(nuevo_periodo, excluir=folio):
            raise SinDisponibilidad("RN-03: no hay disponibilidad para la extension")
        self.apartados[folio] = nuevo_periodo

    def liberar(self, folio):
        self.apartados.pop(folio, None)
