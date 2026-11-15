**Authors:** Spencer Peloquin, Justin Tendilla

# Convert Page
Convert turns each program into a Python draft and lists review notes. The design presentation’s Convert screen shows COBOL beside Python and lets the reviewer switch between Both, COBOL only, and Python only.

## What you see
* Conversion status above the code (`draft` or `review_required`).  
* Side-by-side COBOL and Python with line numbers (requirements §3.1.10).  
* Review notes listed with their COBOL line numbers.  
* Optional AI review result (overall result, matches, concerns with line numbers) beside the output comparison—without changing verify status.

## Performance notes (requirements §3.2.1)
* Convert a 100 KB COBOL program in under 2 seconds.  
* Keep answering other requests while a conversion is running.  
* Analyze, convert, and verify a project of 10 × 100 KB programs without error.

## Where this appears in the app

Convert opens at `/convert?project=`.

* **Reading guide** and, after a conversion, **Go to Export**.
* View switch: **Side by side**, **COBOL**, **Python**, and **Audit report**. COBOL stays read only. Python can be edited in the tab.
* **Convert project** and **Review with AI**. What an AI review means stays on the [[AI Review|AI-Review]] page.
* The dependency card from the [[Analyze Page|Analyze-Page]], the review notes, and a jump from a note to its COBOL line.
* The verification result for the selected program, plus **Run verification again**. Verification compares the saved draft, not unsaved edits.
* The audit report view says **Convert this project before viewing the report** when there is no conversion yet.

Figure 1. Convert, Side by side, with a program selected. To be added when this screen is finalized for the manual.

Figure 2. The Audit report view. To be added when this screen is finalized for the manual.
