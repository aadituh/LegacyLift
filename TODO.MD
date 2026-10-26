# LegacyLift — Demo 2 work

Demo 2 is due November 1. Every open item has a GitHub issue in the [Demo 2 milestone](https://github.com/aadituh/LegacyLift/milestone/1); work it through the steps in [CONTRIBUTING.md](CONTRIBUTING.md) and write `Closes #<number>` in the pull request.

## Demo goal

Upload `BANKMAIN`, `INTCALC`, `TXNPOST`, `ACCTDEF`, and test data as one project. Show dependencies, generate Python, run COBOL and Python on the same inputs, compare results, and download Python with an audit report.

## Demo 2 to-do

### Conversion engine (Spencer)

- [ ] #19 Parser: read fixed-format COBOL: divisions, fields, paragraphs, and copybooks, keeping line numbers.
- [ ] #24 Dependency analysis: `COPY`, `CALL`, and `PERFORM` links and unresolved references.
- [ ] #20 Converter: translate the sample bank's groups, level 88 fields, `OCCURS`, paragraphs, loops, conditions, and calls.
- [ ] #21 Converter: Python prints like COBOL: number padding, overflow, unsigned fields, text length, and `Decimal` arithmetic with `ROUNDED`.
- [ ] #22 Converter: uploaded programs other than the sample convert to Python and show on the page.

### Runner, verify, and setup (Aaditya)

- [ ] #23 GnuCOBOL runner container that compiles and runs `BANKMAIN` (with Spencer).
- [ ] #36 Record real GnuCOBOL output for normal, overdraft, and closed-account inputs; the tests use it.
- [ ] #37 Run the generated Python on the same `.dat` inputs; `POST /api/projects/{id}/verify` returns `verified` or `mismatch` with a diff.
- [ ] #34 `docker compose up` starts the web app, API, database, and runner from a fresh clone (with Jordan).
- [ ] #39 COBOL and `.dat` files for the accountant walkthrough.
- [ ] #38 Decide whether the web app moves from GitHub Pages to Vercel.
- [ ] #35 Update the design diagrams, feature table, website, and Demo 2 slides to match what is built.

### Login and accounts (Darius, Jordan)

- [ ] #17 Login routes (Darius).
- [ ] #15 Login page (Darius).
- [ ] #30 User accounts with projects tied to them (Jordan).
- [ ] #32 Sign-up page and login input validation (Jordan).

### Frontend views (Justin)

- [ ] #27 Dependency list.
- [ ] #26 Verification results view.
- [ ] #28 Audit report after Convert.
- [ ] #29 Keep the verification page and audit report in sync with the converter.

### AI (Darius, Jordan)

- [ ] #18 AI verification of a translation (Darius).
- [ ] #16 AI verification view (Darius).
- [ ] #31 AI-assisted dependency mapping (Jordan).

### Shared

- [ ] #25 Agree the API fields for verify, dependencies, and login; list them in `backend/README.md` (Spencer, Justin, Darius).
- [ ] #33 Stress test with larger COBOL programs (Jordan).
- [ ] Check the full flow from a fresh clone before Demo 2 (everyone).

## Done

- [x] Project API: create, upload, read back, convert, list runs, list projects, and delete a project or one of its files.
- [x] Backend v2: Pydantic models, saved translations, size and project limits, pytest/ruff/mypy in CI.
- [x] Unsupported code stays visible as review notes.
- [x] PostgreSQL (Neon) for projects, files, and runs; JSON files remain the fallback.
- [x] Web app: create a project, upload `.cbl`, `.cob`, `.cpy`, and `.dat` files, show source beside Python with review notes, reopen a project, and show the last translation after a reload.
- [x] Clear upload and conversion errors, including 413 (file too large).
- [x] Sample bank: `TXNPOST.cbl` for deposits, withdrawals, overdrafts, and fees; `BANKMAIN` reads `accounts.dat`.
- [x] Merge rule and contributing guide; course website updated for CS 411W.

Active code is in `backend/src/legacylift/`. `backend/prototype/` is research material that the API doesn't use.

## Later

Tables for dependencies and audit events, and migrations. Gemini/RAG and pgvector after a verified demo. Fortran, JCL, GCP deployment, and the clustering notebooks are deferred.
