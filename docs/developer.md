# Developer guide

How the frontend and backend connect, where to make changes, and how the app is hosted. Commands are in the [root README](../README.md#quick-start); routes and rules are in the [backend README](../backend/README.md).

## How a conversion travels

```text
App.jsx ──api.js──▶ FastAPI router ──▶ service ──▶ cobol/converter.py
   ▲                                       │
   └────── JSON: Python + review notes ◀───┘
```

1. On page load, [`App.jsx`](../frontend/app/src/App.jsx) calls `GET /health` through [`api.js`](../frontend/app/src/api.js). Convert stays disabled until the API answers.
2. **Batch:** **Choose COBOL files** or **Load small sample**, then **Convert files**, calls `POST /api/convert`. Nothing is saved.
3. **Project:** **Create project** or **Load demo project** creates a project, **Upload project files** adds files, and **Convert project** calls `POST /api/projects/{id}/convert`. The result is saved.
4. The app shows COBOL and Python side by side with review notes. **Download .py** saves the file.
5. Errors come back as `{"detail": "message"}`, and `api.js` shows the message.

The browser checks files for quick feedback; the backend checks everything again.

## Where to edit

| Change | Where |
| --- | --- |
| Screen, buttons, display | [`frontend/app/src/App.jsx`](../frontend/app/src/App.jsx) |
| Frontend HTTP calls | [`frontend/app/src/api.js`](../frontend/app/src/api.js) |
| Anything in the backend | See the [backend code layout](../backend/README.md#code-layout) |

If you change a route's JSON, update `api.js` and `App.jsx` in the same pull request.

## Making a change

1. Branch from `main`.
2. Add or update a test in [`backend/tests/`](../backend/tests/) for any backend change.
3. Run the checks: `pytest`, `ruff`, and `mypy` in `backend/`; `npm run lint` and `npm run build` in `frontend/app/`.
4. Add a line to the [backend changelog](../backend/docs/CHANGELOG.md).
5. Open a pull request. GitHub Actions runs the backend checks.

## Configuration and hosting

| Piece | Host | Notes |
| --- | --- | --- |
| Web app | GitHub Pages | [`pages.yml`](../.github/workflows/pages.yml) builds it on every push to `main` and copies `docs/` to `/course/`. In GitHub, **Settings → Pages → Source** must be **GitHub Actions**. |
| API address used by the web app | Actions variable `VITE_API_URL` | The API's HTTPS origin, without `/api`. Default: `https://legacylift-api.onrender.com`. |
| API | Render | Set up in the Render dashboard. Saved projects are lost on every redeploy or restart. |
| Allowed frontend origins | `LEGACYLIFT_CORS_ORIGINS` on the API | Local Vite and `https://aadituh.github.io` are always allowed. |

Locally, Vite forwards `/api` and `/health` to `http://127.0.0.1:8000` ([`vite.config.js`](../frontend/app/vite.config.js)), so no address or CORS setup is needed.
