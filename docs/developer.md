# Developer guide

The [root README](../README.md) has local run commands. The React page currently calls the stateless `/api/convert` route. The separate [project API](../backend/README.md#project-routes) is ready for a future frontend view.

## Current request path

1. [`App.jsx`](../frontend/app/src/App.jsx) selects files and calls [`api.js`](../frontend/app/src/api.js).
2. [`routers/legacy.py`](../backend/src/legacylift/routers/legacy.py) validates the upload and calls [`converter.py`](../backend/src/legacylift/converter.py) once per COBOL file.
3. The API returns Python drafts and review notes. The browser displays them and downloads the selected `.py` file.

The converter handles a small subset of COBOL. Unsupported lines become `TODO` comments and review notes; generated code requires review.

## Where to edit

| Change | File |
| --- | --- |
| Frontend controls and display | [`frontend/app/src/App.jsx`](../frontend/app/src/App.jsx) |
| Frontend HTTP calls | [`frontend/app/src/api.js`](../frontend/app/src/api.js) |
| Legacy upload route | [`backend/src/legacylift/routers/legacy.py`](../backend/src/legacylift/routers/legacy.py) |
| Project routes and HTTP errors | [`backend/src/legacylift/routers/projects.py`](../backend/src/legacylift/routers/projects.py) |
| Project upload and conversion workflow | [`backend/src/legacylift/services/projects.py`](../backend/src/legacylift/services/projects.py) |
| JSON request and response shapes | [`backend/src/legacylift/schemas/projects.py`](../backend/src/legacylift/schemas/projects.py) |
| COBOL conversion rules | [`backend/src/legacylift/converter.py`](../backend/src/legacylift/converter.py) |

Add a focused test under [`backend/tests/`](../backend/tests/) when changing API behavior or a conversion rule. The older [`backend/prototype/`](../backend/prototype/) is research code and is not imported by the running app.

## Configuration and hosting

Vite forwards local `/api` requests to port 8000. For a hosted frontend, set `VITE_API_URL` to the backend's public HTTPS origin and allow the frontend origin with `LEGACYLIFT_CORS_ORIGINS` on the backend. The backend does not load `.env` files automatically. GitHub Pages hosts the static frontend and course site; it cannot run FastAPI. See [GitHub Pages in the root README](../README.md#github-pages) for the deployment steps.
