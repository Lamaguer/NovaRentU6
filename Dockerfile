# NovaRent: API (FastAPI) + interfaz web estática (src/web) en una sola imagen.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Solo dependencias de ejecución (pytest, ruff y httpx son para pruebas/CI).
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY src ./src

# Usuario sin privilegios
RUN useradd --create-home --uid 10001 novarent
USER novarent

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=3)"

# Un solo worker: al arrancar se crean tablas y se siembran datos de demo (idempotente).
# $PORT lo define el proveedor de hosting (Render, Railway, etc.); por defecto 8000.
CMD ["sh", "-c", "exec uvicorn src.api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
