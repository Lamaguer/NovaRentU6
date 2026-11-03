# NovaRent — Sistema de Gestión Operativa (PIA CLN)
Equipo 7 · Componentes de Lógica de Negocios · FIME UANL

**Repositorio:** https://github.com/Lamaguer/NovaRentU6 · **Sistema desplegado:** _(pendiente)_ · **Swagger/OpenAPI:** _(pendiente: URL del despliegue + /docs)_

## Estado
Hechos y probados: dominio, Specifications, máquina de estados, eventos, persistencia (SQLAlchemy + Unit of Work, PostgreSQL en CI), casos de uso y API REST. Pendientes: interfaz web, Docker Compose, despliegue.

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

## Estructura
`docs/` (BRD, architecture/ADR, trazabilidad, api/) · `src/domain|application|infrastructure|api` · `tests/` · `.github/workflows/ci.yml`

## Patrones
DDD (agregados `Reservacion`, `Renta`, `Vehiculo`; Value Objects `Dinero`, `PeriodoRenta`, `EstadoFisico`), Specification AND/OR/NOT, State Machine, Domain Events.
