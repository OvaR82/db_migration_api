# === Build stage: install dependencies into a venv, copying only what is needed ===
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create a virtual environment in /opt/venv (no native compilation)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# If you have a requirements-prod.txt, use it; otherwise, fallback to requirements.txt
COPY requirements.txt .

# Prefer binary wheels to avoid system toolchains when possible
RUN pip install --upgrade pip wheel setuptools \
 && pip install --only-binary=:all: -r requirements.txt || pip install -r requirements.txt

# === Minimal runtime stage ===
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 10001 appuser

# Copy the virtual environment from the builder (no toolchain, no pip cache)
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY . .

USER appuser
EXPOSE 8000

# If running migrations on startup, use a shell-based entrypoint; otherwise run Gunicorn directly
# CMD ["bash", "-lc", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
