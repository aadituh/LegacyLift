**Author(s):** Spencer Peloquin

# Project Upload and Analysis
Users create or open a project and add COBOL programs (`.cbl`), copybooks (`.cpy`), and data files (`.dat`). LegacyLift stores the project and can list dependency links (COPY, CALL, PERFORM) so reviewers see how files connect.

## Current behaviour (summary)
* A project holds at most ten files—the same limit as the October close demo set.
* Analyze returns per-program summaries and unresolved names when a CALL or COPY target is missing.

> **Placeholder:** Replace this section with the final process narrative, decision tables, and exception paths (oversized uploads, invalid names, auth required) after Lab 3 review.
