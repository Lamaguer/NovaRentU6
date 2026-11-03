"""Casos de uso de NovaRent. Cada metodo abre una Unit of Work (una transaccion):
si el dominio lanza una excepcion, no se guarda nada (rollback).

Devuelven diccionarios simples para que la API / interfaz los serialicen sin conocer el dominio.
"""
from datetime import datetime
from uuid import uuid4

from src.domain.errores import DatosInvalidos, SinDisponibilidad, TransicionInvalida
from src.domain.politicas import TARIFARIO
from src.domain.renta import Renta
from src.domain.reservacion import Reservacion
from src.domain.valores import Dinero, EstadoFisico, PeriodoRenta, RequisitosEntrega, nivel
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
            "cargos": cargos, "total_cargos": str(total_cargos)}


def vista_vehiculo(v):
    return {"id": v.id, "categoria": v.categoria, "sucursal_id": v.sucursal_id,
            "estado": v.estado}


class ServicioNovaRent:
    def __init__(self, session_factory, tarifario=TARIFARIO):
        self._factory = session_factory
        self.tarifario = tarifario

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
