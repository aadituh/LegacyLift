# LegacyLift — Demo 2 work

## Demo goal

Upload `BANKMAIN`, `INTCALC`, `TXNPOST`, `ACCTDEF`, and test data as one project. Show dependencies, generate Python, run COBOL and Python on the same inputs, compare results, and download Python with an audit report.

## API and backend

- [x] Create the FastAPI project skeleton: project creation, upload/read-back, draft conversion, and run summaries.
- [ ] Review the initial API schemas with the frontend teammate before building new views.
- [ ] Parse fixed-format COBOL, comments, divisions, fields, paragraphs, and copybooks while retaining source lines.
- [ ] Analyze files together; return `COPY`, `CALL`, and `PERFORM` links and unresolved references.
- [ ] Convert the sample's groups, level 88 fields, `OCCURS`, paragraphs, loops, conditions, calls, and decimal arithmetic with `ROUNDED`.
- [ ] Implement `/analyze` and `/verify`; both currently return HTTP 501.
- [ ] Run COBOL and Python with the same input in a limited runner; return pass/fail and a diff.
- [ ] Keep unsupported constructs visible as review notes instead of claiming verified conversion.

Active code belongs under `backend/src/legacylift/`. `backend/prototype/` is research material and is not imported by the API.

## Frontend

- [ ] Create/open project and upload `.cbl`, `.cob`, `.cpy`, and `.dat` files.
- [ ] Show dependency analysis and fields/paragraphs per program.
- [ ] Show source beside generated Python with review notes.
- [ ] Show verification results, run history, and artifact downloads.
- [ ] Explain upload and conversion errors clearly.

## Demo data and tests

- [ ] Add `TXNPOST.cbl` for deposits, withdrawals, overdrafts, and fees.
- [ ] Change `BANKMAIN` to read `accounts.dat` instead of hard-coded values.
- [ ] Record GnuCOBOL outputs for normal, overdraft, and closed-account inputs.
- [ ] Add parser, API, and COBOL-versus-Python equivalence tests with these fixtures.
- [ ] Check the full flow from a fresh clone before Demo 2.

## Persistence and delivery

- [ ] Add PostgreSQL and migrations for projects, source files, dependencies, runs, and audit events.
- [ ] Save analysis, conversion, and verification results plus downloadable artifacts.
- [ ] Add Docker Compose for UI, API, database, and an isolated GnuCOBOL runner; document one-command startup.
- [ ] Update the design diagrams, feature table, website, and demo slides to match implemented behavior.

## Later

Gemini/RAG comparison and pgvector can follow a deterministic, verified demo. Defer Fortran, JCL, GCP deployment, login, clustering notebooks, and a React rewrite.
