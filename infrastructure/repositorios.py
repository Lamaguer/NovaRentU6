"""Repositorios: traducen entre filas SQL y agregados del dominio.

Al cargar, los agregados llegan con `eventos = []`; al guardar se persisten los eventos
pendientes en la bitacora y se vacia la lista (asi no se duplican).
"""
from sqlalchemy import func

from src.domain.cargos import Cargo
from src.domain.errores import NoEncontrado
from src.domain.inventario import InventarioCategoria
from src.domain.renta import Renta
from src.domain.reservacion import Reservacion
from src.domain.valores import Dinero, EstadoFisico, PeriodoRenta
from src.domain.vehiculo import Vehiculo
from src.infrastructure.models import (
    ApartadoRow,
    CargoRow,
    EventoRow,
    InventarioRow,
    RentaRow,
    ReservacionRow,
    VehiculoRow,
)


def _guardar_eventos(session, agregado):
    for e in agregado.eventos:
        session.add(EventoRow(agregado_id=e.agregado_id, nombre=e.nombre,
                              datos=_json(e.datos), ocurrido_en=e.ocurrido_en))
    agregado.eventos = []


def _json(datos):
    """Los eventos llevan tuplas/fechas; se guardan como JSON simple."""
    def conv(v):
        if isinstance(v, (tuple, list)):
            return [conv(x) for x in v]
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, (int, float, str, bool)) or v is None:
            return v
        return str(v)
    return conv(datos)


def _estado_fisico(comb, km, danos):
    if km is None:
        return None
    return EstadoFisico(comb, km, tuple(danos or ()))


class RepositorioInventarios:
    def __init__(self, session):
        self.s = session

    def obtener(self, sucursal_id, categoria, bloquear=False):
        """bloquear=True hace SELECT ... FOR UPDATE (PostgreSQL): serializa reservaciones
        concurrentes sobre la misma categoria y garantiza 0 sobreventas (BR-02)."""
        fila = self.s.get(InventarioRow, (sucursal_id, categoria), with_for_update=bloquear)
        if fila is None:
            raise NoEncontrado(f"Inventario {sucursal_id}/{categoria} no existe")
        inv = InventarioCategoria(sucursal_id, categoria, fila.capacidad)
        apartados = (self.s.query(ApartadoRow)
                     .filter_by(sucursal_id=sucursal_id, categoria=categoria).all())
        inv.apartados = {a.folio: PeriodoRenta(a.inicio, a.fin) for a in apartados}
        return inv

    def listar(self):
        filas = self.s.query(InventarioRow).order_by(
            InventarioRow.sucursal_id, InventarioRow.categoria).all()
        return [self.obtener(f.sucursal_id, f.categoria) for f in filas]

    def guardar(self, inv):
        fila = self.s.get(InventarioRow, (inv.sucursal_id, inv.categoria))
        if fila is None:
            self.s.add(InventarioRow(sucursal_id=inv.sucursal_id, categoria=inv.categoria,
                                     capacidad=inv.capacidad))
        else:
            fila.capacidad = inv.capacidad
        self.s.flush()
        existentes = {a.folio: a for a in self.s.query(ApartadoRow).filter_by(
            sucursal_id=inv.sucursal_id, categoria=inv.categoria).all()}
        for folio, fila_a in existentes.items():
            if folio not in inv.apartados:
                self.s.delete(fila_a)
        for folio, p in inv.apartados.items():
            if folio in existentes:
                existentes[folio].inicio, existentes[folio].fin = p.inicio, p.fin
            else:
                self.s.add(ApartadoRow(folio=folio, sucursal_id=inv.sucursal_id,
                                       categoria=inv.categoria, inicio=p.inicio, fin=p.fin))


class RepositorioReservaciones:
    def __init__(self, session):
        self.s = session

    def obtener(self, folio):
        f = self.s.get(ReservacionRow, folio)
        if f is None:
            raise NoEncontrado(f"Reservacion {folio} no existe")
        r = Reservacion(f.folio, f.cliente_id, f.sucursal_id, f.categoria,
                        PeriodoRenta(f.inicio, f.fin), Dinero(f.tarifa_diaria))
        r.estado = f.estado
        return r

    def existe(self, folio):
        return self.s.get(ReservacionRow, folio) is not None

    def listar(self):
        return [self.obtener(f.folio) for f in
                self.s.query(ReservacionRow).order_by(ReservacionRow.folio).all()]

    def guardar(self, r):
        f = self.s.get(ReservacionRow, r.folio)
        if f is None:
            f = ReservacionRow(folio=r.folio)
            self.s.add(f)
        f.cliente_id, f.sucursal_id, f.categoria = r.cliente_id, r.sucursal_id, r.categoria
        f.inicio, f.fin = r.periodo.inicio, r.periodo.fin
        f.tarifa_diaria, f.estado = r.tarifa_diaria.monto, r.estado
        _guardar_eventos(self.s, r)


class RepositorioVehiculos:
    def __init__(self, session):
        self.s = session

    def obtener(self, id_vehiculo):
        f = self.s.get(VehiculoRow, id_vehiculo)
        if f is None:
            raise NoEncontrado(f"Vehiculo {id_vehiculo} no existe")
        return Vehiculo(f.id, f.categoria, f.sucursal_id, f.estado)

    def listar(self):
        return [Vehiculo(f.id, f.categoria, f.sucursal_id, f.estado)
                for f in self.s.query(VehiculoRow).order_by(VehiculoRow.id).all()]

    def disponible(self, sucursal_id, categoria):
        """Primera unidad DISPONIBLE de la categoria, o None."""
        f = (self.s.query(VehiculoRow)
             .filter_by(sucursal_id=sucursal_id, categoria=categoria, estado="DISPONIBLE")
             .order_by(VehiculoRow.id).first())
        return None if f is None else Vehiculo(f.id, f.categoria, f.sucursal_id, f.estado)

    def conteo_por_estado(self):
        filas = self.s.query(VehiculoRow.estado, func.count()).group_by(VehiculoRow.estado).all()
        return {estado: n for estado, n in filas}

    def contar_disponibles(self, sucursal_id, categoria):
        return (self.s.query(VehiculoRow)
                .filter_by(sucursal_id=sucursal_id, categoria=categoria, estado="DISPONIBLE")
                .count())

    def guardar(self, v):
        f = self.s.get(VehiculoRow, v.id)
        if f is None:
            f = VehiculoRow(id=v.id)
            self.s.add(f)
        f.categoria, f.sucursal_id, f.estado = v.categoria, v.sucursal_id, v.estado
        _guardar_eventos(self.s, v)


class RepositorioRentas:
    def __init__(self, session):
        self.s = session

    def _hidratar(self, f):
        r = Renta.__new__(Renta)  # reconstruccion sin ejecutar __init__ (no hay reservacion)
        r.id_renta, r.folio, r.cliente_id = f.id_renta, f.folio, f.cliente_id
        r.periodo = PeriodoRenta(f.inicio, f.fin)
        r.tarifa_diaria_original = Dinero(f.tarifa_diaria_original)
        r.categoria_reservada, r.categoria_asignada = f.categoria_reservada, f.categoria_asignada
        r.vehiculo_id, r.estado = f.vehiculo_id, f.estado
        r.checklist_inicial = _estado_fisico(f.ci_combustible, f.ci_km, f.ci_danos)
        r.estado_final = _estado_fisico(f.ef_combustible, f.ef_km, f.ef_danos)
        cargos = self.s.query(CargoRow).filter_by(id_renta=f.id_renta).order_by(CargoRow.id).all()
        r.cargos = [Cargo(c.concepto, Dinero(c.monto), c.detalle) for c in cargos]
        r.eventos = []
        return r

    def obtener(self, id_renta):
        f = self.s.get(RentaRow, id_renta)
        if f is None:
            raise NoEncontrado(f"Renta {id_renta} no existe")
        return self._hidratar(f)

    def obtener_por_folio(self, folio):
        f = self.s.query(RentaRow).filter_by(folio=folio).first()
        if f is None:
            raise NoEncontrado(f"No hay renta para el folio {folio}")
        return self._hidratar(f)

    def listar(self):
        return [self._hidratar(f) for f in
                self.s.query(RentaRow).order_by(RentaRow.id_renta).all()]

    def conteo_por_estado(self):
        filas = self.s.query(RentaRow.estado, func.count()).group_by(RentaRow.estado).all()
        return {estado: n for estado, n in filas}

    def cargos_por_concepto(self):
        filas = (self.s.query(CargoRow.concepto, func.count(), func.sum(CargoRow.monto))
                 .group_by(CargoRow.concepto).all())
        return {c: {"cantidad": n, "total": Dinero(total).monto} for c, n, total in filas}

    def siguiente_id(self):
        return f"R-{self.s.query(RentaRow).count() + 1:04d}"

    def guardar(self, r):
        f = self.s.get(RentaRow, r.id_renta)
        if f is None:
            f = RentaRow(id_renta=r.id_renta)
            self.s.add(f)
        f.folio, f.cliente_id = r.folio, r.cliente_id
        f.inicio, f.fin = r.periodo.inicio, r.periodo.fin
        f.tarifa_diaria_original = r.tarifa_diaria_original.monto
        f.categoria_reservada, f.categoria_asignada = r.categoria_reservada, r.categoria_asignada
        f.vehiculo_id, f.estado = r.vehiculo_id, r.estado
        ci, ef = r.checklist_inicial, r.estado_final
        f.ci_combustible, f.ci_km, f.ci_danos = (
            (ci.combustible_octavos, ci.kilometraje, list(ci.danos)) if ci else (None, None, None))
        f.ef_combustible, f.ef_km, f.ef_danos = (
            (ef.combustible_octavos, ef.kilometraje, list(ef.danos)) if ef else (None, None, None))
        self.s.flush()
        if not self.s.query(CargoRow).filter_by(id_renta=r.id_renta).count():
            for c in r.cargos:
                self.s.add(CargoRow(id_renta=r.id_renta, concepto=c.concepto,
                                    monto=c.monto.monto, detalle=c.detalle))
        _guardar_eventos(self.s, r)


class RepositorioEventos:
    def __init__(self, session):
        self.s = session

    def listar(self, agregado_id=None, nombre=None):
        q = self.s.query(EventoRow).order_by(EventoRow.id)
        if agregado_id:
            q = q.filter_by(agregado_id=agregado_id)
        if nombre:
            q = q.filter_by(nombre=nombre)
        return q.all()

    def conteo_por_nombre(self):
        filas = self.s.query(EventoRow.nombre, func.count()).group_by(EventoRow.nombre).all()
        return {nombre: n for nombre, n in filas}
