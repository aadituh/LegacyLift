**Author(s):** Spencer Peloquin

**Analyze:** The step that lists COPY, CALL, and PERFORM links between project files so you can see how programs and copybooks depend on each other.

**COBOL:** A long-lived business programming language still used in banking and government batch systems; LegacyLift accepts COBOL sources for conversion.

**Converter:** The LegacyLift component that turns supported COBOL statements into Python drafts and leaves unsupported lines as review notes.

**Copybook:** A shared COBOL fragment (often a record layout) included with `COPY`; in LegacyLift these appear as `.cpy` files.

**GnuCOBOL:** The open-source COBOL compiler (`cobc`) used in the runner container to compile and run original programs during verification.

**Legacy code:** Existing production software that is hard to change; here it usually means COBOL programs and their data files.

**Linkage section:** COBOL data passed into a called program; programs with only linkage cannot run alone without a CALL driver.

**Placeholder term:** *Replace this definition with the official Lab 3 glossary entry when terminology is finalized.*

**Project:** A named set of up to ten uploaded files (programs, copybooks, and data) that you analyze, convert, and verify together.

**Runner:** The isolated Docker service that compiles COBOL and executes both COBOL and Python with time and output limits.

**Verification:** Comparing stdout from GnuCOBOL and from generated Python on the same inputs to see if they match (`verified`, `mismatch`, or `not_verified`).
