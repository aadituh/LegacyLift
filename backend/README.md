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
| `POST /api/auth/register` | `{"email", "password", "display_name"}` | New account without the password or its hash (201). Used email is 409. A weak password is 422 |
| `POST /api/auth/login` | `{"email", "password"}` | `{"token", "token_type": "bearer", "expires_in"}`. A wrong email or password is the same 401 |
| `GET /api/auth/me` | `Authorization: Bearer <token>` | The account for that token. Missing, wrong, or expired token is 401 |
| `POST /api/convert` | 1–5 `.cbl`/`.cob` files in multipart field `files` | Python for each file, plus `download_id`. Not saved as a project |
| `GET /api/projects` | none | Every project, newest first: id, name, file counts, last run (no file contents) |
| `POST /api/projects` | `{"name": "Demo"}` | New empty project (201) |
| `POST /api/projects/demo` | none | New project with 3 sample files (201) |
| `GET /api/projects/{id}` | none | The project and its files |
| `DELETE /api/projects/{id}` | none | Deletes the project, its files, and its runs (204) |
| `POST /api/projects/{id}/files` | files in multipart field `files` | The files that were added |
| `DELETE /api/projects/{id}/files/{file_id}` | none | Removes one file (204); saved runs keep their results |
| `POST /api/projects/{id}/analyze` | none | File counts plus COPY/CALL/PERFORM `dependencies` and `unresolved` (status `analyzed`) |
| `POST /api/projects/{id}/convert` | none | Python for each program, saved as a run |
| `POST /api/projects/{id}/verify` | none | Run each main program as COBOL and as Python in the runner and compare stdout: `verified` / `mismatch` / `not_verified` (runner off or unreachable) |
| `GET /api/projects/{id}/runs` | none | All runs, oldest first, without their Python |
| `GET /api/projects/{id}/runs/{run_id}` | none | One run; a convert run includes its Python |
| `GET /api/projects/{id}/runs/{run_id}/files/{name}` | none | One saved `.py` file (`Content-Disposition: attachment`) |
| `GET /api/convert/{download_id}/files/{name}` | none | One batch `.py` file, until the API restarts |

IDs are short numbers as text: projects `"1"`, `"2"`, … across the API; files and runs `"1"`, `"2"`, … within their project. IDs are never reused.

Convert status: `review_required` (some lines became `# TODO` notes) or `draft` (every line converted, not yet verified). To reopen a project: `GET /api/projects`, then `GET /api/projects/{id}`; to show its last translation, fetch `/runs`, then the last `convert` run's `/runs/{run_id}`.

## Rules

- **Files:** up to 10 per project (`.cbl`/`.cob`, `.cpy`, `.dat`), UTF-8 text, at most 100 KB each, names unique ignoring case and at most 255 printable characters. If one file fails, none are added.
- **Converter:** Elementary `WORKING-STORAGE` / `LINKAGE` fields (levels `01`–`49`/`77`) with `PIC X`/`9` (optional `S`, `V` decimals as float); groups as dicts; `OCCURS` as lists with 1-based subscripts; level `88` conditions and `SET … TO TRUE`; `COPY` expansion when project copybooks are present; `DISPLAY`, `MOVE`/`ADD`/`SUBTRACT`, `MULTIPLY`/`DIVIDE`, simple `COMPUTE` (no `ROUNDED`); paragraphs and `PERFORM` / `PERFORM … THRU` / `UNTIL` / `VARYING`; `IF`/`EVALUATE`; `CALL "X" USING …`; `STOP RUN`/`GOBACK`. Other lines (file I/O, edited PICs, etc.) become review notes. Review all output before use.
- **Limits:** requests over 1.2 MB get `413`; the newest 100 projects are kept.

## Errors

Errors are `{"detail": "message"}`; the frontend shows the message as-is. Classes are in [`errors.py`](src/legacylift/errors.py).

| Status | Cause |
| --- | --- |
| 400 | Bad file, file count, or name (`InvalidInputError`); step run too early (`ProjectStateError`); no `PROGRAM-ID` or `PROCEDURE DIVISION` (`ConversionError`); login while `LEGACYLIFT_TOKEN_SECRET` is unset |
| 401 | Missing, wrong, or expired login token (`UnauthenticatedError`); wrong email or password on login |
| 404 | Unknown project, file, or run (`NotFoundError`) |
| 409 | Email already registered (`ConflictError`) |
| 413 | Request body too large |
| 422 | Missing or invalid field, such as an empty `name` or a weak password (`InputError`) |

## Settings

Environment variables, or `backend/.env` (copy [`.env.example`](.env.example)). Environment variables win.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEGACYLIFT_CORS_ORIGINS` | none | Extra frontend origins, comma-separated. Local Vite and `https://aadituh.github.io` are always allowed. |
| `DATABASE_URL` | none | Neon PostgreSQL connection string. When set, projects, files, and runs are stored in the database, and [`database/schema.sql`](../database/schema.sql) (repo root) is applied at startup. |
| `LEGACYLIFT_DATA_DIR` | `data/projects` | Used when `DATABASE_URL` is unset: projects are saved as `<id>.json` (plus `last_id.txt`, the ID counter), relative to where uvicorn starts. Git ignores `backend/data/`. Render resets it on redeploy. |
| `LEGACYLIFT_MAX_PROJECTS` | `100` | Projects kept; the oldest is deleted first. |
| `LEGACYLIFT_MAX_REQUEST_BYTES` | `1200000` | Largest request body. |
| `LEGACYLIFT_ENABLE_RUNNER` | `false` | Lets verify run code in the runner container. Compose sets it to `true`. |
| `LEGACYLIFT_RUNNER_URL` | `http://runner:8001` | The runner container's address. |
| `LEGACYLIFT_TOKEN_SECRET` | unset | HMAC secret for login tokens. Set it on Render and in `backend/.env`. Never commit it. Login cannot sign a token until it is set. |
| `LEGACYLIFT_TOKEN_TTL_SECONDS` | `86400` | How long a login token stays valid (24 hours). |
| `LEGACYLIFT_REQUIRE_LOGIN` | `false` | When `true`, every `/api/projects` route requires `Authorization: Bearer <token>`. |
| `LEGACYLIFT_NEON_AUTH_URL` | this project's Neon Auth URL | JWKS base URL. An EdDSA bearer token from the web app is checked here, and its `sub` is saved as `projects.owner_id`. |

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
├── neon_store.py     NeonProjectStore: the same methods on Neon PostgreSQL
├── dependencies.py   ProjectServiceDep; ProjectDep (loads the project or 404)
├── sample_data.py    files for the demo project
├── data/             sample COBOL bank (programs, copybooks, .dat files)
├── routers/          HTTP only: auth.py, convert.py, projects.py
├── responses.py      `.py` download responses
├── services/         rules: uploads.py, conversion.py, projects.py, auth.py, verification.py, batch_downloads.py
├── runner/           runs COBOL and Python in the runner container: sandbox.py, server.py
└── cobol/
    ├── parser.py        parse_program(): divisions, fields, paragraphs, COPY/CALL
    ├── dependencies.py  find_dependencies(): COPY/CALL/PERFORM links + unresolved
    ├── runtime.py       cobol_number / cobol_text / display_number (DISPLAY semantics)
    ├── converter.py     translate_program(): COBOL subset → Python
    ├── gnucobol.py      compile/run one program with a local cobc (not used by verify)
    └── equivalence.py   compare that run with in-process Python (not used by verify)
```

### Verify

`POST /api/projects/{id}/verify` (after convert) uses the [runner container](#runner-container). For each main program (one that no other program `CALL`s) it compiles the program with the programs it calls and the project's copybooks, runs it with the project's `.dat` files, runs the generated Python with the same files, and compares stdout exactly (only `
` vs `
` is ignored). Called programs get no check of their own.

Each entry in `files` has `equivalent`, `cobol_stdout`, `python_stdout`, `diff` (unified diff, empty when they match), and `error`.

| Status | Meaning |
| --- | --- |
| `verified` | Every program matched (`passed: true`) |
| `mismatch` | At least one differed, failed to compile, crashed, or hit a limit (`passed: false`) |
| `not_verified` | Runner off (`LEGACYLIFT_ENABLE_RUNNER`) or unreachable (`passed: null`) |

### Login

Agreed with the accounts table (#30), the login page (#15), and the sign-up page (#32):

| Choice | Agreement |
| --- | --- |
| Token | JWT, HS256, `Authorization: Bearer <token>`. Default lifetime 24 hours |
| Where the page keeps it | `localStorage` key `legacylift-token` |
| Password | 8 to 128 characters, at least one letter and one number. Message: `Password must be 8 to 128 characters and include a letter and a number.` |
| Email | Stored lowercase. The same address cannot register twice |
| Display name | 1 to 100 characters |
| Routes that need login | `/api/projects` requires a token only when `LEGACYLIFT_REQUIRE_LOGIN=true`. A Neon Auth token on those routes still sets `projects.owner_id` and limits the list to that account. `/api/auth/*`, `/api/convert`, `/health` stay open. Projects created with no token have no owner |
| Wrong login | Unknown email and wrong password both return `{"detail": "Invalid email or password."}` |
| Expired token | `{"detail": "Please log in again."}` |

The password is hashed with Argon2 and is never stored or logged. The response from register and `/me` is `id`, `email`, `display_name`, `created_at`.

### Runner container

[`runner.Dockerfile`](runner.Dockerfile) builds an image with GnuCOBOL 3.1.2 and Python that serves `legacylift.runner.server` on port 8001. Compose starts it as `runner` on an internal network that only the API joins: no internet, read-only file system, no Linux capabilities, user `runner` (uid 1001), 512 MB memory, 64 processes.

| Route | Body | Result |
| --- | --- | --- |
| `GET /health` | none | `{"status": "ok"}` |
| `POST /run/cobol` | `programs`, `main`, optional `copybooks`, `data_files` (each `{"NAME": "text"}`) | `ok`, `stage` (`compile`/`run`), `exit_code`, `stdout`, `stderr`, `timed_out`, `output_truncated` |
| `POST /run/python` | `scripts`, `main`, optional `data_files` | Same fields |

Each run gets a new temporary folder: COBOL compiles with `cobc -x -I <copybooks> <main> <called programs>` (fixed format), data files sit in the working folder, and Python runs as `python -I`. Settings: `RUNNER_TIMEOUT_SECONDS` (10), `RUNNER_MAX_OUTPUT_BYTES` (256000), `RUNNER_MAX_REQUEST_BYTES` (2000000), `RUNNER_PORT` (8001).

Build and start only the runner: `docker compose up --build runner`. Tests that need `cobc` are skipped when it isn't installed.

### Recorded COBOL output

[`tests/data/recorded/`](tests/data/recorded/) holds what GnuCOBOL printed: `FEESCHED.out`, and `bank/<case>/BANKMAIN.out` for the cases `sample` (the files in `src/legacylift/data/`), `normal`, `overdraft`, and `closed` (each with its own `accounts.dat` and `transactions.dat`). Re-record after changing a case or a sample program, from the repository root:

```bash
docker compose run --rm --no-deps -v ./backend:/backend runner python /backend/scripts/record_cobol_output.py
```

Tests are in [`tests/`](tests/); pytest also runs the examples in docstrings.

## Where new work goes

| Task | Where |
| --- | --- |
| A COBOL statement | `translate_statement()` in `cobol/converter.py`, plus a test that runs the output |
| Dependency analysis | New modules in `cobol/`, called from `ProjectService.analyze()` |
| A route | `routers/`, with bodies in `schemas.py` and logic in `services/` |
| An error | Subclass `LegacyLiftError`; set `status_code` if it isn't 400 |
| A table or column | [`database/schema.sql`](../database/schema.sql) and the SQL in `neon_store.py` |

See also: [changelog](docs/CHANGELOG.md), [developer guide](../docs/developer.md), [`prototype/`](prototype/README.md) (research code the API doesn't use).
