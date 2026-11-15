**Author(s):** Spencer Peloquin

# Verification Against GnuCOBOL
After convert, LegacyLift can run each main program as COBOL in the runner and as Python with the same `.dat` files, then compare stdout. Verify is proof for that data; AI review is separate advice.

## Output comparison (requirements §3.1.8)
* Run each main COBOL program and its generated Python on the same project data files.  
* Compile called programs together with the main program.  
* Report matching when printed outputs are exactly the same.  
* For differing outputs, show a line-by-line difference.  
* For compile/run failures, report not matching with the reason.  
* Mark the verify run `verified`, `mismatch`, or `not_verified` accordingly.

## Runner and safety (requirements §3.2.2, §3.3.3)
* Uploaded COBOL and generated Python run only in a separate runner service, never in the API process.  
* Compile timeout 60 seconds; run timeout 10 seconds; max output 256,000 bytes.  
* When the runner is unavailable, mark the run `not_verified`.

## Sample bank results (design presentation)
| Program | Result | Notes |
| --- | --- | --- |
| MONTHEND | Verified | 8 lines match, including leading zeros |
| FEESCHED | Verified | 5 lines match |
| BANKMAIN | Mismatch | File reads / some formats still review notes; diff shows missing lines |
| TXNPOST / INTCALC | (inside BANKMAIN) | No separate result |

MONTHEND example ending line: `TOTAL BALANCE: 000016140.37` (GnuCOBOL 3.1.2).

## Verify vs AI review
* **Verify (GnuCOBOL):** runs both programs → verified or mismatch with a line diff → trust as proof for this data.  
* **AI review (Gemini):** reads COBOL, Python, and notes → matches and concerns by line → advice a person still checks; never changes the verify status.
