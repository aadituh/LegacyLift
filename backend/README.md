# LegacyLift backend

The FastAPI service has two paths: `/api/convert` serves the current React demo, and `/api/projects` is the new project-based API. Both use the same limited COBOL-to-Python converter.

## Run

From `backend/`:

```text
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

Open <http://127.0.0.1:8000/> for the API welcome response or <http://127.0.0.1:8000/docs> to try the routes. Run the tests with `uv run --frozen python -m unittest discover -s tests -v`.

## Project routes

| Route | Current behavior |
| --- | --- |
| `POST /api/projects` | Create a project with `{"name":"Demo"}`. |
| `POST /api/projects/demo` | Create a fresh project with three built-in sample files; no body needed. |
| `GET /api/projects/{id}` | Return its files and contents. |
| `POST /api/projects/{id}/files` | Upload files under multipart field `files`. |
| `POST /api/projects/{id}/analyze` | Return real file counts only; dependency analysis is not built. |
| `POST /api/projects/{id}/convert` | Return Python drafts and `draft` or `review_required` status. |
| `POST /api/projects/{id}/verify` | Return `not_verified` and `passed: null` after conversion; no COBOL/Python comparison yet. |
| `GET /api/projects/{id}/runs` | Return analysis, conversion, and verification run summaries. |

## Try the project routes in Postman

1. `POST /api/projects/demo` with no body. Copy the `id` in the response. Each request creates a new project.
2. `GET /api/projects/{id}` to inspect `store_report.cbl`, `order.cpy`, and `orders.dat`.
3. `POST /api/projects/{id}/analyze` with no body to see file counts.
4. `POST /api/projects/{id}/convert` with no body to get `store_report.py`.
5. `POST /api/projects/{id}/verify` with no body to see the explicit placeholder result.
6. `GET /api/projects/{id}/runs` to see the three recorded runs.

To try uploading, use `POST /api/projects/{id}/files` with **Body → form-data**, key `files`, type **File**. Choose `backend/prototype/data/simple_account.cbl` from your checkout. Convert again to see review notes for statements outside the small supported subset. The stateless `POST /api/convert` route accepts the same file with multipart key `files` and does not need a project ID.

Projects accept up to 10 UTF-8 `.cbl`, `.cob`, `.cpy`, or `.dat` files, each at most 100 KB. Conversion uses only `.cbl` and `.cob`; copybooks and data files are stored but not interpreted. The converter supports simple flat fields and `DISPLAY`, `MOVE`, `ADD`, `SUBTRACT`, and `STOP RUN`. Its output is a draft, even when there are no review notes.

Projects and runs live in memory and disappear when the server restarts. The React app uses both paths: **Choose COBOL files** and **Load small sample** call `/api/convert`; **Load demo project** creates the larger sample through `/api/projects/demo`, then **Convert project** calls `/api/projects/{id}/convert`. Both share `legacylift.converter`. The sample project lives in [`sample_data.py`](src/legacylift/sample_data.py); it is only created when the demo route is called.

## Code layout

`src/legacylift/main.py` assembles the app. `routers/` handles HTTP, `schemas/` defines JSON, `models/` holds internal data, `services/` handles the workflow, and `repositories/` stores projects in memory. `dependencies.py` supplies the service to routes. The older `prototype/` is separate from the running API.

Local Vite on port 5173 and the LegacyLift GitHub Pages origin are allowed by default. Set `LEGACYLIFT_CORS_ORIGINS` to add other frontend origins as a comma-separated list. The service reads environment variables directly and does not load `.env` files automatically.
