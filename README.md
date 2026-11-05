# NovaRent — Sistema de Gestión Operativa (PIA CLN)

Equipo 7 · Componentes de Lógica de Negocio · FIME UANL · Módulo U-6

Integrantes: Luis Enrique Almaguer Castillo, Héctor Alexander Tovar González y Lizzie Anette Mireles Tejada.

**Repositorio:** https://github.com/Lamaguer/NovaRentU6 · **Sistema desplegado:** https://novarent.onrender.com/ · **Swagger/OpenAPI:** https://novarent.onrender.com/docs

NovaRent es una empresa ficticia de renta de autos por día. El cliente reserva una **categoría** (no una unidad) y el auto físico se asigna al entregar. Todos los datos y tarifas son de demostración.

## Estado

Hecho y probado: dominio (agregados, Specifications, máquinas de estado, eventos), persistencia (SQLAlchemy + Unit of Work; PostgreSQL en CI), casos de uso y API REST. También incluye la interfaz web (`src/web`), Docker Compose, CI en GitHub Actions y configuración de despliegue en Render.

Resultado de la última evidencia del reporte: **60 pruebas pasan** con **98.47 %** de cobertura (mínimo exigido: 80 %).

## Relación con el paquete de la actividad

El LEEME del paquete propone un modelo de pruebas con estados `SOLICITADA → APROBADA → ENTREGADA → DEVUELTA`, actores y datos en CSV. Ese modelo es solo una propuesta. Este proyecto se derivó del BRD propio del equipo (renta de autos), por lo que difiere así:

| Paquete de la actividad | Este proyecto |
|---|---|
| Operación con estados `SOLICITADA`, `APROBADA`, `ENTREGADA`, `DEVUELTA`, `CANCELADA` | `Reservacion` (`PENDIENTE`, `CONFIRMADA`, `CUMPLIDA`), `Renta` (`PENDIENTE`, `ENTREGADO`, `DEVUELTO`) y `Vehiculo` (`DISPONIBLE`, `RENTADO`, `EN_LIMPIEZA`) |
| `cliente_activo`, `equipo_disponible`, `deposito_cubierto` | `requisitos_completos` (RN-02), `extension_permitida` (RN-03) y `upgrade_permitido` (RN-01) |
| Actor arrendatario y equipo en renta | Cliente y categoría de auto; la cancelación queda fuera de alcance (BRD v1.1) |
| Datos de ejemplo en CSV | Datos de demostración sembrados en `src/infrastructure/seed.py` |

Los requisitos propios están en `docs/BRD.md` y la trazabilidad en `docs/trazabilidad.md`.

## Ejecutar pruebas

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -v --cov=src --cov-fail-under=80
ruff check src tests
```

Las pruebas usan SQLite en memoria. Para correrlas contra PostgreSQL, define `TEST_DATABASE_URL` (así lo hace el CI) o usa Docker Compose (ver abajo).

## Ejecutar la API (local)

```bash
uvicorn src.api.main:create_app --factory --reload
# Swagger: http://127.0.0.1:8000/docs  (usa SQLite por defecto; DATABASE_URL para PostgreSQL)
```

Contrato para la interfaz: `docs/api/contrato.md`. Especificación OpenAPI: `docs/api/openapi.json`.

## Ejecutar con Docker Compose (base de datos + aplicación + pruebas)

```bash
cp .env.example .env          # opcional: cambia POSTGRES_PASSWORD
docker compose up --build
# Interfaz: http://localhost:8000   ·   Swagger: http://localhost:8000/docs
docker compose down           # detener (agrega -v para borrar la base de datos)
```

Pruebas dentro de Docker, contra una base PostgreSQL separada (`db-test`):

```bash
docker compose --profile tests run --rm tests
```

## Integración continua y despliegue

- **CI:** `.github/workflows/ci.yml` se ejecuta en cada push y pull request: instala dependencias, corre `ruff` y `pytest` con cobertura mínima de 80 % contra PostgreSQL 16.
- **Despliegue:** Render lee `render.yaml`, construye el `Dockerfile` y publica en cada push a `main`, con `/health` como chequeo de salud.

### Despliegue en línea (Render)

1. Entra a https://render.com > **New > Blueprint** y conecta este repositorio.
2. Render lee `render.yaml`, crea la base PostgreSQL y el servicio web con el `Dockerfile`.
3. Al terminar, la URL pública sirve la interfaz en `/` y Swagger en `/docs`.

Nota: en el plan gratuito de Render el servicio se duerme tras un rato sin tráfico (la primera visita tarda cerca de un minuto) y la base gratuita caduca a los 30 días de crearse.

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/BRD.md`, `docs/trazabilidad.md` | Requisitos de negocio y matriz de trazabilidad |
| `docs/Analisis/` | Glosario del dominio y escenarios Gherkin alternos |
| `docs/Arquitectura/` | ADR-001 a ADR-006, diagramas y principios SOLID |
| `docs/api/` | Contrato de la API y `openapi.json` |
| `docs/Reporte_NovaRent_PIA.pdf` | Reporte final con evidencias |
| `src/domain`, `src/application`, `src/infrastructure`, `src/api`, `src/web` | Capas del sistema |
| `tests/unit`, `tests/integration` | Pruebas unitarias y de integración |
| `Dockerfile`, `docker-compose.yml`, `render.yaml`, `.github/workflows/ci.yml` | Contenedores, despliegue y CI |

## Patrones

DDD (agregados `Reservacion`, `Renta`, `Vehiculo` e `InventarioCategoria`; Value Objects `Dinero`, `PeriodoRenta` y `EstadoFisico`), Specification con operadores AND/OR/NOT (`&`, `|`, `~`), State Machine, Domain Events, Unit of Work, Repository y Adapter (`PasarelaPagoSimulada`).
