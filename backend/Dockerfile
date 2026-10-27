# LegacyLift API image. Build from the repository root (the API also needs database/schema.sql):
#   docker build -f backend/Dockerfile -t legacylift-api .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

# Dependencies first, so a code change doesn't reinstall them.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/README.md ./
COPY backend/src ./src
COPY database/schema.sql /app/database/schema.sql
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 app && mkdir -p data && chown app data
USER app

ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "legacylift.main:app", "--host", "0.0.0.0", "--port", "8000"]
