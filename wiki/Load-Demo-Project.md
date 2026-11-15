**Authors:** Spencer Peloquin

# Load Demo Project
This tutorial walks through loading the October month-end close demo used in the design presentation.

## Steps
1. Start the stack locally with `docker compose up --build` (or open the hosted site).  
2. Sign in if login is required.  
3. Go to **Upload**.  
4. Click **Load demo project** (or create a project and upload all 10 files from `backend/src/legacylift/data`).  
5. Confirm five programs, three copybooks, and two data files appear.

## After load
Continue with Analyze (dependencies), Convert, and Verify. Expected: MONTHEND and FEESCHED verified; BANKMAIN mismatch until remaining file I/O is translated.
