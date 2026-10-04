# LegacyLift — Demo 2 work

## Demo goal

Upload `BANKMAIN`, `INTCALC`, `TXNPOST`, `ACCTDEF`, and test data as one project. Show dependencies, generate Python, run COBOL and Python on the same inputs, compare results, and download Python with an audit report.

## API and backend

- [x] Project API: create, upload, read back, convert, and list runs.
- [x] Backend v2: Pydantic models, JSON saving, saved translations, size and project limits, pytest/ruff/mypy in CI.
- [x] Keep unsupported code visible as review notes instead of claiming a conversion works.
- [x] List projects (`GET /api/projects`) so the page can reopen one.
- [x] Delete a project or one of its files.
- [ ] Parse fixed-format COBOL: divisions, fields, paragraphs, and copybooks, keeping line numbers.
- [ ] Analyze files together: return `COPY`, `CALL`, and `PERFORM` links and unresolved references.
- [ ] Make Python behave like COBOL: number padding, overflow, unsigned fields, text length, and `Decimal` arithmetic with `ROUNDED`.
- [ ] Convert the sample's groups, level 88 fields, `OCCURS`, paragraphs, loops, conditions, and calls.
- [ ] Verify: run COBOL (GnuCOBOL) and Python on the same input in a sandbox; return pass/fail and a diff.

Active code is in `backend/src/legacylift/`. `backend/prototype/` is research material that the API doesn't use.

## Frontend

- [x] Create a project and upload `.cbl`, `.cob`, `.cpy`, and `.dat` files.
- [x] Show source beside generated Python with review notes.
- [ ] Reopen an existing project, and show the last translation after a page reload.
- [ ] Show dependency analysis and fields/paragraphs per program.
- [ ] Show verification results, run history, and downloads.
- [x] Explain upload and conversion errors clearly, including 413 (file too large).

## Demo data and tests

- [x] Add `TXNPOST.cbl` for deposits, withdrawals, overdrafts, and fees.
- [x] Change `BANKMAIN` to read `accounts.dat` instead of hard-coded values.
- [ ] Record GnuCOBOL outputs for normal, overdraft, and closed-account inputs.
- [ ] Add parser and COBOL-versus-Python equivalence tests with these files.
- [ ] Check the full flow from a fresh clone before Demo 2.

## Persistence and delivery

- [ ] PostgreSQL and migrations for projects, files, dependencies, runs, and audit events (replaces the JSON files).
- [ ] Docker Compose for UI, API, database, and an isolated GnuCOBOL runner, with one-command startup.
- [ ] Update the design diagrams, feature table, website, and demo slides to match what is built.

## Later

Gemini/RAG and pgvector after a deterministic, verified demo. Fortran, JCL, GCP deployment, login, and the clustering notebooks are deferred.
