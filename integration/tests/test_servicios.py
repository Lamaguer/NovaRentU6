from datetime import date, datetime

import pytest

from src.domain.errores import (
    DatosInvalidos,
    NoEncontrado,
    RequisitosIncompletos,
    SinDisponibilidad,
    TransicionInvalida,
)
from src.infrastructure.seed import sembrar

D = date
CHECK = {"combustible_octavos": 8, "kilometraje": 1000, "danos": ["rayon puerta"]}


def reservar(s, inicio=D(2026, 11, 10), fin=D(2026, 11, 15), categoria="ECONOMICO", **kw):
    return s.reservar("C-01", "MTY-CENTRO", categoria, inicio, fin, **kw)


def entregar_ok(s, id_renta, **kw):
    return s.entregar(id_renta, True, True, True, CHECK, **kw)


# ---- Persistencia de reservaciones (US-01..US-03) ----
def test_us02_reservacion_confirmada_sobrevive_a_una_nueva_transaccion(servicio):
    r = reservar(servicio, folio="F-001")
    assert r["estado"] == "CONFIRMADA" and r["tarifa_diaria"] == "500.00"
    assert servicio.obtener_reservacion("F-001")["estado"] == "CONFIRMADA"
    assert servicio.disponibilidad("MTY-CENTRO", "ECONOMICO", D(2026, 11, 12))["disponibles"] == 1


def test_br02_sobreventa_rechazada_y_nada_se_guarda(servicio):
    reservar(servicio, folio="F-001")
    reservar(servicio, folio="F-002")
    with pytest.raises(SinDisponibilidad):
        reservar(servicio, folio="F-003")
    with pytest.raises(NoEncontrado):  # rollback: la reservacion rechazada no quedo guardada
        servicio.obtener_reservacion("F-003")
    assert servicio.kpis()["sobreventas"] == 0


def test_br02_limite_dia_de_devolucion_se_puede_reservar_de_nuevo(servicio):
    reservar(servicio, folio="F-001")
    reservar(servicio, folio="F-002")
    reservar(servicio, inicio=D(2026, 11, 15), fin=D(2026, 11, 17), folio="F-003")


def test_folio_duplicado_y_categoria_invalida(servicio):
    reservar(servicio, folio="F-001")
    with pytest.raises(DatosInvalidos):
        reservar(servicio, folio="F-001")
    with pytest.raises(DatosInvalidos):
        reservar(servicio, categoria="AVION")
    with pytest.raises(DatosInvalidos):
        reservar(servicio, inicio=D(2026, 11, 15), fin=D(2026, 11, 10))


def test_reservacion_sin_inventario_no_existe(servicio):
    with pytest.raises(NoEncontrado):
        servicio.reservar("C-01", "OTRA-SUCURSAL", "ECONOMICO", D(2026, 11, 10), D(2026, 11, 12))


def test_confirmar_despues_de_crear_pendiente(servicio):
    reservar(servicio, folio="F-001", confirmar=False)
    assert servicio.obtener_reservacion("F-001")["estado"] == "PENDIENTE"
    assert servicio.confirmar_reservacion("F-001")["estado"] == "CONFIRMADA"
    with pytest.raises(TransicionInvalida):
        servicio.confirmar_reservacion("F-001")
    assert [r["folio"] for r in servicio.listar_reservaciones()] == ["F-001"]


# ---- Ciclo completo de la renta (US-04..US-13) ----
def test_ciclo_completo_con_cargos_persistidos(servicio):
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    assert renta["estado"] == "PENDIENTE" and renta["total_renta"] == "2500.00"

    entregada = entregar_ok(servicio, renta["id_renta"])
    assert entregada["estado"] == "ENTREGADO" and entregada["vehiculo_id"]
    estados = {v["id"]: v["estado"] for v in servicio.listar_vehiculos()}
    assert estados[entregada["vehiculo_id"]] == "RENTADO"

    final = {"combustible_octavos": 7, "kilometraje": 2100, "danos": ["rayon puerta", "espejo"]}
    devuelta = servicio.devolver(renta["id_renta"], final, datetime(2026, 11, 15, 14, 0))
    conceptos = {c["concepto"]: c["monto"] for c in devuelta["cargos"]}
    assert devuelta["estado"] == "DEVUELTO"
    assert conceptos == {"RETRASO": "300.00", "KILOMETRAJE": "400.00",   # 2 h; 100 km extra
                         "COMBUSTIBLE": "168.75", "DANOS": "500.00"}
    # persistido: una consulta nueva ve los mismos cargos y el mismo total
    again = servicio.obtener_renta(renta["id_renta"])
    assert again["cargos"] == devuelta["cargos"] and again["total_cargos"] == "1368.75"

    limpio = servicio.terminar_limpieza(entregada["vehiculo_id"])
    assert limpio["estado"] == "DISPONIBLE"


def test_eventos_de_dominio_quedan_en_la_bitacora(servicio):
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    entregar_ok(servicio, renta["id_renta"])
    servicio.devolver(renta["id_renta"], {"combustible_octavos": 8, "kilometraje": 1050})
    nombres = [e["nombre"] for e in servicio.listar_eventos()]
    for esperado in ("ReservacionConfirmada", "VehiculoEntregado", "VehiculoDevuelto",
                     "VehiculoEnLimpieza"):
        assert nombres.count(esperado) == 1


# ---- RN-02: entrega bloqueada ----
def test_rn02_entrega_bloqueada_no_cambia_nada(servicio):
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    with pytest.raises(RequisitosIncompletos) as e:
        servicio.entregar(renta["id_renta"], True, False, False, None)
    assert len(e.value.faltantes) == 3
    assert servicio.obtener_renta(renta["id_renta"])["estado"] == "PENDIENTE"
    assert {v["estado"] for v in servicio.listar_vehiculos()} == {"DISPONIBLE"}


def test_entrega_sin_vehiculos_disponibles(servicio):
    for i in (1, 2):
        reservar(servicio, folio=f"F-00{i}")
        entregar_ok(servicio, servicio.iniciar_renta(f"F-00{i}")["id_renta"])
    reservar(servicio, inicio=D(2026, 12, 1), fin=D(2026, 12, 3), folio="F-003")
    r3 = servicio.iniciar_renta("F-003")
    with pytest.raises(SinDisponibilidad):
        entregar_ok(servicio, r3["id_renta"])


# ---- Transiciones invalidas ----
def test_devolver_renta_no_entregada_y_entregar_dos_veces(servicio):
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    with pytest.raises(TransicionInvalida):
        servicio.devolver(renta["id_renta"], {"combustible_octavos": 8, "kilometraje": 1})
    entregar_ok(servicio, renta["id_renta"])
    with pytest.raises(TransicionInvalida):
        entregar_ok(servicio, renta["id_renta"])
    with pytest.raises(DatosInvalidos):  # km final menor al inicial
        servicio.devolver(renta["id_renta"], {"combustible_octavos": 8, "kilometraje": 10})


def test_iniciar_renta_de_reservacion_pendiente_o_ya_cumplida(servicio):
    reservar(servicio, folio="F-001", confirmar=False)
    with pytest.raises(TransicionInvalida):
        servicio.iniciar_renta("F-001")
    servicio.confirmar_reservacion("F-001")
    servicio.iniciar_renta("F-001")
    with pytest.raises(TransicionInvalida):
        servicio.iniciar_renta("F-001")


def test_terminar_limpieza_de_vehiculo_disponible_y_ids_inexistentes(servicio):
    vid = servicio.listar_vehiculos()[0]["id"]
    with pytest.raises(TransicionInvalida):
        servicio.terminar_limpieza(vid)
    with pytest.raises(NoEncontrado):
        servicio.terminar_limpieza("NO-EXISTE")
    with pytest.raises(NoEncontrado):
        servicio.obtener_renta("R-9999")


# ---- RN-03 extension ----
def test_rn03_extension_con_y_sin_disponibilidad(servicio):
    reservar(servicio, folio="F-001")
    reservar(servicio, folio="F-002", inicio=D(2026, 11, 15), fin=D(2026, 11, 18))
    renta = servicio.iniciar_renta("F-001")
    entregar_ok(servicio, renta["id_renta"])
    ext = servicio.extender(renta["id_renta"], D(2026, 11, 17))   # hay 1 lugar libre
    assert ext["fin"] == "2026-11-17"
    assert servicio.obtener_renta(renta["id_renta"])["fin"] == "2026-11-17"
    reservar(servicio, folio="F-003", inicio=D(2026, 11, 17), fin=D(2026, 11, 20))
    with pytest.raises(SinDisponibilidad):                        # 17 ya lo apartan 2
        servicio.extender(renta["id_renta"], D(2026, 11, 19))
    with pytest.raises(DatosInvalidos):
        servicio.extender(renta["id_renta"], D(2026, 11, 12))


# ---- RN-01 upgrade ----
def test_rn01_upgrade_solo_sin_unidades_y_conserva_tarifa(servicio):
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    with pytest.raises(SinDisponibilidad):  # aun hay unidades ECONOMICO
        servicio.aplicar_upgrade(renta["id_renta"], "COMPACTO")
    # se agotan las unidades fisicas de la categoria reservada
    for i in (2, 3):
        reservar(servicio, folio=f"F-00{i}", inicio=D(2026, 12, 1), fin=D(2026, 12, 3))
        entregar_ok(servicio, servicio.iniciar_renta(f"F-00{i}")["id_renta"])
    up = servicio.aplicar_upgrade(renta["id_renta"], "SUV")
    assert up["categoria_asignada"] == "SUV" and up["tarifa_diaria"] == "500.00"
    assert entregar_ok(servicio, renta["id_renta"])["vehiculo_id"].startswith("MTY-SUV")


# ---- KPIs (US-15) ----
def test_us15_kpis(servicio):
    assert servicio.kpis()["minutos_devolucion_a_disponible"] is None
    reservar(servicio, folio="F-001")
    renta = servicio.iniciar_renta("F-001")
    vid = entregar_ok(servicio, renta["id_renta"])["vehiculo_id"]
    servicio.devolver(renta["id_renta"], {"combustible_octavos": 8, "kilometraje": 1100,
                                          "danos": ["rayon puerta", "espejo"]},
                      datetime(2026, 11, 14, 10, 0))
    servicio.terminar_limpieza(vid)
    k = servicio.kpis()
    assert k["sobreventas"] == 0
    assert k["cobros_por_danos"] == {"cantidad": 1, "total": "500.00"}
    assert k["rentas_por_estado"] == {"DEVUELTO": 1}
    assert k["minutos_devolucion_a_disponible"] >= 0
    assert k["eventos"]["VehiculoDisponible"] == 1


def test_sembrar_es_idempotente(servicio, session_factory):
    antes = len(servicio.listar_vehiculos())
    sembrar(session_factory, sucursales=("MTY-CENTRO",),
            capacidad={"ECONOMICO": 2, "COMPACTO": 1, "SUV": 1})
    assert len(servicio.listar_vehiculos()) == antes
