# Changelog — LegacyLift Backend

Each entry describes the code at that time. The [backend README](../README.md) describes it now.

## Unreleased

### Added

- `POST /api/auth/register`, `POST /api/auth/login`, and `GET /api/auth/me`. Passwords are Argon2 hashes (`pwdlib`); tokens are JWTs (`PyJWT`) signed with `LEGACYLIFT_TOKEN_SECRET` (set on Render, listed in `.env.example`, never committed). A used email is 409; a weak password is 422; a wrong email or password is the same 401. Project routes call `current_user` only when `LEGACYLIFT_REQUIRE_LOGIN` is true (default false). Accounts are stored in `users` (`database/schema.sql`) and, without a database, in `users.json`.
- Recorded GnuCOBOL output for BANKMAIN (`tests/data/recorded/bank/`: sample, normal, overdraft, and closed-account cases) and `scripts/record_cobol_output.py` to re-record it in the runner image. `tests/test_recorded_output.py` checks the record widths and, where `cobc` is installed, that GnuCOBOL still prints the recorded output.
- Demo 2 walkthrough ([`docs/walkthrough.md`](../../docs/walkthrough.md)): `MONTHEND.cbl` and `FEERATES.cpy` in `src/legacylift/data/`, with recorded GnuCOBOL output in `tests/data/recorded/MONTHEND.out`.
- `database/compose-init.sql`: Compose creates a local stand-in for Neon Auth's `neon_auth."user"` table, so `database/schema.sql` applies to the local database and the API starts.
- Runner container (`backend/runner.Dockerfile`, `legacylift.runner`): GnuCOBOL and Python behind `POST /run/cobol` and `POST /run/python`, each run in its own temporary folder with a time limit and an output limit. Compose service `runner` on an internal network with only the API, read-only, no capabilities, non-root, memory and process limits.
- Converter (issue #20): sample-bank constructs — groups as dicts, level `88` / `SET … TO TRUE`, `OCCURS` lists with 1-based indexes, `PERFORM UNTIL` / `VARYING`, `IF`/`EVALUATE`, `CALL "X" USING …`, `PROCEDURE DIVISION USING` callees, and `COPY` expansion from project copybooks. File I/O, edited PICs, and `COMPUTE ROUNDED` stay as review notes. Covered by `tests/test_converter.py` (issue #20 cases).
- Converter (issue #22): programs beyond the sample bank — group/`05` fields, `PIC …V…` decimals, paragraphs/`PERFORM`/`PERFORM … THRU`, `COMPUTE`, `MULTIPLY`/`DIVIDE`. Unsupported lines stay as review notes; drafts still run. Covered by `tests/test_converter.py` (`employee_payroll`, `simple_account`).
- `backend/Dockerfile` and `docker-compose.yml`: `docker compose up --build` starts PostgreSQL, the API (waits for the database), and the web app on port 8080.
- `POST /api/projects/{id}/verify` compiles each program with GnuCOBOL (`cobc`), runs it, compares stdout to the generated Python, and returns per-file results (`verified` / `mismatch` / `not_verified` if `cobc` is missing). Optional `LEGACYLIFT_COBC_PATH`.
- PostgreSQL storage: when `DATABASE_URL` is set, projects, files, and runs are stored in Neon (`neon_store.py`, tables in `database/schema.sql`). Without it, projects are saved as JSON files as before.
- `run_and_verify_python` and `translate_and_verify` in the converter: run a generated draft and compare what it prints with the expected text.
- `GET /api/projects/{id}/runs/{run_id}/files/{name}` downloads one saved `.py` file.
- `POST /api/convert` returns `download_id`. `GET /api/convert/{download_id}/files/{name}` downloads that batch file until the API restarts.
- `GET /api/projects`: every project, newest first, with file counts and its last run.
- `DELETE /api/projects/{id}` and `DELETE /api/projects/{id}/files/{file_id}` (204). CORS now allows `DELETE`.
- Converter: `PIC 99`/`PIC XX` style pictures, and doubled quotes inside literals (`"It""s"`).

### Changed

- Project routes store the Neon Auth user id (`sub`) on `projects.owner_id` when the request sends that user's EdDSA token. The token is checked against the Neon Auth JWKS. `projects.owner_id` references `neon_auth."user"`. `LEGACYLIFT_REQUIRE_LOGIN` still decides whether a missing token is rejected.
- Verify runs in the runner container: each main program compiles with the programs it calls, both COBOL and Python get the project's `.dat` files, and each file in the response adds `diff`. Off unless `LEGACYLIFT_ENABLE_RUNNER=true` (Compose turns it on); `not_verified` when off or unreachable. Called programs get no check of their own. `LEGACYLIFT_COBC_PATH` is removed.
- Short IDs: projects are `"1"`, `"2"`, …; files and runs are numbered within their project. IDs are never reused (the project counter is saved in `last_id.txt`). Projects saved with the old long IDs still load.
- `MOVE`/`ADD`/`SUBTRACT` lines are read by splitting on spaces; a 100 KB line converts in well under a second.
- Upload and convert routes run conversion and saving in a worker thread, so other requests keep answering.
- Fields after `LINKAGE SECTION` (or any later data section) become review notes instead of local variables.
- File names longer than 255 characters or with control characters are rejected (400).
- The demo project's `order.cpy` and `orders.dat` now describe the same 24-character record.
- Internal cleanup with no change to routes or JSON: `conversion_status` moved to `services/conversion.py`, the accepted extensions live once in `services/uploads.py`, and the converter compiles its `MOVE`/`ADD`/`SUBTRACT` patterns once.
- Shorter backend README; shorter tests (table-driven); every module docstring says what the module does and what it connects to.

### Fixed

- A deleted project stays deleted, even if a request on it finishes afterwards.

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
