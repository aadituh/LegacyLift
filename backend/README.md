# LegacyLift — Backend

FastAPI service for analyzing and converting legacy COBOL codebases to Python.

**Status:** v1 scaffold. Structure and tooling are in place; feature modules
are empty pending implementation. See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Requirements

- [uv](https://docs.astral.sh/uv/) — manages the Python version, the
  virtualenv, and dependencies
- Python 3.12 (uv downloads it automatically; no manual install needed)

## Quickstart

```bash
cd backend
uv sync                                        # create .venv, install deps
uv run uvicorn legacylift.main:app --reload    # http://127.0.0.1:8000
```

Verify it is up:

```bash
curl http://127.0.0.1:8000/
# {"message":"Hello from LegacyLift"}
```

Interactive API docs are served at http://127.0.0.1:8000/docs.

## Layout

```
backend/
├── pyproject.toml          # project metadata and dependencies
├── uv.lock                 # locked dependency versions (commit this)
├── .python-version         # pins Python 3.12
├── .env.example            # template for local environment config
├── docs/
│   └── CHANGELOG.md        # version history
├── src/legacylift/
│   ├── main.py             # app factory + router wiring
│   ├── core/               # config, error handlers, shared deps
│   ├── projects/           # feature: uploaded legacy codebase
│   ├── analysis/           # feature: dependency graph
│   ├── conversion/         # feature: COBOL -> Python
│   └── ai/                 # shared infra: Gemini client, RAG
└── tests/
```

Each feature package is intended to hold `router.py` (HTTP layer),
`schemas.py` (request/response models), and `service.py` (business logic),
keeping transport concerns out of the logic. `ai/` is shared infrastructure
rather than a feature and exposes no routes of its own.

## Adding a feature module

Feature directories are currently empty. Before importing from one, add an
`__init__.py` so it is a package:

```bash
touch src/legacylift/conversion/__init__.py
```

Then wire its router into the app factory in `src/legacylift/main.py`:

```python
from legacylift.conversion.router import router as conversion_router

fastapi_app.include_router(conversion_router, prefix="/conversion")
```

## Common commands

| Task | Command |
|---|---|
| Install / sync dependencies | `uv sync` |
| Add a dependency | `uv add <package>` |
| Add a dev-only dependency | `uv add --dev <package>` |
| Run the dev server | `uv run uvicorn legacylift.main:app --reload` |
| Run tests | `uv run pytest` (see note below) |
| Run any command in the venv | `uv run <command>` |

`uv run` executes inside the project virtualenv, so activating it manually is
not necessary.

**pytest is not yet a project dependency.** Add it before writing tests, or it
will resolve to a system install (or fail entirely on a fresh clone):

```bash
uv add --dev pytest
```

## Configuration

Copy the template and fill in real values:

```bash
cp .env.example .env
```

`.env` is gitignored and must never be committed. Configuration is intended to
be loaded through `core/config.py` using pydantic-settings.
