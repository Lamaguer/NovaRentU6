# ADR-005 Despliegue con Docker, Docker Compose y Render con PostgreSQL
**Contexto.** El PIA exige un entorno reproducible (DB + App + Tests con Docker Compose), configuración separada del código (12-Factor) y un despliegue funcional con Swagger activo en producción. El equipo necesita una opción gratuita que cualquier integrante pueda operar.
**Decisión.**
- Un solo contenedor sirve la API (FastAPI) y la interfaz web estática (`src/web`), para no mantener dos despliegues.
- El `Dockerfile` tiene etapas: `base`, `test` (herramientas de prueba) y `prod`, que va al final para que sea la que se construye por defecto.
- `docker-compose.yml` levanta `db` y `web`; con el perfil `tests` agrega `db-test` y `tests`. Las pruebas usan una base **separada**, porque borran y recrean tablas.
- La configuración llega por variables de entorno (`DATABASE_URL`, `APP_ENV`, `PORT`); `.env.example` no contiene secretos reales y `.env` está ignorado por Git.
- En producción se despliega en Render con `render.yaml` (Blueprint): servicio web con Docker y base PostgreSQL, ambos en plan gratuito, con `autoDeploy` en cada push a `main` y `healthCheckPath: /health`.
**Alternativas.**
- Supabase para la base de datos: descartada por ahora, porque exige conexión por pooler (IPv6) y activar RLS; Render permite declarar app y base en un mismo archivo.
- Railway o Fly.io: sin ventaja clara para este alcance y con menos práctica del equipo.
- Interfaz y API por separado: duplica despliegue y configuración sin beneficio para la demostración.
**Consecuencias.**
- (+) Cualquier integrante levanta el sistema con `docker compose up`, y el despliegue se actualiza solo al hacer push.
- (−) El servicio gratuito se duerme tras minutos sin tráfico y la primera visita tarda cerca de un minuto; conviene abrir la URL antes de presentar.
- (−) La base gratuita de Render caduca a los 30 días de crearse; la fecha de creación debe anotarse en el reporte.
- (−) No hay migraciones: las tablas se crean al arrancar, así que un cambio de columna exige recrear la base.