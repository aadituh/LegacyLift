"""Request and response bodies for the routes.

Stored data lives in ``models.py``; these classes only shape what goes over
HTTP. A field typed ``RunSummary`` sends only the summary fields, even when it
holds a full ``Run``, so lists stay small.

Example:
    >>> from legacylift.models import Run, RunKind, RunStatus
    >>> run = Run(id="1", kind=RunKind.VERIFY, status=RunStatus.NOT_VERIFIED)
    >>> "files" in RunsResponse(project_id="1", runs=[run]).model_dump()["runs"][0]
    False
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from legacylift.cobol.describe import ProgramDescription
from legacylift.models import (
    ConvertedFile,
    ConvertedProjectFile,
    DependencyLink,
    FileCounts,
    FileReview,
    ProgramSummary,
    RunStatus,
    RunSummary,
    SourceFile,
    UnresolvedDependency,
)

# Example payload shown in Swagger UI at GET /docs for POST .../analyze (issue #24).
_ANALYZE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "project_id": "1",
    "run_id": "1",
    "status": "analyzed",
    "program_count": 3,
    "copybook_count": 2,
    "data_file_count": 0,
    "dependencies": [
        {"source": "BANKMAIN.cbl", "target": "ACCTDEF.cpy", "kind": "copy", "line": 41},
        {"source": "BANKMAIN.cbl", "target": "TXNDEF.cpy", "kind": "copy", "line": 44},
        {"source": "BANKMAIN.cbl", "target": "TXNPOST.cbl", "kind": "call", "line": 116},
        {"source": "BANKMAIN.cbl", "target": "INTCALC.cbl", "kind": "call", "line": 156},
        {
            "source": "BANKMAIN.cbl:MAIN-LOGIC",
            "target": "LOAD-ACCOUNTS",
            "kind": "perform",
            "line": 74,
        },
        {"source": "TXNPOST.cbl", "target": "ACCTDEF.cpy", "kind": "copy", "line": 17},
        {"source": "INTCALC.cbl", "target": "ACCTDEF.cpy", "kind": "copy", "line": 15},
    ],
    "unresolved": [],
    "programs": [
        {
            "source_name": "BANKMAIN.cbl",
            "program_id": "BANKMAIN",
            "fields": [
                {
                    "level": "01",
                    "name": "WS-ACCOUNT-COUNT",
                    "picture": "9(3)",
                    "value": "0",
                    "occurs": None,
                    "line": 48,
                    "parent": None,
                    "section": "WORKING-STORAGE",
                }
            ],
            "paragraphs": [
                {"name": "MAIN-LOGIC", "start_line": 72, "end_line": 78},
                {"name": "LOAD-ACCOUNTS", "start_line": 79, "end_line": 92},
            ],
        }
    ],
}


class RegisterRequest(BaseModel):
    """Body of ``POST /api/auth/register``.

    Attributes:
        email: Stored lowercase. A second sign-up with the same email is 409.
        password: 8 to 128 characters, with a letter and a number. Not stored.
        display_name: 1 to 100 characters after spaces are removed.
    """

    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    """Body of ``POST /api/auth/login``.

    Attributes:
        email: The account email.
        password: The account password. A mismatch is the same 401 as an unknown email.
    """

    email: str
    password: str


class UserResponse(BaseModel):
    """An account with no password and no password hash.

    Attributes:
        id: Account ID.
        email: Lowercase email.
        display_name: Name shown in the header.
        created_at: When the account was created (UTC).
    """

    id: str
    email: str
    display_name: str
    created_at: datetime


class LoginResponse(BaseModel):
    """Response from ``POST /api/auth/login``.

    Attributes:
        token: Signed JWT. Send it as ``Authorization: Bearer <token>``.
        token_type: Always ``bearer``.
        expires_in: Seconds until the token expires.
    """

    token: str
    token_type: str = "bearer"
    expires_in: int


class CreateProjectRequest(BaseModel):
    """Body of ``POST /api/projects``.

    Attributes:
        name: 1 to 100 characters, and not only spaces.
    """

    name: str = Field(min_length=1, max_length=100)


class ProjectResponse(BaseModel):
    """A project and its files, without its runs.

    Attributes:
        id: The project's ID; use it in every ``/api/projects/{id}`` route.
        name: The project name.
        created_at: When it was created (UTC).
        files: Its files, in upload order.
    """

    id: str
    name: str
    created_at: datetime
    files: list[SourceFile]


class ProjectSummary(FileCounts):
    """One project in the project list: no file contents and no runs.

    Has the ``FileCounts`` fields plus:

    Attributes:
        id: The project's ID.
        name: The project name.
        created_at: When it was created (UTC).
        last_run: The most recent run without its files, or ``None`` if no
            step has run yet.
    """

    id: str
    name: str
    created_at: datetime
    last_run: RunSummary | None


class ProjectListResponse(BaseModel):
    """Response from ``GET /api/projects``.

    Attributes:
        projects: Every project, newest first.
    """

    projects: list[ProjectSummary]


class UploadResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/files``.

    Attributes:
        project_id: The project the files were added to.
        files: Only the files added by this request.
    """

    project_id: str
    files: list[SourceFile]


class ConvertFilesResponse(BaseModel):
    """Response from ``POST /api/convert``.

    Attributes:
        download_id: Use this in ``GET /api/convert/{download_id}/files/{name}``.
            The file is kept in memory until the API restarts.
        files: One result per uploaded file, in upload order.
    """

    download_id: str
    files: list[ConvertedFile]


class ConvertResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/convert``.

    Attributes:
        project_id: The converted project.
        run_id: ID of the saved convert run; ``GET .../runs/{run_id}`` returns it again.
        status: ``review_required`` if any file has notes, otherwise ``draft``.
        files: One result per program.
    """

    project_id: str
    run_id: str
    status: RunStatus
    files: list[ConvertedProjectFile]


class AnalyzeResponse(FileCounts):
    """Response from ``POST /api/projects/{id}/analyze``.

    Has the ``FileCounts`` fields plus:

    Attributes:
        project_id: The analyzed project.
        run_id: ID of the saved analyze run.
        status: ``analyzed`` after COPY/CALL/PERFORM dependency discovery.
        dependencies: Resolved COPY/CALL/PERFORM links (matched file or paragraph).
        unresolved: COPY/CALL/PERFORM names that could not be resolved.
        programs: Per-program field and paragraph summaries (what to convert together).
    """

    model_config = ConfigDict(json_schema_extra={"examples": [_ANALYZE_RESPONSE_EXAMPLE]})

    project_id: str
    run_id: str
    status: RunStatus
    dependencies: list[DependencyLink] = Field(default_factory=list)
    unresolved: list[UnresolvedDependency] = Field(default_factory=list)
    programs: list[ProgramSummary] = Field(default_factory=list)


class DescribeResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/describe``.

    Attributes:
        project_id: The described project.
        programs: One plain-language summary per program file.
        shared_data: Which files and copybooks those programs share.
    """

    project_id: str
    programs: list[ProgramDescription]
    shared_data: str


class FileEquivalenceResponse(BaseModel):
    """One program's COBOL-versus-Python comparison in a verify response."""

    source_name: str
    python_name: str
    equivalent: bool
    cobol_stdout: str = ""
    python_stdout: str = ""
    error: str | None = None
    diff: str = ""


class VerifyResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/verify``.

    Attributes:
        project_id: The project.
        run_id: ID of the saved verify run.
        status: ``verified``, ``mismatch``, or ``not_verified`` (runner off or unreachable).
        passed: ``True`` if every program matched, ``False`` on mismatch,
            ``None`` if nothing was compared.
        note: Short human-readable summary.
        files: Per-program equivalence details, one per main program (programs
            that another program calls run as part of their caller).
    """

    project_id: str
    run_id: str
    status: RunStatus
    passed: bool | None
    note: str
    files: list[FileEquivalenceResponse] = []


class GroqUsageResponse(BaseModel):
    """Groq TPM and RPD state for one model.

    Attributes:
        model: Groq model id.
        limit_tokens: TPM limit. ``None`` until a response includes the header.
        remaining_tokens: TPM remaining.
        reset_tokens: TPM reset delay, such as ``7.66s``.
        limit_requests: RPD limit.
        remaining_requests: RPD remaining.
        reset_requests: RPD reset delay, such as ``2m59.56s``.
        session_requests: Calls counted in this process.
        session_tokens: Tokens counted in this process.
        has_header_data: False until Groq has sent a limit header.
        low_budget: Remaining TPM or RPD is under the configured fraction.
        rate_limited_until: Epoch seconds. ``None`` when Groq is not in a 429 window.
        warning: A short warning, or an empty string.
    """

    model: str
    limit_tokens: int | None = None
    remaining_tokens: int | None = None
    reset_tokens: str | None = None
    limit_requests: int | None = None
    remaining_requests: int | None = None
    reset_requests: str | None = None
    session_requests: int = 0
    session_tokens: int = 0
    has_header_data: bool = False
    low_budget: bool = False
    rate_limited_until: float | None = None
    warning: str = ""


class ProviderModelResponse(BaseModel):
    """One model the UI can put in a dropdown.

    Attributes:
        id: Model id sent back on the next review.
        name: Label shown to the user.
    """

    id: str
    name: str


class ProviderOptionsResponse(BaseModel):
    """Model lists, OpenRouter caps, and Groq usage. API keys are not included.

    Attributes:
        gemini_model: The existing Gemini model id.
        groq_configured: True when ``LEGACYLIFT_GROQ_API_KEY`` is set.
        openrouter_configured: True when ``LEGACYLIFT_OPENROUTER_API_KEY`` is set.
        groq_models: Models returned by Groq for this key.
        openrouter_models: The free OpenRouter models this app is allowed to use.
        openrouter_requests_per_day: Local daily cap. This app does not track
            OpenRouter with a progress bar.
        openrouter_requests_per_minute: Local per-minute cap.
        low_budget_fraction: Share of TPM or RPD that triggers a Groq warning.
        groq_usage: One snapshot per Groq model that has been listed or called.
        catalog_error: Empty, or a short reason a model list could not be loaded.
    """

    gemini_model: str
    groq_configured: bool
    openrouter_configured: bool
    groq_models: list[ProviderModelResponse] = []
    openrouter_models: list[ProviderModelResponse] = []
    openrouter_requests_per_day: int
    openrouter_requests_per_minute: int
    low_budget_fraction: float
    groq_usage: list[GroqUsageResponse] = []
    catalog_error: str = ""


class AIReviewResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/ai-review``.

    Attributes:
        project_id: The project.
        run_id: ID of the saved AI review run.
        status: ``clear`` when every program has no concerns, otherwise ``concerns``.
        model: The model id that produced the review. Gemini stays
            ``gemini-3.5-flash-lite`` when that provider answers.
        files: One comparison per program, each with ``matches`` and ``concerns``.
            Every finding has ``cobol_lines``, ``python_lines``, and ``detail``.
        provider: ``gemini``, ``groq``, or ``openrouter``.
        routing_note: Why that provider was chosen, including a fallback.
        groq_usage: Latest Groq snapshot for the Groq model on the request.
            ``None`` is not used; a snapshot with ``has_header_data`` false means
            Groq has not answered yet.
    """

    project_id: str
    run_id: str
    status: RunStatus
    model: str
    files: list[FileReview] = []
    provider: str = "gemini"
    routing_note: str = ""
    groq_usage: GroqUsageResponse | None = None


class RunsResponse(BaseModel):
    """Response from ``GET /api/projects/{id}/runs``.

    Attributes:
        project_id: The project.
        runs: Every run, oldest first, without generated files.
    """

    project_id: str
    runs: list[RunSummary]
