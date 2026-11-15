**Author(s):** Spencer Peloquin

Definitions drawn from Lab 1 and the product requirements / design presentation.

**Common Business-Oriented Language (COBOL):** A language popular on corporate mainframes in the 1970s and 1980s; still embedded in finance, government, and healthcare. LegacyLift’s primary input language.

**Docker:** Platform for containerizing applications. LegacyLift starts the database, API, runner, and web app with Docker Compose for local development.

**Functional equivalence:** New code produces identical outputs and behavior to the legacy code for the same inputs. Verify marks a program matching when COBOL and Python print exactly the same text.

**Gemini:** Google’s AI model used for AI-assisted translation of review notes and for AI review of converted programs.

**GnuCOBOL (`cobc`):** Open-source COBOL compiler used in the runner container to compile and run original programs during verification.

**Hallucination:** An LLM error that produces output that looks valid but is logically wrong; RAG and rule-based conversion reduce this risk.

**Integrated Development Environment (IDE):** Collection of tools for coding, debugging, and production in one application.

**Job Control Language (JCL):** Scripting language used alongside COBOL on enterprise mainframes.

**Large Language Model (LLM):** Software capable of generative reasoning over large datasets; used in LegacyLift for assisted translation and review, not as the sole converter.

**Node Package Manager (NPM):** Content distribution framework for web packages (Lab 1 packaging discussion).

**Object-Oriented Programming (OOP):** Style that organizes code into modular classes rather than linear procedures.

**Python:** Interpreted language used for LegacyLift’s converter output and API (Python 3.12 + FastAPI).

**Retrieval-Augmented Generation (RAG):** Technique that retrieves relevant code, documentation, and patterns before generation so the model sees real context instead of guessing.

**Review note:** A COBOL line the rule-based converter cannot translate, kept as a comment with the original text and line number for human (or AI-assisted) follow-up.

**Runner:** Isolated Docker service with GnuCOBOL and Python; the only place uploaded COBOL and generated Python execute.

**Structured Query Language (SQL):** Default format for enterprise databases such as PostgreSQL (Neon hosts LegacyLift accounts and projects).

**Technical debt:** Accumulated cost of maintaining outdated code; inherent in legacy systems that need specialized knowledge to operate.

**Vector database:** Store optimized for semantic search of embeddings (used with RAG / pgvector for similar verified examples).

**Verification:** Running COBOL and Python on the same project data files and comparing printed output (`verified`, `mismatch`, or `not_verified`).
