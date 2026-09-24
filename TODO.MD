# TODO — Team Website (GitHub Pages)

# TODO — COBOL Prototype (backend/prototype)

## Parser (`src/cobol_parser.py`) — fix first, everything depends on it

- [ ] Allow hyphens in names (`[A-Z0-9][A-Z0-9-]*` instead of `\w+`) so `ACCOUNT-PROC` / `ACCOUNT-NUMBER` aren't cut at the `-`
- [ ] Drop comment lines (first non-space character is `*`) before parsing
- [ ] Split the DATA DIVISION and PROCEDURE DIVISION and parse each separately
- [ ] Only count a paragraph when a name stands alone on its line followed by `.` (skip `GOBACK.`, `EXIT.`, `END-IF.`)
- [ ] Skip the `USING …` clause after `PROCEDURE DIVISION` (INTCALC)
- [ ] Expand `COPY ACCTDEF.` with the contents of `data/ACCTDEF.cpy`
- [ ] Keep group items (`01 ACCOUNT-RECORD`), 88-level conditions, `COMP-3`, `OCCURS` and `VALUE`
- [ ] Return the entry paragraph (the first one) separately from the other methods
- [ ] Raise an error for files that aren't COBOL (e.g. HTML pages)

## Data Folder

- [ ] Replace `display-test.cbl` with the real COBOL source (it is currently a saved GitHub HTML page), or delete it
- [ ] Rename `reference_oop.py` or update notebook 03 (it looks for `reference_account.py`, which doesn't exist)

## Notebook 01 — Data Exploration

- [ ] Cell 1: include `.cpy` files, check file contents to tell COBOL from HTML, sort the file list, build paths that work from any folder
- [ ] Cell 2: re-run after the parser fix (expect `ACCOUNT-PROC` with 3 methods, not `ACCOUNT` with 21)
- [ ] Cell 3: show full attribute names, the group record, the entry paragraph and the PERFORM call graph
- [ ] Cell 4: re-plot with correct counts and leave out non-COBOL files so they don't blow up the axis
- [ ] Re-run the whole notebook to clear the old "Kernel crashed" output

## Notebook 02 — Pattern Detection

- [ ] Cell 1: collect paragraphs from all valid programs (~11), not just `simple_account` (only 4)
- [ ] Cell 2: pair names with cluster IDs by zipping them, not `parsed['potential_methods'][i]` (a different list)
- [ ] Cell 2: cluster the sentence-transformer embeddings instead of TF-IDF so clusters match the plot
- [ ] Cell 2: pick `k` by silhouette score instead of hard-coding 2 or 3
- [ ] Cell 3: keep perplexity below the sample count, e.g. `max(2, min(30, (n-1)//3))` (the current rule crashes with 5 or fewer samples)
- [ ] Cell 3: colour points with Cell 2's labels, drop `StandardScaler`, use `metric='cosine'`
- [ ] Re-run the whole notebook to clear the old "Kernel crashed" output

## Notebook 03 — Refactoring Demo (+ `src/refactorer.py`)

- [ ] Cell 1: replace `sys.path.append('..')` with a path that works from any folder; remove the unused `CodeEmbedder` import
- [ ] Cell 2: pass `encoding='utf-8'` to `open()`; only print "(truncated)" when the text actually is
- [ ] Cell 3: re-run after the parser fix
- [ ] Cell 4 / `refactorer.py`:
  - [ ] Generate one method per real paragraph, named after it (`process_deposit`), not one per cluster
  - [ ] Turn the entry paragraph into `run()` and each `PERFORM X` into `self.x()`; remove the `hasattr` calls
  - [ ] Translate statements one-to-one (ADD, SUBTRACT, COMPUTE, MOVE, DISPLAY, PERFORM, STOP RUN) instead of keyword matching
  - [ ] Remove the invented "insufficient funds" check (the COBOL just subtracts)
  - [ ] Remove the hard-coded `number` / `owner` / `amount` / `balance` fields and the duplicate assignments
  - [ ] Round or truncate decimals to the PIC scale (`V99` means 2 places)
  - [ ] Build the class name from the program ID (`ACCOUNT-PROC` → `AccountProc`)
  - [ ] Leave unsupported statements (IF, PERFORM VARYING, CALL, `X OF Y(i)`) as visible `# TODO` comments instead of guessing
- [ ] Cell 5: load the real reference file, run the same transactions through both classes, compare the printed lines and final balance
- [ ] Cell 6: compute the evaluation (statement coverage, valid Python, match with the reference) instead of printing hard-coded text
- [ ] Re-run the whole notebook to clear the old "Kernel crashed" output

## Other

- [ ] `run_refactoring_demo.py` and the `/api/analyze` and `/api/convert` endpoints in `main.py` use the same parser and refactorer, so they improve once `src/` is fixed
- [ ] Add a COBOL check to the API endpoints so uploads that aren't COBOL get a 400 error
- [ ] Install `prototype/requirements.txt` before re-running (scikit-learn and sentence-transformers are needed)
