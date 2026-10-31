from src.domain.cargos import CalculadoraCargos
from src.domain.errores import (
    DatosInvalidos,
    RequisitosIncompletos,
    SinDisponibilidad,
    TransicionInvalida,
)
from src.domain.eventos import Evento
from src.domain.specifications import (
    SolicitudExtension,
    SolicitudUpgrade,
    extension_permitida,
    faltantes_entrega,
    requisitos_completos,
    upgrade_permitido,
)
from src.domain.valores import comparar_estados


class Renta:
    """Agregado raiz del ciclo PENDIENTE -> ENTREGADO -> DEVUELTO."""

    def __init__(self, id_renta, reservacion):
        self.id_renta, self.folio = id_renta, reservacion.folio
        self.cliente_id, self.periodo = reservacion.cliente_id, reservacion.periodo
        self.tarifa_diaria_original = reservacion.tarifa_diaria  # RN-01: no cambia
        self.categoria_reservada = self.categoria_asignada = reservacion.categoria
        self.vehiculo_id = self.checklist_inicial = self.estado_final = None
        self.estado = "PENDIENTE"
        self.cargos, self.eventos = [], []

    @classmethod
    def desde_reservacion(cls, id_renta, reservacion):
        reservacion.marcar_cumplida()
        return cls(id_renta, reservacion)

    @property
    def total_renta(self):
        return self.tarifa_diaria_original.por(self.periodo.dias)

    def _evento(self, nombre, **datos):
        self.eventos.append(Evento(nombre, self.id_renta, datos))

    def aplicar_upgrade(self, categoria_destino, unidades_disponibles):  # RN-01 / US-14
        if self.estado != "PENDIENTE":
            raise TransicionInvalida("El upgrade se autoriza antes de la entrega")
        sol = SolicitudUpgrade(self.categoria_reservada, categoria_destino, unidades_disponibles)
        if not upgrade_permitido.is_satisfied_by(sol):
            raise SinDisponibilidad("RN-01: solo hay upgrade sin unidades y a categoria superior")
        self.categoria_asignada = categoria_destino
        self._evento("UpgradeAplicado", de=self.categoria_reservada, a=categoria_destino)

    def entregar(self, requisitos, vehiculo):  # RN-02 / US-04..US-07
        if self.estado != "PENDIENTE":
            raise TransicionInvalida("Solo una renta PENDIENTE puede entregarse")
        if not requisitos_completos.is_satisfied_by(requisitos):
            raise RequisitosIncompletos(faltantes_entrega(requisitos))
        if vehiculo.categoria != self.categoria_asignada:
            raise DatosInvalidos("El vehiculo no es de la categoria asignada")
        vehiculo.rentar()
        self.vehiculo_id, self.checklist_inicial = vehiculo.id, requisitos.checklist
        self.estado = "ENTREGADO"
        self._evento("VehiculoEntregado", vehiculo=vehiculo.id)

    def extender(self, nueva_fin, inventario):  # RN-03 / US-08
        if self.estado != "ENTREGADO":
            raise TransicionInvalida("Solo una renta ENTREGADA puede extenderse")
        sol = SolicitudExtension(self.folio, self.periodo, nueva_fin, inventario)
        if not extension_permitida.is_satisfied_by(sol):
            if nueva_fin <= self.periodo.fin:
                raise DatosInvalidos("La extension debe ampliar la fecha de devolucion")
            raise SinDisponibilidad("RN-03: no hay disponibilidad para la extension")
        nuevo = self.periodo.extendido_a(nueva_fin)
        inventario.extender(self.folio, nuevo)
        self.periodo = nuevo
        self._evento("RentaExtendida", nueva_fin=nueva_fin.isoformat())

    def registrar_devolucion(self, estado_final, retorno, vehiculo, calculadora=None):
        if self.estado != "ENTREGADO":
            raise TransicionInvalida("Solo una renta ENTREGADA puede devolverse")
        if estado_final.kilometraje < self.checklist_inicial.kilometraje:
            raise DatosInvalidos("El kilometraje final no puede ser menor al inicial")
        calculadora = calculadora or CalculadoraCargos()
        self.cargos = calculadora.calcular(self.periodo, self.checklist_inicial,
                                           estado_final, retorno)
        vehiculo.devolver()
        self.estado_final, self.estado = estado_final, "DEVUELTO"
        self._evento("VehiculoDevuelto", **comparar_estados(self.checklist_inicial, estado_final))
        if self.cargos:
            total = sum(c.monto.monto for c in self.cargos)
            self._evento("CargoGenerado", total=str(total))
        return self.cargos
