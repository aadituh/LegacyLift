# Frontend

This React and Vite app lets a teammate choose COBOL files, inspect the source, convert them through the backend, read review notes, and download Python drafts.

## Run

Start the backend first using [its instructions](../../backend/README.md). Then, from this directory:

Windows PowerShell:

```powershell
npm.cmd ci
npm.cmd run dev
```

macOS Terminal:

```bash
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Vite sends local `/api` requests to port 8000.

## Files

| File | Responsibility |
| --- | --- |
| [`src/App.jsx`](src/App.jsx) | Health probe, file/project selection, batch + project convert, download |
| [`src/api.js`](src/api.js) | `/health`, `/api/convert`, and `/api/projects/*` client |
| [`src/App.css`](src/App.css) and [`src/index.css`](src/index.css) | App layout and shared styles |
| [`vite.config.js`](vite.config.js) | React plugin and local API proxy |

The browser checks file count, size, and extension for quick feedback. The backend checks again because browser checks can be bypassed. API errors appear above the controls. See [the developer guide](../../docs/developer.md) for the full request path.

## Check and build

Windows PowerShell:

```powershell
npm.cmd run lint
npm.cmd run build
```

macOS Terminal:

```bash
npm run lint
npm run build
```

The [Pages workflow](../../.github/workflows/pages.yml) builds this app at `https://aadituh.github.io/LegacyLift/`. It sets Vite's base path to `/LegacyLift/` and copies the course website to `/course/`. For a static deployment with conversion, set the repository Actions variable `VITE_API_URL` to the backend's public HTTPS origin (for example, `https://api.example.com`, without `/api`). The app appends `/api/convert`. The backend must allow `https://aadituh.github.io` with `LEGACYLIFT_CORS_ORIGINS`. Without an API URL, the Pages app shows the interface and sample but disables conversion.
