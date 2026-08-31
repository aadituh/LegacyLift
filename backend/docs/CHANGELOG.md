# Changelog — LegacyLift Backend

## [v1] — 2026-08-25

First backend scaffold: project skeleton, tooling, and a single liveness
route. No feature logic yet.

### Added

- uv project pinned to Python 3.12, with `fastapi` and `uvicorn[standard]`
  locked in `uv.lock`.
- `src/legacylift/main.py` — a `create_app()` factory plus a module-level
  `app` for uvicorn to import.
- `GET /` returning `{"message": "Hello from LegacyLift"}`, verified against
  a running server.
- Empty feature packages: `core/`, `projects/`, `analysis/`, `conversion/`,
  `ai/`, and `tests/`.
- `.env.example` placeholder for environment configuration.

### Changed

- Renamed the package from `backend` to `legacylift`. `uv_build` derives the
  source path from `project.name`, so the directory and the name had to move
  together.

### Removed

- The generated `[project.scripts]` entry, which pointed at a placeholder
  `main()` superseded by the app factory.

### Fixed

- Added docstrings in `main.py`, and renamed the local `app` inside
  `create_app()` to `fastapi_app` so it no longer shadows the module-level
  `app`.

### Known issues

- Feature directories have no `__init__.py`. Each needs one before its
  modules can be imported as `legacylift.<feature>.<module>`.
- Git does not track empty directories, so the feature packages will not
  survive a clone until they contain a file.
- `pytest` is not a project dependency yet; add it with `uv add --dev pytest`
  before writing tests.
