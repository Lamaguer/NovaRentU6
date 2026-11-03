"""Datos iniciales de demostracion (ficticios). Idempotente: no duplica si ya existen."""
from src.domain.errores import NoEncontrado
from src.domain.inventario import InventarioCategoria
from src.domain.vehiculo import Vehiculo
from src.infrastructure.unit_of_work import UnitOfWork

SUCURSALES = ("MTY-CENTRO", "MTY-AEROPUERTO")
NOMBRES = {"MTY-CENTRO": "Monterrey Centro", "MTY-AEROPUERTO": "Aeropuerto de Monterrey",
           "APODACA": "Apodaca"}
CAPACIDAD = {"ECONOMICO": 3, "COMPACTO": 2, "SUV": 2, "PREMIUM": 1}


def _asegurar_inventario(uow, sucursal, categoria, capacidad):
    try:
        uow.inventarios.obtener(sucursal, categoria)  # ya existe: se conserva (con sus apartados)
    except NoEncontrado:
        uow.inventarios.guardar(InventarioCategoria(sucursal, categoria, capacidad))


def sembrar(session_factory, sucursales=SUCURSALES, capacidad=CAPACIDAD):
    with UnitOfWork(session_factory) as uow:
        existentes = {v.id for v in uow.vehiculos.listar()}
        for suc in sucursales:
            for cat, n in capacidad.items():
                _asegurar_inventario(uow, suc, cat, n)
                for i in range(1, n + 1):
                    id_v = f"{suc}-{cat[:3]}-{i:02d}"  # ID unico por sucursal
                    if id_v not in existentes:
                        uow.vehiculos.guardar(Vehiculo(id_v, cat, suc))
        uow.commit()


def sembrar_demo(session_factory):
    """Datos de la demostracion. Apodaca/ECONOMICO: hay lugar en el inventario logico pero la
    unica unidad esta en limpieza -> escenario de upgrade (RN-01). Idempotente."""
    sembrar(session_factory)
    sembrar(session_factory, sucursales=("APODACA",),
            capacidad={"ECONOMICO": 1, "COMPACTO": 2, "SUV": 2, "PREMIUM": 1})
    with UnitOfWork(session_factory) as uow:
        v = uow.vehiculos.obtener("APODACA-ECO-01")
        if v.estado == "DISPONIBLE":
            v.rentar()
            v.devolver()
            uow.vehiculos.guardar(v)
            uow.commit()
