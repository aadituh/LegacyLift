**Authors:** Spencer Peloquin, Aaditya Ghimire

Definitions drawn from Lab 1, the Lab 2 requirements specification, and the design presentation.

**Application Programming Interface (API):** A set of operations through which one program requests services from another. The web app sends every request to the LegacyLift API.

**Audit report:** The page and `audit-report.csv` file that list each program's verification status with its COBOL and Python output line by line.

**Batch conversion:** Converting up to five standalone COBOL programs without creating a project. Batch results are not saved or verified.

**Common Business-Oriented Language (COBOL):** A language popular on corporate mainframes in the 1970s and 1980s; still embedded in finance, government, and healthcare. LegacyLift’s primary input language.

**Continuous Integration (CI):** Automatically running tests and checks on every code change. LegacyLift uses GitHub Actions.

**Copybook:** A COBOL source file (`.cpy`) holding shared record or field definitions that programs include with the COPY statement.

**Cross-Origin Resource Sharing (CORS):** The browser rule that lets the API accept requests only from the web origins it names.

**Data file:** A `.dat` text file that a COBOL program reads as input. Verification gives the same data files to the COBOL program and the Python draft.

**Docker:** Platform for containerizing applications. LegacyLift starts the database, API, runner, and web app with Docker Compose for local development.

**Docker Compose:** A Docker tool that starts several containers together from one configuration file.

**FastAPI:** The Python web framework used to build the LegacyLift API.

**Functional equivalence:** New code produces identical outputs and behavior to the legacy code for the same inputs. Verify marks a program matching when COBOL and Python print exactly the same text.

**Fuzz testing:** Testing a system with malformed, unexpected, or random input to confirm it fails safely.

**Gemini:** Google’s AI model used for AI-assisted translation of review notes and for AI review of converted programs.

**GnuCOBOL (`cobc`):** Open-source COBOL compiler used in the runner container to compile and run original programs during verification.

**Hallucination:** An LLM error that produces output that looks valid but is logically wrong; RAG and rule-based conversion reduce this risk.

**Hashing:** A one-way transformation of a password into a fixed-length value, so the stored value cannot be turned back into the password.

**Integrated Development Environment (IDE):** Collection of tools for coding, debugging, and production in one application.

**JavaScript Object Notation (JSON):** The text format of LegacyLift API requests and responses.

**Job Control Language (JCL):** Scripting language used alongside COBOL on enterprise mainframes.

**Large Language Model (LLM):** Software capable of generative reasoning over large datasets; used in LegacyLift for assisted translation and review, not as the sole converter.

**Major Functional Component Diagram (MFCD):** The diagram of the system's components and their connections.

**Node Package Manager (NPM):** Content distribution framework for web packages (Lab 1 packaging discussion).

**Object-Oriented Programming (OOP):** Style that organizes code into modular classes rather than linear procedures.

**pgvector:** A PostgreSQL extension that stores embeddings and performs similarity search; the planned vector database for RAG.

**PostgreSQL:** An open-source relational database. LegacyLift stores accounts, projects, files, and runs in PostgreSQL.

**Project:** A named set of COBOL programs, copybooks, and data files that are uploaded, converted, and verified together and saved to the owner's account.

**Python:** Interpreted language used for LegacyLift’s converter output and API (Python 3.12 + FastAPI).

**React:** The JavaScript library used to build the pages of the LegacyLift web application.

**Real World Product (RWP):** The complete commercial LegacyLift product, as distinct from the prototype built in CS 411W.

**Retrieval-Augmented Generation (RAG):** Technique that retrieves relevant code, documentation, and patterns before generation so the model sees real context instead of guessing.

**Review note:** A COBOL line the rule-based converter cannot translate, kept as a comment with the original text and line number for human (or AI-assisted) follow-up.

**Run:** One saved execution of the analyze, convert, or verify step on a project, with its time and results.

**Runner:** Isolated Docker service with GnuCOBOL and Python; the only place uploaded COBOL and generated Python execute.

**Software Requirements Specification (SRS):** The Lab 2 document that states what the prototype must do.

**Structured Query Language (SQL):** Default format for enterprise databases such as PostgreSQL (Neon hosts LegacyLift accounts and projects).

**Technical debt:** Accumulated cost of maintaining outdated code; inherent in legacy systems that need specialized knowledge to operate.

**Vector database:** Store optimized for semantic search of embeddings (used with RAG / pgvector for similar verified examples).

**Verification:** Running COBOL and Python on the same project data files and comparing printed output (`verified`, `mismatch`, or `not_verified`).
