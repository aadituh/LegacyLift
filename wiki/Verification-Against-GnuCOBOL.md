**Author(s):** Spencer Peloquin

# Verification Against GnuCOBOL
After convert, LegacyLift can run each main program as COBOL in the runner and as Python with the same `.dat` files, then compare stdout.

## Outcomes
* `verified` — outputs match
* `mismatch` — outputs differ (diff is shown)
* `not_verified` — runner off or unreachable

> **Placeholder:** Document timing limits, sample BANKMAIN mismatch cases, and operator runbooks in the next wiki revision.
