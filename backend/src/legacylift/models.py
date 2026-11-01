"""The data the backend stores, as Pydantic models.

A ``Project`` holds its files (``SourceFile``) and the steps run on it
(``Run``). ``ProjectStore`` saves that as JSON; ``NeonProjectStore`` saves the
same fields in Postgres. The
converter's output for one program is a ``PythonDraft``; a convert run keeps
one ``ConvertedProjectFile`` per program.

IDs are short numbers as text: projects ``"1"``, ``"2"``, ... across the app
(handed out by ``ProjectStore.next_id``), files and runs ``"1"``, ``"2"``, ...
within their project (handed out by ``ProjectService``). Timestamps fill
themselves in. The enums are ``StrEnum``, so each value is also its text.

Example:
    >>> project = Project(id="1", name="Payroll")
    >>> project.files, project.runs, project.files_added
    ([], [], 0)
    >>> RunStatus.DRAFT == "draft"
    True
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return the current time in UTC, used for ``created_at``.

    Returns:
        A timezone-aware ``datetime``.
    """
    return datetime.now(UTC)


class FileKind(StrEnum):
    """What a project file is, decided by its extension."""

    PROGRAM = "program"  # .cbl or .cob
    COPYBOOK = "copybook"  # .cpy
    DATA = "data"  # .dat


class RunKind(StrEnum):
    """Which pipeline step a run recorded."""

    ANALYZE = "analyze"
    CONVERT = "convert"
    VERIFY = "verify"
    AI_REVIEW = "ai_review"


class RunStatus(StrEnum):
    """The outcome of a run, or of one converted file."""

    INVENTORY_ONLY = "inventory_only"  # legacy analyze that only counted files
    ANALYZED = "analyzed"  # analyze found COPY/CALL links (may include unresolved)
    DRAFT = "draft"  # converted with no review notes, but still unverified
    REVIEW_REQUIRED = "review_required"  # converted with lines marked TODO
    NOT_VERIFIED = "not_verified"  # verify could not compare (runner off or unreachable)
    VERIFIED = "verified"  # COBOL and Python stdout matched for every program
    MISMATCH = "mismatch"  # at least one program differed or failed to run
    CLEAR = "clear"  # AI review found no concerns
    CONCERNS = "concerns"  # AI review found at least one concern


class SourceFile(BaseModel):
    """One file stored in a project.

    Attributes:
        id: Number within its project, such as ``"1"``. Never reused.
        name: File name, such as ``PAY.cbl``.
        kind: Program, copybook, or data.
        content: The file's text.
    """

    id: str
    name: str
    kind: FileKind
    content: str


class PythonDraft(BaseModel):
    """What the converter produces for one COBOL program.

    Attributes:
        program_name: The name after ``PROGRAM-ID``.
        python: The generated Python script.
        notes: ``"Line N: <code>"`` for each line that was not converted.
    """

    program_name: str
    python: str
    notes: list[str]


class ConvertedFile(PythonDraft):
    """A ``PythonDraft`` plus the names of the input and output files.

    Attributes:
        source_name: The COBOL file name, such as ``PAY.cbl``.
        python_name: The generated file name, such as ``PAY.py``.
    """

    source_name: str
    python_name: str


class ConvertedProjectFile(ConvertedFile):
    """A ``ConvertedFile`` from a project, as saved in its convert run.

    Attributes:
        source_file_id: ID of the COBOL file it came from.
        status: ``draft`` or ``review_required``; never verified here.
    """

    source_file_id: str
    status: RunStatus


class EquivalenceCheck(BaseModel):
    """One program's COBOL-versus-Python stdout comparison from a verify run.

    Attributes:
        source_name: COBOL file name.
        python_name: Generated Python file name.
        equivalent: Whether both sides ran and stdout matched exactly.
        cobol_stdout: Output from GnuCOBOL.
        python_stdout: Output from the generated Python.
        error: Failure detail when not equivalent.
        diff: Unified diff from the COBOL output to the Python output; empty when they match.
    """

    source_name: str
    python_name: str
    equivalent: bool
    cobol_stdout: str = ""
    python_stdout: str = ""
    error: str | None = None
    diff: str = ""


class FileCounts(BaseModel):
    """How many files of each kind a project has.

    Attributes:
        program_count: Number of ``.cbl``/``.cob`` files.
        copybook_count: Number of ``.cpy`` files.
        data_file_count: Number of ``.dat`` files.
    """

    program_count: int
    copybook_count: int
    data_file_count: int


class DependencyLink(BaseModel):
    """A resolved COPY, CALL, or PERFORM link from an analyze run."""

    source: str
    target: str
    kind: str  # "copy" | "call" | "perform"
    line: int


class UnresolvedDependency(BaseModel):
    """A COPY, CALL, or PERFORM whose target could not be resolved."""

    source: str
    name: str
    kind: str  # "copy" | "call" | "perform"
    line: int


class AnalyzedField(BaseModel):
    """One data item from a program's WORKING-STORAGE / LINKAGE / copybook data.

    Attributes:
        level: COBOL level number as text (``01``, ``05``, ``88``, …).
        name: Data-item name.
        picture: ``PIC`` clause when present (``None`` for group headers / 88).
        value: ``VALUE`` clause text when present.
        occurs: ``OCCURS n`` count when present.
        line: 1-based source line of the declaration.
        parent: For level-88 conditions, the elementary field name above them.
        section: ``WORKING-STORAGE``, ``LINKAGE``, etc., when known.
    """

    level: str
    name: str
    picture: str | None = None
    value: str | None = None
    occurs: int | None = None
    line: int
    parent: str | None = None
    section: str | None = None


class AnalyzedParagraph(BaseModel):
    """One PROCEDURE DIVISION paragraph (header location, no body text).

    Attributes:
        name: Paragraph name.
        start_line: 1-based line of the paragraph header.
        end_line: 1-based last line before the next paragraph (or end of procedure).
    """

    name: str
    start_line: int
    end_line: int


class ProgramSummary(BaseModel):
    """Per-program inventory from an analyze run (fields + paragraphs).

    Attributes:
        source_name: Project file name (for example ``BANKMAIN.cbl``).
        program_id: ``PROGRAM-ID`` value when present.
        fields: Data items in declaration order.
        paragraphs: Procedure paragraphs in source order.
    """

    source_name: str
    program_id: str
    fields: list[AnalyzedField] = Field(default_factory=list)
    paragraphs: list[AnalyzedParagraph] = Field(default_factory=list)


class LineFinding(BaseModel):
    """One AI observation, tied to COBOL and Python line numbers.

    Attributes:
        cobol_lines: 1-based lines in the COBOL source. Empty if none apply.
        python_lines: 1-based lines in the generated Python. Empty if none apply.
        detail: One sentence on why these lines match or need a human look.
    """

    cobol_lines: list[int] = Field(default_factory=list)
    python_lines: list[int] = Field(default_factory=list)
    detail: str


class FileReview(BaseModel):
    """Gemini's comparison of one program with its generated Python.

    Attributes:
        source_name: COBOL file name.
        python_name: Generated Python file name.
        matches: Behaviors the model could justify from both sources.
        concerns: Lines the rules could not prove, or behavior that may differ.
    """

    source_name: str
    python_name: str
    matches: list[LineFinding] = Field(default_factory=list)
    concerns: list[LineFinding] = Field(default_factory=list)


class RunSummary(BaseModel):
    """A record that one pipeline step ran on a project.

    Attributes:
        id: Number within its project, in run order: ``"1"``, ``"2"``, ...
        kind: Which step ran.
        status: Its outcome.
        created_at: When it ran (UTC).
    """

    id: str
    kind: RunKind
    status: RunStatus
    created_at: datetime = Field(default_factory=utc_now)


class Run(RunSummary):
    """A ``RunSummary`` plus what the step produced.

    Where a field is typed ``RunSummary``, Pydantic writes only the summary
    fields, so run lists stay small.

    Attributes:
        files: The Python generated by a convert run; empty for other runs.
        checks: Equivalence results from a verify run; empty for other runs.
        dependencies: Resolved COPY/CALL/PERFORM links from an analyze run.
        unresolved: COPY/CALL/PERFORM names that could not be resolved.
        programs: Per-program field and paragraph summaries from an analyze run.
        reviews: Per-program AI findings; empty for other runs.
    """

    files: list[ConvertedProjectFile] = []
    checks: list[EquivalenceCheck] = []
    dependencies: list[DependencyLink] = []
    unresolved: list[UnresolvedDependency] = []
    programs: list[ProgramSummary] = []
    reviews: list[FileReview] = []


class User(BaseModel):
    """An account. The password hash stays in storage and is never sent to clients.

    Attributes:
        id: UUID text.
        email: Lowercase email, unique.
        password_hash: Argon2 hash. Not a password.
        display_name: Name shown in the header.
        created_at: When the account was created (UTC).
    """

    id: str
    email: str
    password_hash: str
    display_name: str
    created_at: datetime = Field(default_factory=utc_now)


class Project(BaseModel):
    """A set of COBOL files and the history of steps run on them.

    Attributes:
        id: Number across the app, such as ``"1"``.
        name: Name given by the user.
        created_at: When the project was created (UTC).
        files: Stored files, in upload order.
        runs: Steps run so far, oldest first.
        files_added: How many files were ever added, including deleted ones.
            The next file's ID is this plus one. Saved, but not sent to clients.
        owner_id: Account that owns the project, or ``None`` when login is off.
    """

    id: str
    name: str
    created_at: datetime = Field(default_factory=utc_now)
    files: list[SourceFile] = []
    runs: list[Run] = []
    files_added: int = 0
    owner_id: str | None = None
