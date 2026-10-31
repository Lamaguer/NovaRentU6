from src.domain.errores import DatosInvalidos, TransicionInvalida
from src.domain.eventos import Evento
from src.domain.valores import nivel


class Reservacion:
    """US-01, US-02, US-03: garantiza una CATEGORIA, no una unidad fisica."""

    def __init__(self, folio, cliente_id, sucursal_id, categoria, periodo, tarifa_diaria):
        nivel(categoria)
        self.folio, self.cliente_id, self.sucursal_id = folio, cliente_id, sucursal_id
        self.categoria, self.periodo, self.tarifa_diaria = categoria, periodo, tarifa_diaria
        self.estado = "PENDIENTE"
        self.eventos = []

    def confirmar(self, inventario):
        if self.estado != "PENDIENTE":
            raise TransicionInvalida("Solo una reservacion PENDIENTE puede confirmarse")
        if (inventario.sucursal_id, inventario.categoria) != (self.sucursal_id, self.categoria):
            raise DatosInvalidos("Inventario de otra sucursal o categoria")
        inventario.apartar(self.folio, self.periodo)
        self.estado = "CONFIRMADA"
        self.eventos.append(Evento("ReservacionConfirmada", self.folio,
                                   {"categoria": self.categoria}))

    def marcar_cumplida(self):
        if self.estado != "CONFIRMADA":
            raise TransicionInvalida("Solo una reservacion CONFIRMADA puede cumplirse")
        self.estado = "CUMPLIDA"
