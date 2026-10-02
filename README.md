# LegacyLift

LegacyLift analyzes legacy COBOL programs and converts them to Python for human review. It is the ODU CS 411W team project; the full design is in [the design presentation](docs/Formal%20Design%20Presentation%20Final.pdf).

## Status

| Pipeline step (from the design) | Today |
| --- | --- |
| Upload COBOL programs, copybooks, and data files | Working; saved as JSON files on the API's disk |
| Keep translations after a page reload | Working; each convert run saves its Python |
| Convert COBOL to Python | Working for a small subset; other lines become `TODO` review notes |
| Dependency analysis (`COPY`, `CALL`, `PERFORM`) | Placeholder: counts files only |
| Verify Python output against COBOL (GnuCOBOL) | Placeholder: returns `not_verified` |
| PostgreSQL storage | Not started |
| Gemini + RAG translation | Not started |

All generated Python is a draft. Review it before use.

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Node.js 24. Open two terminals at the repository root.

**Terminal 1: API** on <http://127.0.0.1:8000>

```bash
cd backend
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

**Terminal 2: web app** on <http://127.0.0.1:5173>

```bash
cd frontend/app
npm ci          # Windows PowerShell: npm.cmd ci
npm run dev     # Windows PowerShell: npm.cmd run dev
```

In the browser: on **Upload**, click **Load demo project**; on **Convert**, click **Convert project**; on **Export**, click **Download .py**. To call the API directly, use the interactive docs at <http://127.0.0.1:8000/docs>.

## Repository map

| Path | What it holds |
| --- | --- |
| [`backend/`](backend/) | FastAPI service: routes, project workflow, COBOL converter, tests. [README](backend/README.md), [changelog](backend/docs/CHANGELOG.md) |
| [`frontend/app/`](frontend/app/) | React + Vite app for uploading, converting, and downloading. [README](frontend/app/README.md) |
| [`backend/prototype/`](backend/prototype/) | Earlier research scripts shown in the design deck. The API does not use them. [README](backend/prototype/README.md) |
| [`docs/`](docs/) | Course website, design deck, and the [developer guide](docs/developer.md) |
| [`TODO.MD`](TODO.MD) | Work planned for Demo 2 |
| [`.github/workflows/`](.github/workflows/) | Backend checks, and the GitHub Pages deployment |

## Checks

| Where | Commands |
| --- | --- |
| `backend/` | `uv run --frozen pytest`, `uv run --frozen ruff check src tests`, `uv run --frozen mypy` |
| `frontend/app/` | `npm run lint`, `npm run build` (Windows PowerShell: `npm.cmd`) |

GitHub Actions runs the backend checks on every change under `backend/`.

## Hosting

| Part | Where | URL |
| --- | --- | --- |
| Web app | GitHub Pages | <https://aadituh.github.io/LegacyLift/> |
| Course website | GitHub Pages | <https://aadituh.github.io/LegacyLift/course/> |
| API | Render | <https://legacylift-api.onrender.com> |

Pages redeploys on every push to `main`. See [Configuration and hosting](docs/developer.md#configuration-and-hosting) for settings.
