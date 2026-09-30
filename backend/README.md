# LegacyLift backend

The FastAPI service has two paths: `/api/convert` serves the current React demo, and `/api/projects` is the new project-based API. Both use the same limited COBOL-to-Python converter.

## Run

From `backend/`:

```text
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

Open <http://127.0.0.1:8000/docs> to try the API. Run the tests with `uv run --frozen python -m unittest discover -s tests -v`.

## Project routes

| Route | Current behavior |
| --- | --- |
| `POST /api/projects` | Create a project with `{"name":"Demo"}`. |
| `GET /api/projects/{id}` | Return its files and contents. |
| `POST /api/projects/{id}/files` | Upload files under multipart field `files`. |
| `POST /api/projects/{id}/convert` | Return Python drafts and `draft` or `review_required` status. |
| `GET /api/projects/{id}/runs` | Return conversion run summaries. |
| `POST /api/projects/{id}/analyze` | HTTP 501; analysis is not built. |
| `POST /api/projects/{id}/verify` | HTTP 501; verification is not built. |

Projects accept up to 10 UTF-8 `.cbl`, `.cob`, `.cpy`, or `.dat` files, each at most 100 KB. Conversion uses only `.cbl` and `.cob`; copybooks and data files are stored but not interpreted. The converter supports simple flat fields and `DISPLAY`, `MOVE`, `ADD`, `SUBTRACT`, and `STOP RUN`. Its output is a draft, even when there are no review notes.

Projects and runs live in memory and disappear when the server restarts. The React app uses both paths: file-picker **Convert files** calls `/api/convert`, and **Convert project** calls `/api/projects/{id}/convert` after create/upload. Both share `legacylift.converter`.

## Code layout

`src/legacylift/main.py` assembles the app. `routers/` handles HTTP, `schemas/` defines JSON, `models/` holds internal data, `services/` handles the workflow, and `repositories/` stores projects in memory. `dependencies.py` supplies the service to routes. The older `prototype/` is separate from the running API.

Set `LEGACYLIFT_CORS_ORIGINS` for other frontend origins; the default allows local Vite on port 5173. The service reads environment variables directly and does not load `.env` files automatically.
