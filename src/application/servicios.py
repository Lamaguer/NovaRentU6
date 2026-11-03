"""Casos de uso de NovaRent. Cada metodo abre una Unit of Work (una transaccion):
si el dominio lanza una excepcion, no se guarda nada (rollback).

Devuelven diccionarios simples para que la API / interfaz los serialicen sin conocer el dominio.
"""
from datetime import datetime
from uuid import uuid4

from src.domain.errores import (
    DatosInvalidos,
    NoEncontrado,
    RequisitosIncompletos,
    SinDisponibilidad,
    TransicionInvalida,
)
from src.domain.politicas import TARIFARIO
from src.domain.renta import Renta
from src.domain.reservacion import Reservacion
from src.domain.specifications import faltantes_entrega
from src.domain.valores import (
    Dinero,
    EstadoFisico,
    PeriodoRenta,
    RequisitosEntrega,
    comparar_estados,
    nivel,
)
from src.infrastructure.pasarela import PasarelaPagoSimulada
from src.infrastructure.seed import NOMBRES
from src.infrastructure.unit_of_work import UnitOfWork


def _estado_fisico(datos):
    if datos is None:
        return None
    return EstadoFisico(int(datos["combustible_octavos"]), int(datos["kilometraje"]),
                        tuple(datos.get("danos") or ()))


def vista_reservacion(r):
    return {"folio": r.folio, "cliente_id": r.cliente_id, "sucursal_id": r.sucursal_id,
            "categoria": r.categoria, "inicio": r.periodo.inicio.isoformat(),
            "fin": r.periodo.fin.isoformat(), "dias": r.periodo.dias,
            "tarifa_diaria": str(r.tarifa_diaria.monto), "estado": r.estado}


def _fisico_dict(e):
    if e is None:
        return None
    return {"combustible_octavos": e.combustible_octavos, "kilometraje": e.kilometraje,
            "danos": list(e.danos)}


def _comparacion(r):  # US-09
    if r.checklist_inicial is None or r.estado_final is None:
        return None
    c = comparar_estados(r.checklist_inicial, r.estado_final)
    return {**c, "danos_nuevos": list(c["danos_nuevos"])}


def vista_renta(r):
    cargos = [{"concepto": c.concepto, "monto": str(c.monto.monto), "detalle": c.detalle}
              for c in r.cargos]
    total_cargos = sum((c.monto.monto for c in r.cargos), start=Dinero.cero().monto)
    return {"id_renta": r.id_renta, "folio": r.folio, "cliente_id": r.cliente_id,
            "estado": r.estado, "vehiculo_id": r.vehiculo_id,
            "categoria_reservada": r.categoria_reservada,
            "categoria_asignada": r.categoria_asignada,
            "inicio": r.periodo.inicio.isoformat(), "fin": r.periodo.fin.isoformat(),
            "tarifa_diaria": str(r.tarifa_diaria_original.monto),
            "total_renta": str(r.total_renta.monto),
            "cargos": cargos, "total_cargos": str(total_cargos),
            "checklist_inicial": _fisico_dict(r.checklist_inicial),
            "estado_final": _fisico_dict(r.estado_final), "comparacion": _comparacion(r)}


def vista_vehiculo(v):
    return {"id": v.id, "categoria": v.categoria, "sucursal_id": v.sucursal_id,
            "estado": v.estado}


class ServicioNovaRent:
    def __init__(self, session_factory, tarifario=TARIFARIO, pasarela=None):
        self._factory = session_factory
        self.tarifario = tarifario
        self.pasarela = pasarela or PasarelaPagoSimulada()

    def _uow(self):
        return UnitOfWork(self._factory)

    # ---- Reservaciones (US-01..US-03, BR-02) ----
    def reservar(self, cliente_id, sucursal_id, categoria, inicio, fin,
                 folio=None, confirmar=True):
        """Crea la reservacion y, si confirmar=True, aparta el lugar en la misma transaccion.
        Si no hay disponibilidad (BR-02) no se guarda nada."""
        nivel(categoria)  # valida la categoria antes de consultar el tarifario
        periodo = PeriodoRenta(inicio, fin)
        folio = folio or f"F-{uuid4().hex[:8].upper()}"
        with self._uow() as uow:
            if uow.reservaciones.existe(folio):
                raise DatosInvalidos(f"El folio {folio} ya existe")
            res = Reservacion(folio, cliente_id, sucursal_id, categoria, periodo,
                              Dinero(self.tarifario.tarifa_diaria[categoria]))
            if confirmar:
                inv = uow.inventarios.obtener(sucursal_id, categoria, bloquear=True)
                res.confirmar(inv)
                uow.inventarios.guardar(inv)
            uow.reservaciones.guardar(res)
            uow.commit()
            return vista_reservacion(res)

    def confirmar_reservacion(self, folio):
        with self._uow() as uow:
            res = uow.reservaciones.obtener(folio)
            inv = uow.inventarios.obtener(res.sucursal_id, res.categoria, bloquear=True)
            res.confirmar(inv)
            uow.inventarios.guardar(inv)
            uow.reservaciones.guardar(res)
            uow.commit()
            return vista_reservacion(res)

    def obtener_reservacion(self, folio):
        with self._uow() as uow:
            return vista_reservacion(uow.reservaciones.obtener(folio))

    def listar_reservaciones(self):
        with self._uow() as uow:
            return [vista_reservacion(r) for r in uow.reservaciones.listar()]

    def disponibilidad(self, sucursal_id, categoria, dia):
        with self._uow() as uow:
            inv = uow.inventarios.obtener(sucursal_id, categoria)
            return {"sucursal_id": sucursal_id, "categoria": categoria,
                    "dia": dia.isoformat(), "capacidad": inv.capacidad,
                    "disponibles": inv.lugares_disponibles(dia)}

    def sucursales(self):
        with self._uow() as uow:
            ids = sorted({i.sucursal_id for i in uow.inventarios.listar()})
            return [{"id": i, "nombre": NOMBRES.get(i, i)} for i in ids]

    def disponibilidad_periodo(self, sucursal_id, inicio, fin):  # US-01
        """Solo las categorias con al menos un lugar libre TODOS los dias del periodo."""
        periodo = PeriodoRenta(inicio, fin)
        with self._uow() as uow:
            invs = [i for i in uow.inventarios.listar() if i.sucursal_id == sucursal_id]
            if not invs:
                raise NoEncontrado(f"Sucursal {sucursal_id} no existe")
            salida = []
            for inv in sorted(invs, key=lambda i: nivel(i.categoria)):
                lugares = min(inv.lugares_disponibles(d) for d in periodo.dias_cubiertos())
                if lugares > 0:
                    tarifa = Dinero(self.tarifario.tarifa_diaria[inv.categoria])
                    salida.append({"categoria": inv.categoria, "lugares": lugares,
                                   "tarifa_diaria": str(tarifa.monto),
                                   "total": str(tarifa.por(periodo.dias).monto)})
            return salida

    # ---- Rentas (US-04..US-14) ----
    def iniciar_renta(self, folio):
        """La reservacion CONFIRMADA pasa a CUMPLIDA y nace la renta PENDIENTE de entrega."""
        with self._uow() as uow:
            res = uow.reservaciones.obtener(folio)
            renta = Renta.desde_reservacion(uow.rentas.siguiente_id(), res)
            uow.reservaciones.guardar(res)
            uow.rentas.guardar(renta)
            uow.commit()
            return vista_renta(renta)

    def obtener_renta(self, id_renta):
        with self._uow() as uow:
            return vista_renta(uow.rentas.obtener(id_renta))

    def listar_rentas(self):
        with self._uow() as uow:
            return [vista_renta(r) for r in uow.rentas.listar()]

    def aplicar_upgrade(self, id_renta, categoria_destino):  # RN-01 / US-14
        with self._uow() as uow:
            renta = uow.rentas.obtener(id_renta)
            res = uow.reservaciones.obtener(renta.folio)
            libres = uow.vehiculos.contar_disponibles(res.sucursal_id, renta.categoria_reservada)
            renta.aplicar_upgrade(categoria_destino, libres)
            uow.rentas.guardar(renta)
            uow.commit()
            return vista_renta(renta)

    def entregar(self, id_renta, identificacion_valida, licencia_vigente, pago_autorizado,
                 checklist, vehiculo_id=None):  # RN-02 / US-04..US-07
        """checklist: dict {combustible_octavos, kilometraje, danos} o None.
        Sin vehiculo_id se asigna la primera unidad DISPONIBLE de la categoria asignada."""
        with self._uow() as uow:
            renta = uow.rentas.obtener(id_renta)
            if vehiculo_id:
                vehiculo = uow.vehiculos.obtener(vehiculo_id)
            else:
                res = uow.reservaciones.obtener(renta.folio)
                vehiculo = uow.vehiculos.disponible(res.sucursal_id, renta.categoria_asignada)
                if vehiculo is None:
                    raise SinDisponibilidad(
                        f"No hay vehiculo DISPONIBLE de categoria {renta.categoria_asignada}")
            requisitos = RequisitosEntrega(identificacion_valida, licencia_vigente,
                                           pago_autorizado, _estado_fisico(checklist))
            renta.entregar(requisitos, vehiculo)
            uow.vehiculos.guardar(vehiculo)
            uow.rentas.guardar(renta)
            uow.commit()
            return vista_renta(renta)

    def entregar_con_tarjeta(self, id_renta, identificacion_valida, licencia_vigente, tarjeta,
                             checklist):  # RN-02 + US-05 (pasarela simulada)
        """Cobra el deposito ANTES de entregar: nunca hay renta ENTREGADA sin pago autorizado."""
        faltantes = faltantes_entrega(RequisitosEntrega(
            identificacion_valida, licencia_vigente, bool(tarjeta), _estado_fisico(checklist)))
        pago = False
        if identificacion_valida and licencia_vigente and tarjeta and not faltantes:
            total = Dinero(self.obtener_renta(id_renta)["total_renta"])
            pago = self.pasarela.retener_deposito(tarjeta, total)
        if faltantes or not pago:
            raise RequisitosIncompletos(faltantes or ["Falta el pago / deposito autorizado"])
        return self.entregar(id_renta, identificacion_valida, licencia_vigente, pago, checklist)

    def extender(self, id_renta, nueva_fin):  # RN-03 / US-08
        with self._uow() as uow:
            renta = uow.rentas.obtener(id_renta)
            res = uow.reservaciones.obtener(renta.folio)
            inv = uow.inventarios.obtener(res.sucursal_id, renta.categoria_reservada,
                                          bloquear=True)
            renta.extender(nueva_fin, inv)
            uow.inventarios.guardar(inv)
            uow.rentas.guardar(renta)
            uow.commit()
            return vista_renta(renta)

    def devolver(self, id_renta, estado_final, retorno=None):  # US-09..US-12
        """estado_final: dict {combustible_octavos, kilometraje, danos}."""
        with self._uow() as uow:
            renta = uow.rentas.obtener(id_renta)
            vehiculo = uow.vehiculos.obtener(renta.vehiculo_id) if renta.vehiculo_id else None
            final = _estado_fisico(estado_final)
            if final is None:
                raise DatosInvalidos("Falta el estado final del vehiculo")
            if vehiculo is None:  # renta aun no entregada: la maquina de estados lo rechaza
                raise TransicionInvalida("Solo una renta ENTREGADA puede devolverse")
            renta.registrar_devolucion(final, retorno or datetime.now(), vehiculo)
            uow.vehiculos.guardar(vehiculo)
            uow.rentas.guardar(renta)
            uow.commit()
            return vista_renta(renta)

    # ---- Vehiculos (US-12, US-13) ----
    def terminar_limpieza(self, id_vehiculo):
        with self._uow() as uow:
            vehiculo = uow.vehiculos.obtener(id_vehiculo)
            vehiculo.terminar_limpieza()
            uow.vehiculos.guardar(vehiculo)
            uow.commit()
            return vista_vehiculo(vehiculo)

    def listar_vehiculos(self):
        with self._uow() as uow:
            return [vista_vehiculo(v) for v in uow.vehiculos.listar()]

    def listar_eventos(self, agregado_id=None):
        with self._uow() as uow:
            return [{"agregado_id": e.agregado_id, "nombre": e.nombre, "datos": e.datos,
                     "ocurrido_en": e.ocurrido_en.isoformat()}
                    for e in uow.eventos.listar(agregado_id)]

    # ---- KPIs (US-15, BRD seccion 8) ----
    def kpis(self):
        with self._uow() as uow:
            sobreventas = 0
            for inv in uow.inventarios.listar():
                dias = {d for p in inv.apartados.values() for d in p.dias_cubiertos()}
                sobreventas += sum(1 for d in dias if inv.ocupacion(d) > inv.capacidad)

            en_limpieza, tiempos = {}, []
            for e in uow.eventos.listar():
                if e.nombre == "VehiculoEnLimpieza":
                    en_limpieza[e.agregado_id] = e.ocurrido_en
                elif e.nombre == "VehiculoDisponible" and e.agregado_id in en_limpieza:
                    tiempos.append((e.ocurrido_en - en_limpieza.pop(e.agregado_id))
                                   .total_seconds() / 60)
            cargos = uow.rentas.cargos_por_concepto()
            return {
                "sobreventas": sobreventas,  # meta BRD: 0
                "minutos_devolucion_a_disponible": (
                    round(sum(tiempos) / len(tiempos), 2) if tiempos else None),
                "cobros_por_danos": {"cantidad": cargos.get("DANOS", {}).get("cantidad", 0),
                                     "total": str(cargos.get("DANOS", {}).get(
                                         "total", Dinero.cero().monto))},
                "cargos_por_concepto": {k: {"cantidad": v["cantidad"], "total": str(v["total"])}
                                        for k, v in cargos.items()},
                "rentas_por_estado": uow.rentas.conteo_por_estado(),
                "vehiculos_por_estado": uow.vehiculos.conteo_por_estado(),
                "eventos": uow.eventos.conteo_por_nombre(),
            }
