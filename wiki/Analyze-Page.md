**Authors:** Spencer Peloquin, Justin Tendilla

# Analyze Page
The Analyze view shows how files in the current project depend on each other—COPY, CALL, and PERFORM links—plus program structure (divisions, fields, paragraphs). Unresolved references are flagged when the target is missing from the project.

## What reviewers see (design presentation / requirements)
* Dependency list for the selected program: what it copies, calls, and performs, plus fields and paragraphs.  
* Unresolved COPY / CALL / PERFORM names so missing files are obvious before convert.  
* On the sample bank: BANKMAIN calls TXNPOST and INTCALC; 16 links, none unresolved.

## Related API behaviour
Analyze results are saved as a run with time, status, and results so they can be reopened with the project. An optional plain-language AI dependency map can describe each program and the data they share for people who do not read COBOL.

## Where this appears in the app

The built app has no separate Analyze screen. The dependency map is a section of [[Convert Page|Convert-Page]], on a card titled **Dependencies for** the selected program.

* The card counts **COPY**, **CALL**, and **PERFORM** connections and can filter to one type.
* A wide screen shows a graph. A narrow screen shows a list. The reader can switch between **Graph** and **List**.
* Choosing a connection jumps to that line in the COBOL source.
* Unresolved names stay on the card when a target is missing from the project.

Figure 1. Dependencies for BANKMAIN on the Convert page. To be added when this screen is finalized for the manual.
