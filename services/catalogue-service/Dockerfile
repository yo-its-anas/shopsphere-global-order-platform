FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=poc \
    SERVICE_NAME=catalogue-service \
    SERVICE_VERSION=0.1.0

WORKDIR /app

RUN groupadd --gid 10001 shopsphere \
    && useradd --uid 10001 --gid shopsphere --no-create-home --shell /usr/sbin/nologin shopsphere

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir .

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).close()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
