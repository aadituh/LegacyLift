# GnuCOBOL DISPLAY / storage cases (issue #21)

Shared with the team so converted Python can be checked against real COBOL
behaviour. Fixtures under `tests/data/recorded/` hold the expected stdout for
sample programs. When GnuCOBOL (`cobc`) is available, re-record with the
scripts noted in issue #36.

## Numeric and text rules (10+ cases)

| # | Picture / operation | Stored / printed result | Notes |
| --- | --- | --- | --- |
| 1 | `PIC 9(4)` value 14 | DISPLAY `0014` | Leading zeros |
| 2 | `PIC 9(3)` value 1234 | DISPLAY `234` | Overflow drops leftmost digits |
| 3 | `PIC 9(3)` value −5 | DISPLAY `005` | Unsigned drops the sign |
| 4 | `PIC S9(3)` value −5 / +5 | DISPLAY `-005` / `+005` | Signed always shows `+` or `-` |
| 5 | `PIC X(10)` value `"HI"` | `HI        ` | Right-pad with spaces |
| 6 | `PIC X(10)` value `"ABCDEFGHIJKLMN"` | `ABCDEFGHIJ` | Truncate to 10 |
| 7 | `PIC 9V99` store 1.239 (no ROUNDED) | `1.23` | Truncate toward zero |
| 8 | `PIC 9V99` ROUNDED 1.235 | `1.24` | Half away from zero |
| 9 | FEESCHED `PIC 9(3)` fee 35 | `035` | Sample bank fee line |
| 10 | FEESCHED `PIC 9(4)` total 65 | `0065` | After ADD of three fees |
| 11 | INTCALC interest (see below) | DISPLAY `+0000025.69` | `COMPUTE … ROUNDED`; signed `+` |

## INTCALC interest (Alice @ 30 days)

`INTCALC` has a `LINKAGE SECTION`, so it cannot run alone. Record stdout with
`INTDRV.cbl` (CALLs `INTCALC`) through `scripts/record_cobol_output.py` in the
runner image. Fixture: `tests/data/recorded/INTCALC_alice_30d.out`.

Alice’s first line in `accounts.dat` against `ACCTDEF.cpy`:

- `ACCT-BALANCE` `PIC S9(7)V99 SIGN LEADING SEPARATE` bytes `+001250050` → **`12500.50`**
  (the leading `+` is the sign; do not read this as `1250.05`)
- `ACCT-RATE` `PIC 9V9999` bytes `00250` → `0.0250`
- days `30`, year `365`
- `interest = balance * rate * days / 365` with `ROUNDED` to `S9(7)V99` → **`25.69`**
- GnuCOBOL plain `DISPLAY` of that field: **`+0000025.69`**

## FEESCHED recorded stdout

See `tests/data/recorded/FEESCHED.out` (`LEGACYLIFT BANK` is exactly 15 characters, so `PIC X(15)` adds no pad).

## BANKMAIN recorded cases

`tests/data/recorded/bank/<case>/BANKMAIN.out` holds GnuCOBOL 3.1.2 output for the
`sample`, `normal`, `overdraft`, and `closed` cases (`scripts/record_cobol_output.py`).
