**Authors:** Spencer Peloquin

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
