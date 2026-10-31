from src.domain.errores import TransicionInvalida
from src.domain.eventos import Evento
from src.domain.valores import nivel

TRANSICIONES = {
    ("DISPONIBLE", "rentar"): "RENTADO",
    ("RENTADO", "devolver"): "EN_LIMPIEZA",
    ("EN_LIMPIEZA", "terminar_limpieza"): "DISPONIBLE",
}


class Vehiculo:
    """Maquina de estados de la unidad fisica (BRD alcance, US-12, US-13)."""

    def __init__(self, id_vehiculo, categoria, sucursal_id, estado="DISPONIBLE"):
        nivel(categoria)
        self.id, self.categoria, self.sucursal_id, self.estado = (
            id_vehiculo, categoria, sucursal_id, estado)
        self.eventos = []

    def _transicion(self, accion):
        nuevo = TRANSICIONES.get((self.estado, accion))
        if nuevo is None:
            raise TransicionInvalida(f"No se puede '{accion}' un vehiculo {self.estado}")
        self.estado = nuevo

    def rentar(self):
        self._transicion("rentar")

    def devolver(self):
        self._transicion("devolver")
        self.eventos.append(Evento("VehiculoEnLimpieza", self.id))  # US-12 / BR-04

    def terminar_limpieza(self):
        self._transicion("terminar_limpieza")
        self.eventos.append(Evento("VehiculoDisponible", self.id))  # US-13
