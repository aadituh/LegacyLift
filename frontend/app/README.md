# Frontend

A React + Vite app for uploading COBOL files, converting them through the backend, reading review notes, and downloading the Python.

## Run

Start the [backend](../../backend/README.md) first. Then, from this folder:

```bash
npm ci          # Windows PowerShell: npm.cmd ci
npm run dev     # Windows PowerShell: npm.cmd run dev
```

Open <http://127.0.0.1:5173>. Vite forwards `/api` and `/health` to the backend on port 8000.

## What the screen does

| Control | API call |
| --- | --- |
| Page load | `GET /health`; Convert stays disabled until the API answers |
| **Choose COBOL files**, **Load small sample**, **Convert files** | `POST /api/convert` (up to 5 `.cbl`/`.cob` files, not saved) |
| **Create project**, **Load demo project** | `POST /api/projects`, `POST /api/projects/demo` |
| **Upload project files** | `POST /api/projects/{id}/files` (`.cbl`, `.cob`, `.cpy`, `.dat`) |
| **Convert project** | `POST /api/projects/{id}/convert` |
| **Both / COBOL only / Python only**, **Download .py** | No API call; these switch the view and save the file in the browser |

## Files

| File | Responsibility |
| --- | --- |
| [`src/App.jsx`](src/App.jsx) | The whole screen: state, buttons, panels, download |
| [`src/api.js`](src/api.js) | Every backend call, and turns API errors into messages |
| [`src/App.css`](src/App.css), [`src/index.css`](src/index.css) | Layout and shared styles |
| [`vite.config.js`](vite.config.js) | React plugin, local API proxy, Pages base path |

## Check and build

```bash
npm run lint    # Windows PowerShell: npm.cmd run lint
npm run build   # Windows PowerShell: npm.cmd run build
```

The [Pages workflow](../../.github/workflows/pages.yml) publishes the build to <https://aadituh.github.io/LegacyLift/>. It points the app at the API through `VITE_API_URL`; see [hosting](../../docs/developer.md#configuration-and-hosting).
