# ============================================================================
# P6_AP-IA — Imagen única con NumPy 1.26 (anclaje de PaddleOCR)
#
# Por qué un único contenedor:
#   - Validamos previamente que TODAS las dependencias (paddle, torch,
#     facenet-pytorch, langchain, fastapi, sklearn, statsmodels)
#     resuelven en Python 3.12 + NumPy 1.26.
#   - Mantiene la simplicidad: un Dockerfile, un proceso, sin RPC interno.
# ============================================================================

FROM python:3.12-slim

# --- Dependencias del sistema ---
# - libgl1, libglib2.0-0: requeridos por opencv-python
# - libgomp1: OpenMP (paddle, torch)
# - build-essential, gcc: por si alguna wheel falla y hay que compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Instalar uv (gestor de paquetes) ---
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# --- Capa de dependencias (cache friendly) ---
COPY requirements.txt /app/requirements.txt
RUN uv venv /app/.venv --python 3.12 && \
    uv pip install --python /app/.venv/bin/python --link-mode=copy -r /app/requirements.txt

# --- Código de la aplicación ---
COPY src /app/src
COPY main.py /app/main.py
COPY config /app/config

# --- Directorios writeables ---
RUN mkdir -p /app/data /app/logs /app/models

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# --- Arranque: FastAPI vía uvicorn ---
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
