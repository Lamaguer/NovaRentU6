from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.api.main import crear_servicio, create_app


@pytest.fixture
def client():
    return TestClient(create_app(crear_servicio("sqlite://"), hoy=lambda: date(2026, 11, 2)))


RES = {"cliente": "Ana Torres", "sucursal_id": "MTY-CENTRO", "categoria": "ECONOMICO",
       "inicio": "2026-11-10", "fin": "2026-11-15"}
ENTREGA = {"identificacion_valida": True, "licencia_vigente": True, "tarjeta": "4111",
           "combustible_octavos": 8, "kilometraje": 100}


def abrir(client, **cambios):
    folio = client.post("/api/reservaciones", json={**RES, **cambios}).json()["folio"]
    return client.post("/api/rentas", json={"folio": folio}).json()["id_renta"]


def test_flujo_feliz_por_api(client):
    assert client.get("/health").json() == {"ok": True}
    assert {s["id"] for s in client.get("/api/sucursales").json()} == {
        "MTY-CENTRO", "MTY-AEROPUERTO", "APODACA"}
    r = client.post("/api/reservaciones", json=RES)
    assert r.status_code == 201 and r.json()["dias"] == 5 and "sin unidad" in r.json()["mensaje"]
    folio = r.json()["folio"]
    renta = client.post("/api/rentas", json={"folio": folio}).json()["id_renta"]
    e = client.post(f"/api/rentas/{renta}/entrega", json=ENTREGA)
    assert e.status_code == 200 and e.json()["estado"] == "ENTREGADO"
    d = client.post(f"/api/rentas/{renta}/devolucion", json={
        "combustible_octavos": 6, "kilometraje": 300, "danos": ["espejo"],
        "fecha_hora": "2026-11-15T10:00:00"})
    cuerpo = d.json()
    assert cuerpo["estado"] == "DEVUELTO"
    assert {c["concepto"] for c in cuerpo["cargos"]} == {"COMBUSTIBLE", "DANOS"}
    assert cuerpo["comparacion"]["danos_nuevos"] == ["espejo"]
    en_limpieza = [v["id"] for v in client.get("/api/limpieza").json()]
    assert "MTY-CENTRO-ECO-01" in en_limpieza
    assert client.post("/api/vehiculos/MTY-CENTRO-ECO-01/limpieza-terminada").status_code == 200
    assert client.get("/api/kpis").json()["sobreventas"] == 0
    assert client.get(f"/api/rentas/{renta}").status_code == 200
    assert len(client.get("/api/rentas").json()) == 1
    assert len(client.get("/api/reservaciones").json()) == 1
    assert client.get(f"/api/reservaciones/{folio}").json()["estado"] == "CUMPLIDA"
    assert len(client.get("/api/vehiculos").json()) > 10


def test_us01_disponibilidad_oculta_categorias_llenas(client):
    q = {"sucursal_id": "MTY-AEROPUERTO", "inicio": "2026-11-10", "fin": "2026-11-12"}
    assert len(client.get("/api/disponibilidad", params=q).json()) == 4
    client.post("/api/reservaciones", json={**RES, "sucursal_id": "MTY-AEROPUERTO",
                                            "categoria": "PREMIUM"})
    cats = [c["categoria"] for c in client.get("/api/disponibilidad", params=q).json()]
    assert "PREMIUM" not in cats
    assert client.get("/api/disponibilidad", params={**q, "sucursal_id": "NOPE"}).status_code == 404


def test_errores_llegan_en_lenguaje_de_cliente(client):
    pr = {**RES, "categoria": "PREMIUM"}
    client.post("/api/reservaciones", json=pr)
    r = client.post("/api/reservaciones", json=pr)
    assert r.status_code == 409
    assert "No hay unidades disponibles" in r.json()["mensaje"]
    assert "BR-02" not in r.json()["mensaje"]
    r = client.post("/api/reservaciones", json={**RES, "inicio": "2026-11-01", "fin": "2026-11-05"})
    assert r.status_code == 422 and "anterior a hoy" in r.json()["mensaje"]
    r = client.post("/api/reservaciones", json={**RES, "cliente": " "})
    assert r.status_code == 422 and "nombre" in r.json()["mensaje"]


def test_entrega_incompleta_devuelve_faltantes_legibles(client):
    renta = abrir(client)
    r = client.post(f"/api/rentas/{renta}/entrega", json={"identificacion_valida": True})
    assert r.status_code == 409 and len(r.json()["faltantes"]) == 3
    assert "licencia" in r.json()["mensaje"]
    assert client.get(f"/api/rentas/{renta}").json()["estado"] == "PENDIENTE"


def test_us05_pago_rechazado_por_pasarela_simulada(client):
    renta = abrir(client)
    r = client.post(f"/api/rentas/{renta}/entrega", json={**ENTREGA, "tarjeta": "4111111111110000"})
    assert r.status_code == 409 and "pago" in r.json()["mensaje"]
    assert client.get(f"/api/rentas/{renta}").json()["estado"] == "PENDIENTE"


def test_upgrade_y_extension_por_api(client):
    renta = abrir(client, sucursal_id="APODACA")
    sin_unidad = client.post(f"/api/rentas/{renta}/entrega", json=ENTREGA)
    assert sin_unidad.status_code == 409 and "upgrade" in sin_unidad.json()["mensaje"]
    mal = client.post(f"/api/rentas/{renta}/upgrade", json={"categoria_destino": "ECONOMICO"})
    assert mal.status_code == 409 and "categoría superior" in mal.json()["mensaje"]
    ok = client.post(f"/api/rentas/{renta}/upgrade", json={"categoria_destino": "SUV"})
    assert ok.json()["categoria_asignada"] == "SUV" and ok.json()["tarifa_diaria"] == "500.00"
    assert client.post(f"/api/rentas/{renta}/entrega", json=ENTREGA).status_code == 200
    ext = client.post(f"/api/rentas/{renta}/extension", json={"nueva_fin": "2026-11-17"})
    assert ext.json()["fin"] == "2026-11-17"
    antes = client.post(f"/api/rentas/{renta}/extension", json={"nueva_fin": "2026-11-16"})
    assert antes.status_code == 422 and "posterior" in antes.json()["mensaje"]


def test_extension_bloqueada_se_explica_al_cliente(client):
    pr = {"sucursal_id": "MTY-AEROPUERTO", "categoria": "PREMIUM"}
    renta = abrir(client, **pr)
    client.post(f"/api/rentas/{renta}/entrega", json=ENTREGA)
    client.post("/api/reservaciones", json={**RES, **pr, "inicio": "2026-11-15",
                                            "fin": "2026-11-18"})
    r = client.post(f"/api/rentas/{renta}/extension", json={"nueva_fin": "2026-11-17"})
    assert r.status_code == 409 and "ya está reservada" in r.json()["mensaje"]


def test_no_encontrado_validacion_y_estado_sin_tecnicismos(client):
    r = client.get("/api/rentas/NOPE")
    assert r.status_code == 404 and "Revisa el folio" in r.json()["mensaje"]
    r = client.post("/api/reservaciones", json={"cliente": "x"})
    assert r.status_code == 422 and "Revisa el formulario" in r.json()["mensaje"]
    r = client.post("/api/reservaciones", json={**RES, "fin": "2026-11-10"})
    assert r.status_code == 422 and "posterior" in r.json()["mensaje"]
    renta = abrir(client)
    r = client.post(f"/api/rentas/{renta}/devolucion",
                    json={"combustible_octavos": 8, "kilometraje": 1})
    assert r.status_code == 409 and "estado actual" in r.json()["mensaje"]
