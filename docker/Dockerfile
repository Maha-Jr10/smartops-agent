# Étape 1 : installation des dépendances avec uv
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
RUN uv sync --no-dev --no-editable --extra mlops

# Étape 2 : image d'exécution minimale, utilisateur non root
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY configs ./configs
ENV PATH="/app/.venv/bin:$PATH" \
    SMARTOPS_CONFIG_DIR=/app/configs \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "smartops_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
