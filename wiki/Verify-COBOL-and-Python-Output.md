**Authors:** Spencer Peloquin, Aaditya Ghimire

# Verify COBOL and Python Output
Check that each Python draft prints the same output as its COBOL program.

## Before you start
* Open a project that has at least one COBOL program. Add the `.dat` files the programs read.
* Use a copy of LegacyLift started with Docker (see [[Run LegacyLift Locally|Run-LegacyLift-Locally]]). Without the runner, every result is **Not compared**.

## Steps
1. Open the project and go to **Convert**.
2. Click **Convert project**. Verification starts when the conversion finishes; the status line reads "Comparing COBOL and Python outputs."
3. Select a program in the list on the left.
4. Scroll to **Verification for** *program name* and read the status: **Verified**, **Mismatch**, or **Not compared**.
5. For a mismatch, read the line under the status, such as "3 of 12 output lines differ", and the output table.
6. To see every program on one page, set **Code view** to **Audit report**.
7. To check again without converting, click **Run verification again**.

## Reading the output table
| Column | Shows |
| --- | --- |
| Line | Output line number |
| COBOL output | What the original program printed |
| Python output | What the draft printed |
| Comparison | **Match** or **Differs** |

The table shows the first 200 lines. Click **Show all rows** for the rest.

## Messages you may see
| Message | What to do |
| --- | --- |
| "COBOL and Python outputs match." | Nothing. The draft printed the same output for this data. |
| "Outputs differed or a program failed." | Read the differing lines and the review notes for that program. |
| "*Name* runs inside *caller*. Its output is checked with the caller." | Open the calling program's result. |
| "Verification is unavailable. No outputs were compared." | Start LegacyLift with Docker, then click **Run verification again**. |
| "You have local Python edits." | Verification describes the saved draft, not your edits. Download your edits before converting again. |

## Keep a record
Go to **Export** and click **Download .csv** next to `audit-report.csv`. The file lists each program's status and both outputs line by line.

Background: [[Verification Against GnuCOBOL|Verification-Against-GnuCOBOL]].
