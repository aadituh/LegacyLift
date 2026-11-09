# LegacyLift web

Next.js App Router frontend for the existing FastAPI service. The visual system uses the project's original navy/teal logo, locally bundled Manrope and JetBrains Mono fonts, responsive layouts, keyboard focus, and reduced motion.

## Run

Use Node.js 24 or newer. Start the API as documented in the repository README, then:

```sh
cd frontend/web
npm ci
cp .env.example .env.local
npm run dev
```

PowerShell uses `npm.cmd` and `Copy-Item .env.example .env.local`. Open http://localhost:3000. The root redirects to Upload; signed-out users see Sign in.

For API accounts, configure a persistent, random `LEGACYLIFT_TOKEN_SECRET` on the API before signing in. Or set `NEXT_PUBLIC_NEON_AUTH_URL` to the Neon Auth endpoint and use Neon accounts. Public variables must be set before building.

[Screenshots](../../docs/frontend-refactor.md).

## Local review

Run `npm run build` then `npm run review` to start the production website and a separate local API workspace. Open http://localhost:3000; sign in with `review@legacylift.local` / `LegacyLiftReview1!`. This mode seeds the sample bank and keeps review data and a generated signing secret under ignored `backend/data/web-review`, without using the configured PostgreSQL database. The runner and Neon Auth are disabled in this local review mode. Gemini uses a configured key when present.

## Workflow

Create a project or load the sample bank, upload files, inspect dependencies, convert and automatically verify, request AI review, and download Python and an audit CSV. Convert and Export restore the most recent saved run on refresh. Local Python edits survive navigation within the workspace and downloads use that exact text. Edits are not saved to the API; refresh, sign-out, and conversion discard them. Verification and AI review always describe the saved generated draft.

Batch converts up to five standalone programs without saving a project. It does not run verification. Its state lasts for the current tab session until refresh.

The code workspace uses CodeMirror for COBOL and Python syntax highlighting, line numbers, per-language search, optional wrapping and fullscreen focus mode. Original source stays read only, Python remains editable, and Tab leaves the editor. The shared viewer also highlights source and export previews. Wide screens use a fluid layout up to 1920px; established-project setup controls collapse while Add files stays visible.

Convert includes project file uploads and previews, a grouped React Flow dependency map with an inspector and mobile list, grouped review guidance, and validated original-source links. Upload also supports source previews, filename search and file-type filtering. A Reading guide on Upload, Convert and Export explains COBOL/Python and review limits. Motion animates navigation/selection and contextual reveals with reduced-motion support; native refresh/close and sign-out warnings protect local edits. Export previews Python (including edits), original COBOL, and the audit CSV before download. The header appearance control offers Light, Dark and Use system; the preference is stored locally.

Export currently provides individual Python files and the CSV. A complete ZIP with the LegacyLift runtime and environment instructions remains a follow-up; generated Python imports that runtime. Gemini and the isolated GnuCOBOL runner are backend capabilities; unavailable services produce plain-language feedback.

## Configuration

| Variable                    | Purpose                                                                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `API_URL`                   | Server-only backend origin used by Next rewrites. Default `http://127.0.0.1:8000`. Set before building; rewrites are compiled into the build. Docker sets `http://api:8000`. |
| `NEXT_PUBLIC_API_URL`       | Optional browser API origin; leave blank for the same-origin proxy. A separate origin needs backend CORS.                                                                    |
| `NEXT_PUBLIC_NEON_AUTH_URL` | Optional Neon browser auth endpoint. Blank uses API account routes. Never put API keys or database credentials in public variables.                                          |

The Next proxy accepts the same 24,000,000-byte request limit as FastAPI. API requests and proxy operations have a two-minute timeout.

## Structure and decisions

- `src/app`: server pages, metadata, route boundaries; dynamic project URLs; Upload's open project uses `?project=`.
- `src/components`: focused screens and reusable UI; pages contain no business logic.
- `src/hooks`: auth, shared workspace, project and conversion workflows. Workspace resets when the user changes.
- `src/lib/api`: authenticated HTTP client, account and project routes.
- `src/lib`: validation, export, CSV, formatting and progress functions.
- `src/types/api-schema.d.ts`: generated from the checked-in FastAPI OpenAPI snapshot.
- `src/styles`: semantic color roles, light/dark/system themes, scoped component styles and responsive rules. Tailwind v4 uses PostCSS.
- `tests/e2e`: real-backend browser workflows; runner and Gemini display outcomes additionally use explicit test fixtures.

Auth uses Neon's browser adapter and bearer tokens, with the API's account implementation as fallback. Hosting uses a Node server (Docker standalone or Vercel), not a static GitHub Pages export. The course site remains on Pages. Batch is intentionally transient. Conversion progress is indeterminate. The decorative background is CSS-only on authentication pages.

## Checks

```sh
npm run typecheck
npm run lint
npm run test:run
npm run format:check
npm run build
npm run e2e
```

Browser tests use Google Chrome, ports 3011 and 8011, an isolated API store, and synthetic local accounts. Build with `API_URL=http://127.0.0.1:8011` and an empty `NEXT_PUBLIC_NEON_AUTH_URL` before running them. The API dependencies must be installed in `backend/.venv` or available through uv. CI installs Chrome. Screenshots, traces, and the HTML report are written to ignored test output directories.

To refresh API contracts, export `app.openapi()` from the backend into `openapi.json`, then run `npm run api:types`. The generator retains optional default-factory fields; consumers handle missing arrays defensively. Run typecheck after schema changes.

Lighthouse accessibility reports: while the isolated API and web server are running, run `npm run a11y:lighthouse`. Reports are saved under `test-results/lighthouse/`. Set `PW_REUSE_SERVERS=1` to reuse those QA servers when running browser tests.

Design direction: [DESIGN.md](DESIGN.md).
