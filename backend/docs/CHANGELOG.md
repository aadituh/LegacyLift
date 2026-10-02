# Changelog — LegacyLift Backend

Each entry describes the code at that time. The [backend README](../README.md) describes it now.

## Backend v2 — 2026-10-01

Branch `feature/backend-v2`. Routes the React app already uses keep their fields; new fields are only added.

### Added

- Projects are saved as `data/projects/<id>.json` and reloaded at startup.
- Convert runs keep their Python; `GET /api/projects/{id}/runs/{run_id}` returns it.
- `created_at` on projects and runs.
- Limits: 413 for requests over 1.2 MB, and only the newest 100 projects are kept.
- Settings with `pydantic-settings`, from `LEGACYLIFT_*` variables or `backend/.env`.
- pytest, ruff, and `mypy --strict`, run by a GitHub Actions workflow. 68 tests, 100% coverage.
- Docstrings with `Args`/`Returns`/`Raises`/`Example` on every function; pytest runs the examples.

### Changed

- All data is Pydantic: `models.py` (stored) and `schemas.py` (request/response), replacing dataclasses and dicts.
- New layout: `cobol/converter.py`, `routers/convert.py` (was `legacy.py`), `services/` (uploads, conversion, projects), `storage.py`, `errors.py`, `config.py`.
- One error handler turns service errors into `{"detail": ...}` responses, and logs every rejected request.
- Routes load the project through `ProjectDep`, so 404 is handled in one place.
- Project changes happen one at a time, so two uploads at once can't both pass the file limit.
- Clearer names: converter functions are `translate_*` (`convert_source` → `translate_program`, `convert_statement` → `translate_statement`, `python_name` → `variable_name`), and route functions say what they do (`convert_files`, `convert_project`, `list_runs`). URLs and JSON fields are unchanged.

### Fixed

- Generated Python crashed while marked `draft` when a field was named like a Python built-in (`PRINT`), or when `MOVE` put text into a number field.
- `VALUE 007` produced invalid Python (`x = 007`).
- Decimals, text/number mixes, and unsupported `WORKING-STORAGE` lines (group items, level 88) were sometimes dropped silently. They now become review notes.
- Uploads larger than the limit were fully received before being rejected.

## Demo conversion — 2026-09-29

- Added `POST /api/convert` for small UTF-8 COBOL uploads and `GET /health`.
- Added rule-based Python drafts and review notes for unsupported lines.
- Added API checks for conversion, review notes, and bad uploads.
- Added request and rejection logs without recording source code.
- Kept the research prototype separate from the running API.

## v1 — 2026-08-25

First backend scaffold: project skeleton, tooling, and one route.

- uv project on Python 3.12, with `fastapi` and `uvicorn[standard]` locked in `uv.lock`.
- `src/legacylift/main.py` with a `create_app()` factory and a module-level `app` for uvicorn.
- `GET /` returning `{"message": "Hello from LegacyLift"}`.
- Renamed the package from `backend` to `legacylift`, because `uv_build` derives the source path from `project.name`.
