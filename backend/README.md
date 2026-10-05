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
| Format check | `uv run --frozen ruff format --check src tests` |
| Type check | `uv run --frozen mypy` |

Try every route at <http://127.0.0.1:8000/docs>.

## Routes

| Route | Body | Result |
| --- | --- | --- |
| `GET /health` | none | `{"status": "ok"}` |
| `POST /api/convert` | 1–5 `.cbl`/`.cob` files in multipart field `files` | Python for each file, plus `download_id`. Not saved as a project |
| `GET /api/projects` | none | Every project, newest first: id, name, file counts, last run (no file contents) |
| `POST /api/projects` | `{"name": "Demo"}` | New empty project (201) |
| `POST /api/projects/demo` | none | New project with 3 sample files (201) |
| `GET /api/projects/{id}` | none | The project and its files |
| `DELETE /api/projects/{id}` | none | Deletes the project, its files, and its runs (204) |
| `POST /api/projects/{id}/files` | files in multipart field `files` | The files that were added |
| `DELETE /api/projects/{id}/files/{file_id}` | none | Removes one file (204); saved runs keep their results |
| `POST /api/projects/{id}/analyze` | none | File counts. Placeholder: status `inventory_only` |
| `POST /api/projects/{id}/convert` | none | Python for each program, saved as a run |
| `POST /api/projects/{id}/verify` | none | Run each program with GnuCOBOL and compare stdout to Python: `verified` / `mismatch` / `not_verified` (no `cobc`) |
| `GET /api/projects/{id}/runs` | none | All runs, oldest first, without their Python |
| `GET /api/projects/{id}/runs/{run_id}` | none | One run; a convert run includes its Python |
| `GET /api/projects/{id}/runs/{run_id}/files/{name}` | none | One saved `.py` file (`Content-Disposition: attachment`) |
| `GET /api/convert/{download_id}/files/{name}` | none | One batch `.py` file, until the API restarts |

IDs are short numbers as text: projects `"1"`, `"2"`, … across the API; files and runs `"1"`, `"2"`, … within their project. IDs are never reused.

Convert status: `review_required` (some lines became `# TODO` notes) or `draft` (every line converted, not yet verified). To reopen a project: `GET /api/projects`, then `GET /api/projects/{id}`; to show its last translation, fetch `/runs`, then the last `convert` run's `/runs/{run_id}`.

## Rules

- **Files:** up to 10 per project (`.cbl`/`.cob`, `.cpy`, `.dat`), UTF-8 text, at most 100 KB each, names unique ignoring case and at most 255 printable characters. If one file fails, none are added.
- **Converter:** `01`/`77` `WORKING-STORAGE` fields with `PIC X`, `XX`, `X(n)` or `PIC 9`, `99`, `9(n)`, plus `DISPLAY`, `MOVE … TO`, `ADD … TO`, `SUBTRACT … FROM`, `STOP RUN`. Other lines become review notes. Review all output before use.
- **Limits:** requests over 1.2 MB get `413`; the newest 100 projects are kept.

## Errors

Errors are `{"detail": "message"}`; the frontend shows the message as-is. Classes are in [`errors.py`](src/legacylift/errors.py).

| Status | Cause |
| --- | --- |
| 400 | Bad file, file count, or name (`InvalidInputError`); step run too early (`ProjectStateError`); no `PROGRAM-ID` or `PROCEDURE DIVISION` (`ConversionError`) |
| 404 | Unknown project, file, or run (`NotFoundError`) |
| 413 | Request body too large |
| 422 | Missing or invalid field, such as an empty `name` |

## Settings

Environment variables, or `backend/.env` (copy [`.env.example`](.env.example)). Environment variables win.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEGACYLIFT_CORS_ORIGINS` | none | Extra frontend origins, comma-separated. Local Vite and `https://aadituh.github.io` are always allowed. |
| `LEGACYLIFT_DATA_DIR` | `data/projects` | Where projects are saved as `<id>.json` (plus `last_id.txt`, the ID counter), relative to where uvicorn starts. Git ignores `backend/data/`. Render resets it on redeploy. |
| `LEGACYLIFT_MAX_PROJECTS` | `100` | Projects kept; the oldest is deleted first. |
| `LEGACYLIFT_MAX_REQUEST_BYTES` | `1200000` | Largest request body. |
| `LEGACYLIFT_COBC_PATH` | unset | Optional path to GnuCOBOL `cobc` for verify. Otherwise `cobc` must be on PATH. |

## Code layout

A request goes **router → service → storage or converter**.

```text
src/legacylift/
├── main.py           builds the app: size limit, CORS, error handler, routers
├── config.py         Settings
├── errors.py         error classes and their HTTP status
├── models.py         stored data: Project, SourceFile, Run, enums
├── schemas.py        request and response bodies
├── storage.py        ProjectStore: memory + one JSON file per project, project IDs
├── dependencies.py   ProjectServiceDep; ProjectDep (loads the project or 404)
├── sample_data.py    files for the demo project
├── data/             sample COBOL bank (programs, copybooks, .dat files)
├── routers/          HTTP only: convert.py, projects.py
├── responses.py      `.py` download responses
├── services/         rules: uploads.py, conversion.py, projects.py, batch_downloads.py
└── cobol/
    ├── converter.py     translate_program(): COBOL subset → Python
    ├── gnucobol.py      compile/run programs with cobc
    └── equivalence.py   compare GnuCOBOL stdout to generated Python
```

### Verify / GnuCOBOL

`POST /api/projects/{id}/verify` (after convert) compiles each `.cbl`/`.cob` with [GnuCOBOL](https://gnucobol.sourceforge.io/) (`cobc -x -free`), runs it, runs the matching Python draft, and requires **exact** stdout equality. Copybooks in the project are placed beside the program for `COPY`.

| Status | Meaning |
| --- | --- |
| `verified` | Every program matched (`passed: true`) |
| `mismatch` | At least one differed or failed (`passed: false`) |
| `not_verified` | `cobc` not found (`passed: null`) |


Tests are in [`tests/`](tests/); pytest also runs the examples in docstrings.

## Where new work goes

| Task | Where |
| --- | --- |
| A COBOL statement | `translate_statement()` in `cobol/converter.py`, plus a test that runs the output |
| Dependency analysis | New modules in `cobol/`, called from `ProjectService.analyze()` |
| A route | `routers/`, with bodies in `schemas.py` and logic in `services/` |
| An error | Subclass `LegacyLiftError`; set `status_code` if it isn't 400 |
| PostgreSQL | A store with `ProjectStore`'s methods (`get`, `add`, `save`) |

See also: [changelog](docs/CHANGELOG.md), [developer guide](../docs/developer.md), [`prototype/`](prototype/README.md) (research code the API doesn't use).
