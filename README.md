# LegacyLift — CS410

A tool for analyzing and converting legacy COBOL codebases to Python, plus the
team's course website.

The current demo lets you select COBOL files in a React page, send them to a FastAPI service, review draft Python, and download each result. The converter supports a small, explicit set of COBOL statements. It adds `TODO` comments and review notes for lines it cannot convert.

## Run locally

Install [uv](https://docs.astral.sh/uv/) and a Node.js version supported by the `frontend/app` Vite dependencies. Open **two terminals** at the repository root, then use the commands for your system.

### Windows (PowerShell)

Terminal 1 — API:

```powershell
cd backend
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

Terminal 2 — React app:

```powershell
cd frontend/app
npm.cmd ci
npm.cmd run dev
```

### macOS (Terminal)

Terminal 1 — API:

```bash
cd backend
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

Terminal 2 — React app:

```bash
cd frontend/app
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Click **Load sample**, **Convert files**, and **Download .py** to try the full path. The Vite development server forwards `/api` requests to <http://127.0.0.1:8000>. The API health check is at <http://127.0.0.1:8000/health>; interactive API docs are at <http://127.0.0.1:8000/docs>.

## Repository map

| Path | Purpose |
| --- | --- |
| [`frontend/app/`](frontend/app/) | React and Vite upload, preview, and download app |
| [`backend/src/legacylift/`](backend/src/legacylift/) | Active FastAPI route and small rule-based converter |
| [`backend/tests/`](backend/tests/) | API conversion checks |
| [`backend/prototype/`](backend/prototype/) | Earlier research scripts and notebooks; separate from the active app |
| [`docs/`](docs/) | Static course website copied to `/course/` on Pages, plus the [developer guide](docs/developer.md) |
| [`TODO.MD`](TODO.MD) | Longer-term team ideas; the running demo is intentionally smaller |

## GitHub Pages

The [Pages workflow](.github/workflows/pages.yml) builds the React app for <https://aadituh.github.io/LegacyLift/> and includes the course website at <https://aadituh.github.io/LegacyLift/course/>. In GitHub, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**, then push this branch to `main` or run the workflow from the Actions tab. The workflow keeps generated files out of Git.

GitHub Pages hosts only static files. Until the backend is deployed, the app shows its sample and upload interface but disables conversion. When the backend has a public HTTPS URL, add a repository **Actions variable** named `VITE_API_URL` with that API origin (for example, `https://api.example.com`, without `/api`), set `LEGACYLIFT_CORS_ORIGINS=https://aadituh.github.io` on the backend, and rerun the Pages workflow. See the [developer guide](docs/developer.md#configuration-and-hosting) for details.

## Check changes

Backend checks (Windows or macOS), from the repository root:

```text
cd backend
uv run --frozen python -m unittest discover -s tests -v
```

Frontend checks on Windows, from the repository root:

```powershell
cd frontend/app
npm.cmd run lint
npm.cmd run build
```

Frontend checks on macOS, from the repository root:

```bash
cd frontend/app
npm run lint
npm run build
```

The conversion is a teaching draft, not a general COBOL translator. Review generated Python and every reported line before using the output. For the file-by-file walkthrough, API shape, logs, and common changes, see [docs/developer.md](docs/developer.md).
