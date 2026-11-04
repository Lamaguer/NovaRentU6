# NovaRent — Sistema de Gestión Operativa (PIA CLN)
Equipo 7 · Componentes de Lógica de Negocios · FIME UANL

**Repositorio:** https://github.com/Lamaguer/NovaRentU6 · **Sistema desplegado:** https://novarent.onrender.com/ · **Swagger/OpenAPI:** https://novarent.onrender.com/docs

## Estado
Hechos y probados: dominio, Specifications, máquina de estados, eventos, persistencia (SQLAlchemy + Unit of Work, PostgreSQL en CI), casos de uso y API REST. Interfaz web (`src/web`), Docker Compose y configuración de despliegue incluidos.

## Ejecutar pruebas
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -v --cov=src --cov-fail-under=80
ruff check src tests
```
## Ejecutar la API (local)
```bash
uvicorn src.api.main:create_app --factory --reload
# Swagger: http://127.0.0.1:8000/docs  (usa SQLite por defecto; DATABASE_URL para PostgreSQL)
```
Contrato para la interfaz: `docs/api/contrato.md`.

## Ejecutar con Docker Compose (API + interfaz + PostgreSQL)
```bash
cp .env.example .env          # opcional: cambia POSTGRES_PASSWORD
docker compose up --build
# Interfaz: http://localhost:8000   ·   Swagger: http://localhost:8000/docs
docker compose down           # detener (agrega -v para borrar la base de datos)
```

## Despliegue en línea (Render)
1. Entra a https://render.com > **New > Blueprint** y conecta este repositorio.
2. Render lee `render.yaml`, crea la base PostgreSQL y el servicio web con el `Dockerfile`.
3. Al terminar, la URL pública sirve la interfaz en `/` y Swagger en `/docs`. Copia esa URL al encabezado de este README.

Nota: en el plan gratuito de Render el servicio se duerme tras un rato sin tráfico (la primera visita tarda en responder) y la base gratuita tiene vigencia limitada.

## Estructura
`docs/` (BRD, architecture/ADR, trazabilidad, api/) · `src/domain|application|infrastructure|api|web` · `tests/` · `.github/workflows/ci.yml` · `Dockerfile` · `docker-compose.yml` · `render.yaml`

## Patrones
DDD (agregados `Reservacion`, `Renta`, `Vehiculo`; Value Objects `Dinero`, `PeriodoRenta`, `EstadoFisico`), Specification AND/OR/NOT, State Machine, Domain Events.
