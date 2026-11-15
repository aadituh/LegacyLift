**Author(s):** Spencer Peloquin

# Verify COBOL and Python Output
## Steps
1. Ensure the runner is available (`docker compose up` locally, or hosted runner enabled).  
2. After Convert, start **Verify** (or use the verify step that follows convert when configured).  
3. Read each file’s status: `verified`, `mismatch`, or `not_verified`.  
4. Open the line diff for any mismatch; use the audit report for a project-wide CSV.

## How to read the sample results
* MONTHEND / FEESCHED — exact match including leading zeros → proof for that data.  
* BANKMAIN — mismatch with missing statement lines still useful: the diff shows what the draft does not print yet.  
* AI review never changes these statuses; it only explains possible causes by line.
