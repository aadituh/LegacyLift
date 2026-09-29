# Backend

The active backend is a small FastAPI service. It receives up to five UTF-8 `.cbl` or `.cob` files, converts a basic subset of COBOL, and sends Python drafts back in one response. It does not store uploads or require a database.

## Start and test

From this directory, on Windows PowerShell or macOS Terminal (the commands are the same):

```text
uv sync --frozen
uv run --frozen uvicorn legacylift.main:app --reload
```

Open <http://127.0.0.1:8000/docs> to inspect the API. `GET /health` returns `{"status":"ok"}`. The React app calls `POST /api/convert` with multipart form files under the field name `files`.

To run the backend checks on either system:

```text
uv run --frozen python -m unittest discover -s tests -v
```

## Where to change code

| File | Responsibility |
| --- | --- |
| [`src/legacylift/main.py`](src/legacylift/main.py) | API route, CORS, upload validation, response, and request logs |
| [`src/legacylift/converter.py`](src/legacylift/converter.py) | COBOL cleanup, supported statements, Python draft, and review notes |
| [`tests/test_convert.py`](tests/test_convert.py) | Upload and generated-output checks |
| [`pyproject.toml`](pyproject.toml) and [`uv.lock`](uv.lock) | Dependencies and locked versions |

The converter currently handles simple `01` and `77` text or whole-number fields, `DISPLAY`, `MOVE`, `ADD`, `SUBTRACT`, and `STOP RUN`. Unsupported procedure lines become `# TODO` comments in the generated file and entries in `notes`. See [the developer guide](../docs/developer.md) before adding a rule.

## Configuration and logs

Local CORS origins default to `http://localhost:5173,http://127.0.0.1:5173`. Set the `LEGACYLIFT_CORS_ORIGINS` environment variable to a comma-separated list for other frontend origins. The service reads the environment directly; it does not automatically load `.env` files. [`.env.example`](.env.example) shows the setting.

Uvicorn prints startup messages, upload counts, converted filenames with review-note counts, and rejection reasons to the terminal. Uploaded source and generated Python are not logged. Logs are for local debugging; generated files are returned to the browser rather than saved on the server.

[`prototype/`](prototype/) contains older research experiments. It is not imported by the API.
