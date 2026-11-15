**Authors:** Spencer Peloquin

# Welcome to LegacyLift
> "AI Pipeline for Legacy Code Modernization"

Developed by: LegacyLift Team, Old Dominion University CS411W

# What is LegacyLift?
LegacyLift is an AI-assisted legacy code analysis and modernization toolchain. It ingests COBOL programs and procedures, performs automated parsing, dependency mapping, and data-flow analysis, then uses rule-based conversion (with Gemini / RAG-assisted review) to produce functionally equivalent modern Python. The goal is to reduce security risk and technical debt while preserving critical business logic—especially for small and medium financial and accounting firms.

As of 2026, about 95% of U.S. ATM transactions still run on COBOL-based systems, and over 60% of U.S. hospitals run critical applications on legacy software such as COBOL and Fortran. LegacyLift proposes an AI-driven pipeline that analyzes dependencies and incrementally converts legacy systems to modern infrastructure while keeping compatibility with existing data and workflows.

# How Does LegacyLift Work?
LegacyLift allows you to:
* Upload COBOL programs (`.cbl` / `.cob`), copybooks (`.cpy`), and data files (`.dat`) as one project (up to ten files)
* Analyze divisions, fields, paragraphs, and every COPY, CALL, and PERFORM link
* Convert each program to Python with fixed rules; unsupported lines become review notes (never guessed)
* Verify by running GnuCOBOL and the generated Python on the same data, then comparing printed output character for character
* Optionally request an AI review that reports matches and concerns by line without changing the verify result

# Product goals
1. Functional equivalence between COBOL and Python for the same inputs  
2. Lower technical debt and maintenance cost without a full-time COBOL bench  
3. Safer path toward modern / cloud-native environments  
4. Logically compatible output that can be reviewed beside the original  
5. Support for consultants and organizations modernizing enterprise systems  

# Thank you for Choosing LegacyLift!
This wiki covers processes, interfaces, and tasks behind LegacyLift, drawn from Lab 1, the product requirements, and the formal design presentation. Browse the sidebar for workflows and how-to pages.

Live demo: https://aadituh.github.io/LegacyLift/
