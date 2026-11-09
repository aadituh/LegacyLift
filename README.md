# LegacyLift

LegacyLift analyzes legacy COBOL programs and converts them to Python for human review. It is the ODU CS 411W team project; the full design is in [the design presentation](docs/presentations/cs410-formal-design.pdf).

## Status

| Pipeline step | Today |
| --- | --- |
| Upload programs, copybooks, and data files | Working; saved in PostgreSQL (Neon) when `DATABASE_URL` is set, otherwise as JSON on the API's disk |
| Convert COBOL to Python | Working for a subset (fields, groups, `OCCURS`, `IF`/`EVALUATE`, `PERFORM`, `CALL`, `COPY`); other lines become `TODO` review notes. Each run is saved |
| Dependency analysis (`COPY`, `CALL`, `PERFORM`) | Working: links between files and paragraphs, plus names with no matching file |
| Verify against COBOL (GnuCOBOL) | Working with `docker compose up`: COBOL and Python run in the runner container and outputs are compared. Off elsewhere (`not_verified`) |
| Gemini + RAG | Not started |

Generated Python is a draft; review it before use.

## Quick start

### With Docker

You need [Docker](https://docs.docker.com/get-docker/) with Compose. From the repository root:

```bash
docker compose up --build
```

This starts PostgreSQL, the API, the GnuCOBOL runner, and the web app. Open <http://localhost:8080> for the web app and <http://localhost:8000/docs> for the API. Projects are kept in the `db-data` volume; `docker compose down -v` deletes them (do this once if the API stops with `schema "neon_auth" does not exist`). Stop with `Ctrl+C` or `docker compose down`.

For API accounts, set a persistent random `LEGACYLIFT_TOKEN_SECRET` in the root `.env`; or configure `NEXT_PUBLIC_NEON_AUTH_URL` for Neon accounts. See [web configuration](frontend/web/README.md).

To use AI review, put `LEGACYLIFT_GEMINI_API_KEY=<your key>` in a `.env` file at the repository root before starting.

### Without Docker

You need [uv](https://docs.astral.sh/uv/) and Node.js 24 or newer. Open two terminals at the repository root.

**Terminal 1: API** on <http://127.0.0.1:8000>

```bash
cd backend
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

**Terminal 2: web app** on <http://localhost:3000>

```bash
cd frontend/web
npm ci          # Windows PowerShell: npm.cmd ci
npm run dev     # Windows PowerShell: npm.cmd run dev
```

Configure `LEGACYLIFT_TOKEN_SECRET` for API account sign-in (or the optional Neon Auth endpoint), then create an account and sign in. In the browser: on **Upload**, click **Load demo project**; on **Convert**, click **Convert project**; on **Export**, click **Download .py**. To call the API directly, use the interactive docs at <http://127.0.0.1:8000/docs>.

## Repository map

| Path | What it holds |
| --- | --- |
| [`backend/`](backend/) | FastAPI service: routes, project workflow, COBOL converter, tests. [README](backend/README.md), [changelog](backend/docs/CHANGELOG.md) |
| [`frontend/web/`](frontend/web/) | Next.js app for uploading, converting, and downloading. [README](frontend/web/README.md) |
| [`backend/prototype/`](backend/prototype/) | Earlier research scripts shown in the design deck. The API does not use them. [README](backend/prototype/README.md) |
| [`docs/`](docs/) | Course website, design deck, the [developer guide](docs/developer.md), the [Demo 2 walkthrough](docs/walkthrough.md), and the [Demo 2 stress test](docs/demo2-stress-test.md) |
| [`TODO.MD`](TODO.MD) | Work planned for Demo 2 |
| [`docker-compose.yml`](docker-compose.yml) | Starts the database, API, runner, and web app together; images from `backend/Dockerfile`, `backend/runner.Dockerfile`, and `frontend/web/Dockerfile` |
| [`.github/workflows/`](.github/workflows/) | Backend and frontend checks, CodeQL code scanning (security and quality), dependency review, and the GitHub Pages deployment; [`dependabot.yml`](.github/dependabot.yml) sets weekly dependency updates |
| [`.editorconfig`](.editorconfig), [`.gitattributes`](.gitattributes) | Editor settings; COBOL, `.dat`, and recorded output keep LF line endings |
| [`SECURITY.md`](SECURITY.md) | How to report a vulnerability privately |

## Checks

| Where | Commands |
| --- | --- |
| `backend/` | `uv run --frozen pytest`, `uv run --frozen ruff check src tests`, `uv run --frozen ruff format --check src tests`, `uv run --frozen mypy` |
| `frontend/web/` | `npm run lint`, `npm run build` (Windows PowerShell: `npm.cmd`) |

The new frontend CI also runs typechecking, formatting, unit tests, and real-backend browser/accessibility tests. See [frontend/web/README.md](frontend/web/README.md).

On every pull request GitHub Actions runs the backend checks, the frontend checks, CodeQL, and a dependency review that fails on new dependencies with high or critical vulnerabilities.

## Merge rule

Nothing is pushed straight to `main`. Every change has its own branch and a pull request (feature work also has an issue) that a teammate reviews before the author merges it; every other member is asked to review automatically. The checks must pass first. GitHub enforces this on `main`. Steps: [CONTRIBUTING.md](CONTRIBUTING.md).

Work is tracked on the [project board](https://github.com/users/aadituh/projects/3): every issue is a user story, grouped by epic, milestone (Demo 1, Demo 2, Demo 3), and sprint.

## Hosting

| Part | Where | URL |
| --- | --- | --- |
| Web app | Next.js Node server (Docker; Vercel-ready) | Local: <http://localhost:8080>; hosted deployment is not configured |
| Course website | GitHub Pages | <https://aadituh.github.io/LegacyLift/course/> |
| API | Render | <https://legacylift-api.onrender.com> |

The course site redeploys through Pages on changes to `docs/` on `main`. See [Configuration and hosting](docs/developer.md#configuration-and-hosting) for settings.
