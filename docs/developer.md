# Developer guide

The [root README](../README.md) has local run commands. The React app talks to FastAPI for both batch conversion and project conversion. Both paths use [`converter.py`](../backend/src/legacylift/converter.py).

## Current request path

1. On load, [`App.jsx`](../frontend/app/src/App.jsx) probes `/health` through [`api.js`](../frontend/app/src/api.js) and enables Convert only when the API is up.
2. **Batch (file picker / Load sample):** `POST /api/convert` with multipart field `files` (1–5 `.cbl`/`.cob`). Handled by [`routers/legacy.py`](../backend/src/legacylift/routers/legacy.py).
3. **Project:** `POST /api/projects` → `POST /api/projects/{id}/files` → `POST /api/projects/{id}/convert`. For a ready-made Postman example, call `POST /api/projects/demo` instead of creating and uploading files. Handled by [`routers/projects.py`](../backend/src/legacylift/routers/projects.py) and [`services/projects.py`](../backend/src/legacylift/services/projects.py).
4. Each COBOL program is converted by [`converter.py`](../backend/src/legacylift/converter.py). The API returns Python drafts and review notes; the browser displays them and downloads the selected `.py` file.

Local Vite proxies `/api` and `/health` to port 8000. The converter handles a small subset of COBOL. Unsupported lines become `TODO` comments and review notes; generated code requires review.

## Where to edit

| Change | File |
| --- | --- |
| Frontend controls and display | [`frontend/app/src/App.jsx`](../frontend/app/src/App.jsx) |
| Frontend HTTP calls | [`frontend/app/src/api.js`](../frontend/app/src/api.js) |
| Legacy upload route | [`backend/src/legacylift/routers/legacy.py`](../backend/src/legacylift/routers/legacy.py) |
| Project routes and HTTP errors | [`backend/src/legacylift/routers/projects.py`](../backend/src/legacylift/routers/projects.py) |
| Project upload and conversion workflow | [`backend/src/legacylift/services/projects.py`](../backend/src/legacylift/services/projects.py) |
| Built-in Postman sample files | [`backend/src/legacylift/sample_data.py`](../backend/src/legacylift/sample_data.py) |
| JSON request and response shapes | [`backend/src/legacylift/schemas/projects.py`](../backend/src/legacylift/schemas/projects.py) |
| COBOL conversion rules | [`backend/src/legacylift/converter.py`](../backend/src/legacylift/converter.py) |

Add a focused test under [`backend/tests/`](../backend/tests/) when changing API behavior or a conversion rule. The older [`backend/prototype/`](../backend/prototype/) is research code and is not imported by the running app.

The sample project is created only when requested and gets a new ID each time. `analyze` reports file counts without dependency analysis. `verify` reports `not_verified` with `passed: null`; it does not compare COBOL and Python output. Both calls appear in `/runs` so teammates can test the route sequence without mistaking placeholders for completed features.

## Configuration and hosting

Vite forwards local `/api` requests to port 8000. For a hosted frontend, set `VITE_API_URL` to the backend's public HTTPS origin and allow the frontend origin with `LEGACYLIFT_CORS_ORIGINS` on the backend. The backend does not load `.env` files automatically. GitHub Pages hosts the static frontend and course site; it cannot run FastAPI. See [GitHub Pages in the root README](../README.md#github-pages) for the deployment steps.
