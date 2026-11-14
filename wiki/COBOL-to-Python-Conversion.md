**Author(s):** Spencer Peloquin

# COBOL to Python Conversion
Conversion walks each program’s PROCEDURE DIVISION and emits a Python draft. Supported constructs become runnable Python; unsupported lines become review notes so humans know what still needs work.

## Current behaviour (summary)
* Groups, OCCURS, IF/EVALUATE, PERFORM, CALL, and COPY expansion are among the working paths.
* File I/O and some edited pictures may remain as TODOs until later converter work lands.

> **Placeholder:** Insert architecture diagrams and a before/after COBOL→Python sample when the converter write-up is ready.
