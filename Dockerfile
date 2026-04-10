# ─── LocalizaVotos — Imagem de produção ───────────────────────────────────────
# Build context: raiz do repositório (localizavotos/)
# Uso local: docker build -t localizavotos .
# Railway usa esta imagem automaticamente; a variável PORT é injetada pelo Railway.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Paths esperados pelo backend (sobrescrevem os padrões de desenvolvimento)
ENV CANDIDATOS_DIR=/app/candidatos
ENV DATA_DIR=/app/data

# ── Dependências ──────────────────────────────────────────────────────────────
COPY app/backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

# ── Código-fonte ──────────────────────────────────────────────────────────────
COPY app/backend/  ./backend/
COPY app/frontend/ ./frontend/

# ── Dados (candidatos e camadas compartilhadas) ───────────────────────────────
COPY candidatos/ ./candidatos/
COPY data/       ./data/

# ── Startup ───────────────────────────────────────────────────────────────────
WORKDIR /app/backend

EXPOSE 8000
ENV PORT=8000

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
