**Authors:** Spencer Peloquin, Aaditya Ghimire

# Verification Against GnuCOBOL
Verification answers one question: does the Python draft print the same text as the original COBOL? LegacyLift compiles and runs each main program with GnuCOBOL, runs its Python draft with the same data files, and compares what the two print.

## When it runs
* Automatically after **Convert project** on the Convert page.
* Again whenever you choose **Run verification again**.
* Only for saved projects. Batch conversion is not verified.

## What is compared
* Each main program and its Python draft read the project's `.dat` files.
* Programs that a main program calls are compiled with it and checked through its output. They have no result of their own.
* The printed output must be exactly the same, including spaces and leading zeros.
* Verification always uses the saved generated draft. Edits you make to the Python in the browser are not included.

## Results
| Status on the page | Meaning |
| --- | --- |
| **Verified** | COBOL and Python printed the same output. |
| **Mismatch** | The outputs differ, or one program did not compile or finish. The table marks each differing line and a message gives the reason for a failure. |
| **Not compared** | Verification is not available where the app is running, so nothing was run. |

A **Verified** result covers the data files in the project. Add data files for other cases you want to check.

## Where the programs run
Uploaded COBOL and generated Python run only in the runner, a separate service with no internet access. The API does not run them.

| Limit | Value |
| --- | --- |
| Compile time | 60 seconds |
| Run time for each program | 10 seconds |
| Printed output | 256,000 bytes |

The runner starts with `docker compose up` (see [[Run LegacyLift Locally|Run-LegacyLift-Locally]]). Where it is not running, every result is **Not compared**.

## Sample bank results
| Program | Result | Notes |
| --- | --- | --- |
| `MONTHEND` | Verified | 8 lines match, ending `TOTAL BALANCE:   000016140.37` |
| `FEESCHED` | Verified | 5 lines match |
| `BANKMAIN` | Mismatch | The table shows the statement lines the draft does not print yet |
| `TXNPOST`, `INTCALC` | Checked inside `BANKMAIN` | No separate result |

## Verification and AI review
* **Verification** runs both programs and reports Verified or Mismatch. It is the evidence for the data you supplied.
* **AI review** reads the COBOL, the Python, and the review notes, and lists matches and concerns by line. It is advice for the reviewer and never changes the verification status.

Steps: [[Verify COBOL and Python Output|Verify-COBOL-and-Python-Output]].
