# LegacyLift backend

A FastAPI service that stores COBOL projects and converts COBOL programs into draft Python. Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

## Commands

Run from `backend/`. The [backend checks workflow](../.github/workflows/backend.yml) runs the last four on every change under `backend/`.

| Task | Command |
| --- | --- |
| Install | `uv sync --frozen` |
| Start the API on port 8000 | `uv run --frozen uvicorn legacylift.main:app --reload` |
| Test | `uv run --frozen pytest` |
| Lint | `uv run --frozen ruff check src tests` |
| Format | `uv run --frozen ruff format src tests` |
| Type check | `uv run --frozen mypy` |

Try every route at <http://127.0.0.1:8000/docs>.

## Routes

| Route | Body | Result |
| --- | --- | --- |
| `GET /health` | none | `{"status": "ok"}` |
| `POST /api/convert` | 1–5 `.cbl`/`.cob` files in multipart field `files` | Python for each file; nothing is saved |
| `POST /api/projects` | `{"name": "Demo"}` | New empty project (201) |
| `POST /api/projects/demo` | none | New project with 3 sample files (201) |
| `GET /api/projects/{id}` | none | The project and its files |
| `POST /api/projects/{id}/files` | files in multipart field `files` | The files that were added |
| `POST /api/projects/{id}/analyze` | none | File counts. Placeholder: status `inventory_only` |
| `POST /api/projects/{id}/convert` | none | Python for each program, saved in a run |
| `POST /api/projects/{id}/verify` | none | Placeholder: status `not_verified`, `passed: null` |
| `GET /api/projects/{id}/runs` | none | All runs, oldest first, without their Python |
| `GET /api/projects/{id}/runs/{run_id}` | none | One run; a convert run includes its Python |

Convert statuses: `review_required` (some lines became `# TODO` notes) or `draft` (all lines converted, not yet verified).

To show a translation again after a reload: call `/runs`, take the last `convert` run, and fetch `/runs/{run_id}`.

## Rules

- **Files:** up to 10 per project: `.cbl`/`.cob`, `.cpy`, `.dat`. UTF-8 text, at most 100 KB each. If one file fails, none are added.
- **Names:** unique in a project, ignoring case (`a.cbl` and `a.cob` would both become `a.py`).
- **Converter:** `01`/`77` fields with `PIC X` or `PIC 9`, and `DISPLAY`, `MOVE`, `ADD … TO`, `SUBTRACT … FROM`, `STOP RUN`. Other lines become review notes. Output is a draft; review it before use.
- **Requests** over 1.2 MB get `413`.
- **Storage:** each project is saved as `data/projects/<id>.json`; the newest 100 are kept. Render resets its disk on redeploy.

## Errors

Errors are `{"detail": "message"}`, which the frontend shows as-is.

| Status | Cause | Class in [`errors.py`](src/legacylift/errors.py) |
| --- | --- | --- |
| 400 | Bad file, file count, or project name | `InvalidInputError` |
| 400 | Step run too early, such as converting with no programs | `ProjectStateError` |
| 400 | No `PROGRAM-ID` or `PROCEDURE DIVISION` | `ConversionError` |
| 404 | Unknown project or run | `NotFoundError` |
| 413 | Request body too large | (Starlette) |
| 422 | Missing or invalid field, such as an empty `name` | (FastAPI) |

## Settings

Read from environment variables or `backend/.env` (copy [`.env.example`](.env.example)). Environment variables win.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEGACYLIFT_CORS_ORIGINS` | none | Extra frontend origins, comma-separated. Local Vite and `https://aadituh.github.io` are always allowed. |
| `LEGACYLIFT_DATA_DIR` | `data/projects` | Where project files are saved, relative to where uvicorn starts. Git ignores `backend/data/`. |
| `LEGACYLIFT_MAX_PROJECTS` | `100` | Projects kept; the oldest is deleted first. |
| `LEGACYLIFT_MAX_REQUEST_BYTES` | `1200000` | Largest request body. |

## Code layout

```text
src/legacylift/
├── main.py           builds the app: size limit, CORS, error handler, routers
├── config.py         Settings (pydantic-settings)
├── errors.py         error classes and their HTTP status
├── models.py         stored data (Pydantic): Project, SourceFile, Run, enums
├── schemas.py        request and response bodies (Pydantic)
├── storage.py        ProjectStore: memory + one JSON file per project
├── dependencies.py   ProjectServiceDep, and ProjectDep (loads the project or 404)
├── sample_data.py    files for the demo project
├── data/             sample COBOL files (a small bank's batch) for demos
├── routers/          HTTP only: convert.py, projects.py
├── services/         the rules: uploads.py, conversion.py, projects.py
└── cobol/
    └── converter.py  translate_program(): COBOL subset → Python
```

A request goes **router → service → storage**. For example, `POST /api/projects/{id}/convert`:

```text
routers/projects.py   convert_project()
  → services/projects.py   ProjectService.convert()
    → services/conversion.py   convert_file(), once per program
      → cobol/converter.py   translate_program()
  → storage.py   ProjectStore.save()
```

Tests in [`tests/`](tests/): `test_convert.py` (batch route), `test_projects.py` (project routes), `test_storage.py` (saving), `test_converter.py` (conversion rules).

## Where new work goes

| Task | Where |
| --- | --- |
| Another COBOL statement | `translate_statement()` in `cobol/converter.py`, plus a test that runs the output |
| Parser or dependency analysis | New modules in `cobol/`, called from `ProjectService.analyze()` |
| A new route | `routers/`, with its bodies in `schemas.py` and its logic in `services/` |
| A new error | Subclass `LegacyLiftError`; set `status_code` if it isn't 400 |
| PostgreSQL | A store with `ProjectStore`'s methods (`get`, `add`, `save`); the URL in `config.py` |

See also: [changelog](docs/CHANGELOG.md), [developer guide](../docs/developer.md) (frontend ↔ backend and hosting), [`prototype/`](prototype/README.md) (research code, not part of the API).
