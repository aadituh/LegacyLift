# Developer guide

This guide describes the **running demo**. Start with [the root README](../README.md) to launch both servers, then use this map to find the code to change. [`TODO.MD`](../TODO.MD) is a longer-term idea list; the current demo intentionally has fewer features.

## What runs where

| Part | Location | Job |
| --- | --- | --- |
| React app | [`frontend/app/`](../frontend/app/) | Choose COBOL files, show source and Python, download output |
| API | [`backend/src/legacylift/main.py`](../backend/src/legacylift/main.py) | Validate uploads and return conversion results |
| Converter | [`backend/src/legacylift/converter.py`](../backend/src/legacylift/converter.py) | Translate supported lines and flag others for review |
| API checks | [`backend/tests/test_convert.py`](../backend/tests/test_convert.py) | Exercise upload, Python output, and errors |
| Course website | [`docs/index.html`](index.html) and related HTML/CSS | Copied to `/course/` beside the React app on GitHub Pages |
| Research prototype | [`backend/prototype/`](../backend/prototype/) | Earlier experiments; the running API does not import it |

There is no database or user account. The API reads each upload in memory and sends results in the response. The browser creates the downloaded `.py` file locally.

## Follow one conversion

1. A teammate clicks **Choose COBOL files** or **Load sample** in [`App.jsx`](../frontend/app/src/App.jsx). `chooseFiles` checks the count, size, and extension, then `showFile` displays source text.
2. **Convert files** calls `handleConvert`, which calls `convertFiles` in [`api.js`](../frontend/app/src/api.js). It sends a `POST /api/convert` request with each file under the multipart field name `files`.
3. [`main.py`](../backend/src/legacylift/main.py) checks file count, unique output names, extension, byte size, UTF-8 text, and required COBOL sections. It calls `convert_source` once per file.
4. [`converter.py`](../backend/src/legacylift/converter.py) reads declarations and statements, returns a Python string, and records lines that need a human review.
5. The API returns all results. `App.jsx` puts each result beside its source tab, shows `notes`, and uses `downloadPython` to save the selected draft.

The response looks like this:

```json
{
  "files": [
    {
      "source_name": "hello.cbl",
      "python_name": "hello.py",
      "program_name": "HELLO-TEAM",
      "python": "# Draft conversion...\ndef main():\n    ...",
      "notes": []
    }
  ]
}
```

The JSON example shows the shape, not a complete generated program. A rejected upload returns HTTP 400 with a `detail` message that the frontend displays.

## Frontend code map

| File | Start here when you want to... |
| --- | --- |
| [`src/App.jsx`](../frontend/app/src/App.jsx) | Change the controls, selected files, preview, notes, or download |
| [`src/api.js`](../frontend/app/src/api.js) | Change the HTTP request or displayed API/network errors |
| [`src/App.css`](../frontend/app/src/App.css) | Change the page layout or component styles |
| [`src/index.css`](../frontend/app/src/index.css) | Change shared fonts, colors, and browser defaults |
| [`vite.config.js`](../frontend/app/vite.config.js) | Change the development proxy to the backend |

`App.jsx` uses React state: `files` holds selected browser files, `sourceText` holds the visible input, `selectedFile` chooses a tab, `results` holds API output, `error` holds a user-facing message, and `isConverting` disables controls during a request. `sampleCobol` is the built-in demo input. The frontend validates for fast feedback; `main.py` always validates again.

## Backend code map

| Function | Purpose |
| --- | --- |
| `create_app` in [`main.py`](../backend/src/legacylift/main.py) | Configure FastAPI, CORS, `/health`, and `/api/convert` |
| `invalid_upload` in `main.py` | Log a rejected upload and return HTTP 400 |
| `clean_line` in [`converter.py`](../backend/src/legacylift/converter.py) | Remove simple COBOL line numbers and comments |
| `python_name` | Change a COBOL field name into a Python variable name |
| `python_value` | Read a literal or previously declared field |
| `convert_statement` | Convert one supported procedure statement |
| `convert_source` | Walk a whole file, collect Python lines and review notes |

The current rules recognize simple flat `01`/`77` text and whole-number fields and the statements `DISPLAY`, `MOVE`, `ADD`, `SUBTRACT`, and `STOP RUN`. A line outside these rules can receive a `# TODO` comment and a review note. This is a draft converter: review generated code before running it or extending a rule.

To add a COBOL statement, make one small change in `convert_statement`, then add an input/output example in [`test_convert.py`](../backend/tests/test_convert.py). If a new statement needs a new data type or multiple lines of Python, update `convert_source` as well. Keep an unsupported case visible as a review note instead of silently guessing.

## Logs, errors, and debugging

The terminal running Uvicorn shows server startup, request logs, the number of COBOL files received, each converted filename and its review-note count, and upload rejection reasons. These messages are in [`main.py`](../backend/src/legacylift/main.py). They do **not** print uploaded COBOL source or generated Python.

When the page says it cannot reach the backend, check that Uvicorn is running on port 8000 and that Vite is running on port 5173. When the page shows an upload error, read its message first, then the backend terminal for the matching rejection log. For a conversion that looks wrong, load the sample, compare source and output tabs, and add a small backend test before changing the rule.

Run the backend checks from the repository root. The command works in Windows PowerShell and macOS Terminal:

```text
cd backend
uv run --frozen python -m unittest discover -s tests -v
```

Run the frontend checks from the repository root. On Windows PowerShell:

```powershell
cd frontend/app
npm.cmd run lint
npm.cmd run build
```

On macOS Terminal:

```bash
cd frontend/app
npm run lint
npm run build
```

## Configuration and hosting

During local development, [`vite.config.js`](../frontend/app/vite.config.js) forwards `/api` to `http://127.0.0.1:8000`. No extra environment setting is needed. The backend permits the two common local Vite origins by default.

The [Pages workflow](../.github/workflows/pages.yml) builds the React app with Vite's `/LegacyLift/` base path. It also copies the [`docs/`](./) course website into the Pages artifact at `/course/`. The workflow deploys on pushes to `main` or when manually run. GitHub's Pages source must be set to **GitHub Actions**.

For conversion on Pages, set the repository Actions variable `VITE_API_URL` to the public HTTPS backend origin, such as `https://api.example.com` (no trailing `/api`), then rebuild. The frontend adds `/api/convert`. Set `LEGACYLIFT_CORS_ORIGINS=https://aadituh.github.io` on the backend and restart it. The backend reads environment variables directly and does not automatically load `.env` files. Until the backend is hosted and this variable is set, the Pages app displays the sample and upload interface with conversion disabled.

GitHub Pages cannot run FastAPI. The [root README](../README.md) has local run commands; the backend can be hosted separately when ready.

## Notes for teammates

- Keep `backend/uv.lock` and `frontend/app/package-lock.json` in Git so installs match across machines.
- Keep virtual environments, `node_modules`, build output, caches, logs, and generated prototype output out of Git; the root [`.gitignore`](../.gitignore) covers them.
- Put new active API behavior under `backend/src/legacylift/`. The research prototype is for experiments and does not change the web app.
- If a rule cannot translate a COBOL line safely, return a clear review note and a `TODO` line in the draft.

## Codebase audit

Every function in `backend/src/legacylift/` and `frontend/app/src/` participates in the current upload, convert, review, or download path. Keep those files and the two lockfiles. The Pages workflow packages only the built React app and `docs/` course site; it does not package Python source or research files.

The following files are outside the skeletal app:

| Path | Why it is separate |
| --- | --- |
| [`backend/prototype/`](../backend/prototype/) | Older research code, notebooks, and data; nothing in the active API imports it |
| [`SYSTEM.png`](../SYSTEM.png) and [`Formal Design Presentation Final.pdf`](../Formal%20Design%20Presentation%20Final.pdf) | Course deliverables, not loaded by the app or course pages |
| [`TODO.MD`](../TODO.MD) | Long-term roadmap that predates the smaller demo |

The empty `site_dependencies.txt` file, the old `docs/.nojekyll` branch-publishing marker, and the unused `.placeholder-note` CSS rule were removed. The previous standalone frontend and redundant backend parser are also removed from the active tree. Keep the research and course files only while the team still needs those historical materials; they are not required to run or publish the demo.
