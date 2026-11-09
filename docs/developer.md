# Developer guide

LegacyLift has a FastAPI backend, a Next.js frontend, PostgreSQL or JSON storage, and an isolated GnuCOBOL/Python runner.

## Web application

The frontend is in [frontend/web](../frontend/web/README.md). Start it with `npm ci && npm run dev`; PowerShell uses `npm.cmd`. Open http://localhost:3000. Start the API separately on port 8000.

Next.js rewrites `/api/*` and `/health` to the server-only `API_URL` (default http://127.0.0.1:8000). Browser requests stay same-origin. Set the origin before building; rewrites are compiled into the build.

Pages set metadata and render feature screens. Hooks manage workflows; `useWorkspace` keeps project state and Python edits across navigation. `src/lib/api` owns HTTP calls. `src/types/api-schema.d.ts` is generated from the backend OpenAPI snapshot.

| Change | Location |
| --- | --- |
| Screen behavior | `frontend/web/src/components/{upload,convert,export,batch}` |
| Shared workspace and operations | `frontend/web/src/hooks` |
| API calls and errors | `frontend/web/src/lib/api` |
| CSV, downloads, validation | `frontend/web/src/lib` |
| Colors, typography, responsive styles | `frontend/web/src/styles`, `src/app/globals.css` |
| Backend routes | `backend/src/legacylift/routers` |
| Conversion | `backend/src/legacylift/cobol` |

## Accounts

Configure either:
- API accounts: a random, persistent `LEGACYLIFT_TOKEN_SECRET` on the API; leave `NEXT_PUBLIC_NEON_AUTH_URL` empty.
- Neon Auth: set `NEXT_PUBLIC_NEON_AUTH_URL` on the web build to match the backend's `LEGACYLIFT_NEON_AUTH_URL`.

Both use bearer tokens; project ownership is enforced by the API. Never expose database credentials or Gemini keys through public frontend variables.

## Saved results and edits

The latest conversion, dependency analysis, and subsequent verification/AI review restore from saved runs. New uploads and deletions invalidate visible drafts. Python edits survive route navigation within the workspace and downloads save the current text. Edits are local only; refresh, sign-out, or conversion discards them. Verification and AI review describe the saved generated draft.

## Configuration and hosting

| Setting | Location | Purpose |
| --- | --- | --- |
| `API_URL` | Web server/build | Same-origin backend proxy |
| `NEXT_PUBLIC_API_URL` | Web build, optional | Direct browser API origin; requires API CORS |
| `NEXT_PUBLIC_NEON_AUTH_URL` | Web build, optional | Neon Auth endpoint |
| `LEGACYLIFT_TOKEN_SECRET` | API only | Sign API account tokens |
| `DATABASE_URL` | API only | PostgreSQL storage; unset uses JSON |
| `LEGACYLIFT_GEMINI_API_KEY` | API only | AI review and descriptions |
| `LEGACYLIFT_ENABLE_RUNNER` | API only | Enable isolated execution |

Docker Compose builds the Next.js standalone Node server on port 8080, API on 8000, PostgreSQL and the internal runner. Configure the authentication setting in the root `.env` before starting. The web Docker build points its proxy to `http://api:8000`.

For Vercel, select `frontend/web` as the root and set the build variables above. No Vercel deployment has been configured by this refactor. Next.js dynamic project URLs and the API proxy require a Node host; the app is not exported to GitHub Pages. The Pages workflow deploys the course website from `docs` at the repository root and `/course/`.

## Checks

Run `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm run test:run`, and `npm run build` in `frontend/web`. The [web README](../frontend/web/README.md) explains the isolated browser suite and screenshots.

Backend checks remain `uv run --frozen pytest`, `uv run --frozen ruff check src tests`, `uv run --frozen ruff format --check src tests`, and `uv run --frozen mypy`.

Work on a feature branch, run the checks, and open a reviewed pull request to main as described in [CONTRIBUTING](../CONTRIBUTING.md).
