# NovaRent: API (FastAPI) + interfaz web estática (src/web) en una sola imagen.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# ---- Etapa de pruebas (docker compose --profile tests) ----
FROM base AS test
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY tests ./tests
CMD ["python", "-m", "pytest", "-v", "--cov=src", "--cov-fail-under=80"]

# ---- Etapa de producción (debe ser la ÚLTIMA) ----
FROM base AS prod
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt
COPY src ./src

RUN useradd --create-home --uid 10001 novarent
USER novarent

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=3)"

CMD ["sh", "-c", "exec uvicorn src.api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]