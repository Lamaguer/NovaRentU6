# NovaRent — Sistema de Gestión Operativa (PIA CLN)
Equipo 7 · Componentes de Lógica de Negocios · FIME UANL

**Repositorio:** https://github.com/Lamaguer/NovaRentU6 · **Sistema desplegado:** _(URL)_ · **Swagger/OpenAPI:** _(URL)/docs_

## Estado
Dominio, Specifications, máquina de estados y eventos: **hechos y probados**. Pendientes: persistencia, API REST, interfaz, Docker Compose, despliegue.

## Ejecutar pruebas
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -v --cov=src --cov-fail-under=80
ruff check src tests
```
## Estructura
`docs/` (BRD, architecture/ADR, trazabilidad, api/) · `src/domain|application|infrastructure|api` · `tests/` · `.github/workflows/ci.yml`

## Patrones
DDD (agregados `Reservacion`, `Renta`, `Vehiculo`; Value Objects `Dinero`, `PeriodoRenta`, `EstadoFisico`), Specification AND/OR/NOT, State Machine, Domain Events.
