from datetime import date, datetime
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.mensajes import clasificar
from src.application.servicios import ServicioNovaRent
from src.domain.errores import DatosInvalidos, DominioError, RequisitosIncompletos
from src.domain.valores import Dinero
from src.infrastructure.db import crear_engine, crear_session_factory, crear_tablas
from src.infrastructure.seed import sembrar_demo


class ReservaIn(BaseModel):
    cliente: str
    sucursal_id: str
    categoria: str
    inicio: date
    fin: date


class AbrirRentaIn(BaseModel):
    folio: str


class UpgradeIn(BaseModel):
    categoria_destino: str


class EntregaIn(BaseModel):
    identificacion_valida: bool = False
    licencia_vigente: bool = False
    tarjeta: str = ""
    combustible_octavos: int | None = Field(None, ge=0, le=8)
    kilometraje: int | None = Field(None, ge=0)
    danos: list[str] = []


class ExtensionIn(BaseModel):
    nueva_fin: date


class DevolucionIn(BaseModel):
    combustible_octavos: int = Field(ge=0, le=8)
    kilometraje: int = Field(ge=0)
    danos: list[str] = []
    fecha_hora: datetime | None = None


def crear_servicio(url=None):
    """Conecta a DATABASE_URL (o SQLite en memoria), crea tablas y siembra datos de demo."""
    engine = crear_engine(url)
    crear_tablas(engine)
    sf = crear_session_factory(engine)
    sembrar_demo(sf)
    return ServicioNovaRent(sf)


def create_app(servicio=None, hoy=date.today):
    app = FastAPI(title="NovaRent API", version="1.0",
                  description="Sistema de gestión operativa de renta de autos.")
    svc = servicio or crear_servicio()

    @app.exception_handler(DominioError)
    async def _dominio(_: Request, exc: DominioError):
        codigo, mensaje = clasificar(exc)
        cuerpo = {"ok": False, "mensaje": mensaje}
        if isinstance(exc, RequisitosIncompletos):
            cuerpo["faltantes"] = exc.faltantes
        return JSONResponse(cuerpo, status_code=codigo)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        return JSONResponse({"ok": False, "mensaje":
                             "Faltan datos o tienen un formato incorrecto. Revisa el formulario."},
                            status_code=422)

    @app.get("/health", tags=["sistema"])
    def health():
        return {"ok": True}

    @app.get("/api/sucursales", tags=["reservaciones"])
    def sucursales():
        return svc.sucursales()

    @app.get("/api/disponibilidad", tags=["reservaciones"], summary="US-01")
    def disponibilidad(sucursal_id: str, inicio: Annotated[date, Query()],
                       fin: Annotated[date, Query()]):
        return svc.disponibilidad_periodo(sucursal_id, inicio, fin)

    @app.post("/api/reservaciones", status_code=201, tags=["reservaciones"],
              summary="US-02/US-03")
    def reservar(d: ReservaIn):
        if not d.cliente.strip():
            raise DatosInvalidos("Falta el nombre del cliente")
        if d.inicio < hoy():
            raise DatosInvalidos("La fecha de inicio no puede ser anterior a hoy")
        r = svc.reservar(d.cliente.strip(), d.sucursal_id, d.categoria, d.inicio, d.fin)
        r["total"] = str(Dinero(r["tarifa_diaria"]).por(r["dias"]).monto)
        r["mensaje"] = "Categoría garantizada (sin unidad física específica)."
        return r

    @app.get("/api/reservaciones", tags=["reservaciones"])
    def reservaciones():
        return svc.listar_reservaciones()

    @app.get("/api/reservaciones/{folio}", tags=["reservaciones"])
    def reservacion(folio: str):
        return svc.obtener_reservacion(folio)

    @app.get("/api/rentas", tags=["rentas"])
    def rentas():
        return svc.listar_rentas()

    @app.post("/api/rentas", status_code=201, tags=["rentas"], summary="Abrir renta desde folio")
    def abrir(d: AbrirRentaIn):
        return svc.iniciar_renta(d.folio)

    @app.get("/api/rentas/{id_renta}", tags=["rentas"])
    def renta(id_renta: str):
        return svc.obtener_renta(id_renta)

    @app.post("/api/rentas/{id_renta}/upgrade", tags=["rentas"], summary="RN-01 / US-14")
    def upgrade(id_renta: str, d: UpgradeIn):
        return svc.aplicar_upgrade(id_renta, d.categoria_destino)

    @app.post("/api/rentas/{id_renta}/entrega", tags=["rentas"], summary="RN-02 / US-04..US-07")
    def entrega(id_renta: str, d: EntregaIn):
        checklist = None
        if d.combustible_octavos is not None and d.kilometraje is not None:
            checklist = {"combustible_octavos": d.combustible_octavos,
                         "kilometraje": d.kilometraje, "danos": d.danos}
        return svc.entregar_con_tarjeta(id_renta, d.identificacion_valida, d.licencia_vigente,
                                        d.tarjeta, checklist)

    @app.post("/api/rentas/{id_renta}/extension", tags=["rentas"], summary="RN-03 / US-08")
    def extension(id_renta: str, d: ExtensionIn):
        return svc.extender(id_renta, d.nueva_fin)

    @app.post("/api/rentas/{id_renta}/devolucion", tags=["rentas"], summary="US-09..US-11")
    def devolucion(id_renta: str, d: DevolucionIn):
        final = {"combustible_octavos": d.combustible_octavos, "kilometraje": d.kilometraje,
                 "danos": d.danos}
        return svc.devolver(id_renta, final, d.fecha_hora)

    @app.get("/api/vehiculos", tags=["limpieza"])
    def vehiculos():
        return svc.listar_vehiculos()

    @app.get("/api/limpieza", tags=["limpieza"], summary="US-12")
    def limpieza():
        return [v for v in svc.listar_vehiculos() if v["estado"] == "EN_LIMPIEZA"]

    @app.post("/api/vehiculos/{vehiculo_id}/limpieza-terminada", tags=["limpieza"],
              summary="US-13")
    def limpieza_terminada(vehiculo_id: str):
        return svc.terminar_limpieza(vehiculo_id)

    @app.get("/api/kpis", tags=["administracion"], summary="US-15")
    def kpis():
        return svc.kpis()

    return app
