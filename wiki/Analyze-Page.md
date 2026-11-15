**Author(s):** Spencer Peloquin

# Analyze Page
The Analyze view shows how files in the current project depend on each other—COPY, CALL, and PERFORM links—plus program structure (divisions, fields, paragraphs). Unresolved references are flagged when the target is missing from the project.

## What reviewers see (design presentation / requirements)
* Dependency list for the selected program: what it copies, calls, and performs, plus fields and paragraphs.  
* Unresolved COPY / CALL / PERFORM names so missing files are obvious before convert.  
* On the sample bank: BANKMAIN calls TXNPOST and INTCALC; 16 links, none unresolved.

## Related API behaviour
Analyze results are saved as a run with time, status, and results so they can be reopened with the project. An optional plain-language AI dependency map can describe each program and the data they share for people who do not read COBOL.
