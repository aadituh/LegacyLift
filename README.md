# LegacyLift — CS410

A tool for analyzing and converting legacy COBOL codebases to Python, plus the
team's course website.

## Repository layout

| Path | Contents |
|---|---|
| [`backend/`](backend/) | FastAPI service — analysis and conversion API |
| [`docs/`](docs/) | Static team website published via GitHub Pages |
| [`TODO.MD`](TODO.MD) | Outstanding work for the team website |

> **Note:** `docs/` holds the *published website*, not project documentation.
> GitHub Pages serves this directory directly. Backend documentation lives in
> [`backend/docs/`](backend/docs/).

## Backend

FastAPI service managed with [uv](https://docs.astral.sh/uv/), on Python 3.12.

```bash
cd backend
uv sync
uv run uvicorn legacylift.main:app --reload
```

Setup, layout, and troubleshooting: [backend/README.md](backend/README.md).
Version history: [backend/docs/CHANGELOG.md](backend/docs/CHANGELOG.md).

**Current status:** v1 scaffold — project structure and tooling are in place
with a single liveness route. Feature modules are not yet implemented.

## Website

A static site (HTML/CSS, no build step) served from `docs/` at the repository's
GitHub Pages URL. Open `docs/index.html` directly in a browser to preview
changes locally.
