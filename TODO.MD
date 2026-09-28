# TODO — LegacyLift to Prototype 2

## The Demo 2 goal

A consultant uploads a small multi-file COBOL system (BANKMAIN + INTCALC + TXNPOST +
ACCTDEF + data files) and sees the dependency analysis. They convert it to Python and
click **Verify**: the COBOL and the Python run on the same input, and their outputs match.
Last, they download the Python and an audit report.

## Setup (do first)

- [ ] Remove `backend/prototype/*` from the root `.gitignore` and commit `pipeline.py` and `translator.py` (the app can't start without them)
- [ ] Agree on the API endpoints and JSON shapes before building the frontend or backend against them

---



## Frontend — `frontend/`

- [ ] Projects page: create and open a project
- [ ] Multi-file upload (`.cbl`, `.cpy`, `.dat`)
- [ ] Analysis view: dependency graph (CALL / COPY) plus fields and paragraphs per program
- [ ] Side-by-side view: COBOL paragraph next to its Python method
- [ ] Verify panel: pass/fail per program plus a line diff
- [ ] History / audit page (from the database, not browser storage)
- [ ] Download the Python as a zip
- [ ] Show clear errors (for example, when a non-COBOL file is uploaded)



## Frontend — `frontend/`

- [ ] Projects page: create and open a project
- [ ] sssa
- [ ] saas
- [ ] saassa
- [ ] saas
- [ ] 



## Backend



### Conversion engine — `backend/prototype/src/`

- [ ] Parser: allow hyphens in names, skip comment lines, split the DATA and PROCEDURE divisions
- [ ] Parser: expand `COPY`, keep group items / 88-levels / `COMP-3` / `OCCURS`
- [ ] Parser: parse several files together and return the `CALL` / `COPY` / `PERFORM` links
- [ ] Translator: one Python method per paragraph; translate MOVE, ADD, COMPUTE, IF, EVALUATE, PERFORM, CALL
- [ ] Translator: use `Decimal` with the PIC scale and `ROUNDED`; leave `# TODO` for anything unsupported
- [ ] Gemini + RAG: translate at least one program and show it next to the rule-based version



### API — `backend/src/legacylift/`

- [ ] Endpoints: create a project, upload files, analyze, convert, verify, run history
- [ ] Reject non-COBOL uploads with a 400 error
- [ ] Verify endpoint: run the COBOL (GnuCOBOL) and the Python on the same input and compare the outputs
- [ ] Load settings (database URL, Gemini key) from `.env`, never committed



## Database — PostgreSQL

- [ ] PostgreSQL in Docker Compose
- [ ] First migration (Alembic): projects, source_files, components, dependencies, runs, audit
- [ ] Save every analyze / convert / verify run (this is the audit log)
- [ ] Later: pgvector tables for RAG (rag_knowledge_base, embeddings)



## QA



### Demo COBOL system — `backend/prototype/data/`

- [ ] Write `TXNPOST.cbl`: post deposits and withdrawals, reject overdrafts, add fees
- [ ] Change BANKMAIN to read `accounts.dat` instead of hard-coded values
- [ ] Create 2–3 input sets (normal, overdraft, closed account) with the expected output from GnuCOBOL
- [ ] Replace or delete `display-test.cbl` (it's a saved HTML page, not COBOL)



### Tests — `backend/tests/`

- [ ] Write the test plan (test IDs that the demo will run)
- [ ] pytest: parser tests, API tests, COBOL-vs-Python equivalence tests
- [ ] Before Demo 2: the full demo works from a fresh clone and Verify passes on every input set



## Infrastructure — repo root

- [ ] `docker-compose.yml`: UI, API, Postgres and a GnuCOBOL runner
- [ ] One command to start the whole demo: `docker compose up`
- [ ] Update `README.md` with how to run it



## Presentation & website — `docs/`

- [ ] Redraw the Major Functional Components Diagram (MFCD) as Frontend → API → Engine / Runner → Database
- [ ] Feature table: real-world product vs. prototype
- [ ] Final demo scenario slide
- [ ] Update `docs/presentations.html` with the new deck



## Cut for now

- Notebooks 02/03 (KMeans clustering), Fortran, JCL, GCP deployment, login, React rewrite

