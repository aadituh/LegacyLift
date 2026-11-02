# Demo 2 walkthrough: October month-end close

An accountant at LegacyLift Bank moves the bank's month-end COBOL to Python and checks that the Python prints the same numbers.

## Files

All ten are in [`backend/src/legacylift/data/`](../backend/src/legacylift/data/), the most one project holds.

| File | Role |
| --- | --- |
| `BANKMAIN.cbl` | Nightly batch: reads the accounts and today's transactions, posts them, adds interest, prints a statement |
| `TXNPOST.cbl`, `INTCALC.cbl` | Called by `BANKMAIN`: post one transaction; add one account's interest |
| `ACCTDEF.cpy`, `TXNDEF.cpy` | Account (43 characters) and transaction (16 characters) record layouts |
| `accounts.dat`, `transactions.dat` | The batch's input |
| `MONTHEND.cbl` | Month-end close: interest on savings, a $5 fee on checking under $1,000, ledger totals. Starts from the batch's balances |
| `FEERATES.cpy` | Month-end settings copied by `MONTHEND`: 31 days, $5 fee, $1,000 minimum |
| `FEESCHED.cbl` | Prints the fee schedule |

## Steps

Start everything with `docker compose up --build` and open <http://localhost:8080>.

1. **Upload:** choose **Project** and click **Load demo project**. Or create a project named `October close`, then **Upload project files** and select all ten files.
2. **Analyze:** the dependency list shows `BANKMAIN` calling `TXNPOST` and `INTCALC`, the copybooks each program copies, and `MONTHEND` copying `FEERATES`.
3. **Convert:** click **Convert project**. `MONTHEND`, `FEESCHED`, and `TXNPOST` convert with no review notes; `BANKMAIN` and `INTCALC` have review notes for lines the converter doesn't handle yet, such as file reads and edited pictures (`Z,ZZ9.99`).
4. **Verify:** runs after Convert. Each main program runs as COBOL in the runner and as Python with the same `.dat` files.

| Program | Result |
| --- | --- |
| `MONTHEND` | `verified`: the same eight lines, ending `TOTAL BALANCE:   000016140.37` |
| `FEESCHED` | `verified` |
| `BANKMAIN` | `mismatch`, with a line diff of the statement lines the draft doesn't print yet |

`TXNPOST` and `INTCALC` run inside `BANKMAIN`, so they have no result of their own.

## Expected output

What GnuCOBOL prints for each program is in [`backend/tests/data/recorded/`](../backend/tests/data/recorded/) (`MONTHEND.out`, `FEESCHED.out`, `bank/sample/BANKMAIN.out`).
