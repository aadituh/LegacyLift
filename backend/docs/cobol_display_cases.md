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
| 4 | `PIC S9(3)` value −5 | DISPLAY `-005` | Signed keeps the minus |
| 5 | `PIC X(10)` value `"HI"` | `HI        ` | Right-pad with spaces |
| 6 | `PIC X(10)` value `"ABCDEFGHIJKLMN"` | `ABCDEFGHIJ` | Truncate to 10 |
| 7 | `PIC 9V99` store 1.239 (no ROUNDED) | `1.23` | Truncate toward zero |
| 8 | `PIC 9V99` ROUNDED 1.235 | `1.24` | Half away from zero |
| 9 | FEESCHED `PIC 9(3)` fee 35 | `035` | Sample bank fee line |
| 10 | FEESCHED `PIC 9(4)` total 65 | `0065` | After ADD of three fees |
| 11 | INTCALC interest (see below) | `2.57` | `COMPUTE … ROUNDED` |

## INTCALC interest (BANKMAIN path)

For Alice’s account in `accounts.dat`:

- balance `1250.05`, rate `0.0250`, days `30`, year `365`
- `interest = balance * rate * days / 365` with `ROUNDED` to `S9(7)V99`
- Result: **`2.57`**

## FEESCHED recorded stdout

See `tests/data/recorded/FEESCHED.out` (`LEGACYLIFT BANK` is exactly 15 characters, so `PIC X(15)` adds no pad).

## BANKMAIN recorded cases

Until full BANKMAIN stdout is re-recorded with GnuCOBOL (#36), the helper tests
cover the same pictures BANKMAIN uses on the statement path (`PIC 9(3)` counters,
`PIC X(20)` names, `S9(7)V99` money / INTCALC interest).
