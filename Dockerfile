# Etapa de deps: instala dependencias en una venv para copiar solo lo necesario
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Instala deps de Python en /opt/venv (sin compilar nativo)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Si tienes un requirements-prod.txt, cópialo; si no, usa requirements.txt
COPY requirements.txt .
# Fuerza ruedas binarias cuando sea posible para evitar toolchains del sistema
RUN pip install --upgrade pip wheel setuptools \
 && pip install --only-binary=:all: -r requirements.txt || pip install -r requirements.txt

# Etapa runtime mínima
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# Crea usuario no root
RUN useradd -m -u 10001 appuser

# Copia la venv con dependencias desde builder (sin toolchain, sin pip cache)
COPY --from=builder /opt/venv /opt/venv

# Copia el código de la app
COPY . .

USER appuser
EXPOSE 8000

# Si ejecutas migraciones en arranque, usa un entrypoint/cmd de shell; si no, Gunicorn directo
# CMD ["bash", "-lc", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]


