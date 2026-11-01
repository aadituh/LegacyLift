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

The side menu has three screens: **Upload**, **Convert**, and **Export**. A progress ring shows how far you are.

| Screen | Control | API call |
| --- | --- | --- |
| (logged out) | **Log in** | `POST /api/auth/login`, then `GET /api/auth/me`. A wrong password or other failed sign-in shows the API message. If the API is down, the form says the backend is not reachable. **Log out** clears the token and returns to this page. An expired token shows "Please log in again". |
| (logged out) | **Create account** | `POST /api/auth/register`, then login. Display name, email, password, and confirm password. Empty fields, a bad email, a display name with other characters, a password of the wrong length, or passwords that do not match show a message under the form and are not sent. A used email or a weak password shows the API message under the form. A valid sign-up logs the user in. |
| (page load) | | `GET /health`; Convert stays disabled until the API answers |
| Upload → **Project** | **Create project**, **Load demo project** | `POST /api/projects`, `POST /api/projects/demo` |
| Upload → **Project** | **Upload project files** | `POST /api/projects/{id}/files` (`.cbl`, `.cob`, `.cpy`, `.dat`) |
| Upload → **Batch files** | **Choose COBOL files**, **Load small sample** | None yet; files stay in the browser |
| Convert | **Convert files** (batch) or **Convert project** | `POST /api/convert` (up to 5 `.cbl`/`.cob` files, not saved) or `POST /api/projects/{id}/convert` |
| Convert | **Review with AI** | `POST /api/projects/{id}/ai-review`. Each program shows `clear` or `concerns`; each concern lists its COBOL and Python lines |
| Convert | **Both / COBOL only / Python only** | No API call; switches the view |
| Convert | Python panel | The converted Python is an editor. Typing or deleting updates the copy that **Download .py** saves. |
| Export | **Download .py** | Saves the Python currently shown, including edits. If that text is not on the page, falls back to `GET /api/projects/{id}/runs/{run_id}/files/{name}` or `GET /api/convert/{download_id}/files/{name}`. |

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
