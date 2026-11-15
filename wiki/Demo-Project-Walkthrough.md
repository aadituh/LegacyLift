**Author(s):** Spencer Peloquin

# Demo Project Walkthrough
The built-in scenario is a small bank’s October month-end close: an accountant moves COBOL to Python and checks that the Python prints the same numbers.

## Sample files (design presentation)
| File | Role |
| --- | --- |
| `BANKMAIN.cbl` | Nightly batch: posts transactions, adds interest, prints a statement |
| `TXNPOST.cbl`, `INTCALC.cbl` | Called by BANKMAIN to post one transaction and add one account’s interest |
| `MONTHEND.cbl` | Month-end close: savings interest, checking fees, ledger totals |
| `FEESCHED.cbl` | Prints the fee schedule |
| Copybooks + `.dat` | Record layouts and batch input (10 files total: five programs, three copybooks, two data files) |

## Steps
1. **Upload** — all 10 files as one project (or Load demo project).  
2. **Dependencies** — BANKMAIN calls TXNPOST and INTCALC; COPY / CALL / PERFORM links.  
3. **Convert** — rules write the Python; review notes where needed.  
4. **Run both** — same data, clear result per program (`docker compose up --build`, open `http://localhost:8080`).  
5. **AI review** (optional) — advice by line; needs a Gemini API key for the API.

## Expected verify outcomes
* MONTHEND and FEESCHED → `verified`  
* BANKMAIN → `mismatch` until file I/O and remaining formats are translated  

Rules do the conversion, GnuCOBOL gives the proof, and AI reviews on top.
