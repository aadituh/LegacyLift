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

from pydantic import BaseModel, Field

from legacylift.models import (
    ConvertedFile,
    ConvertedProjectFile,
    FileCounts,
    RunStatus,
    RunSummary,
    SourceFile,
)


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
    """Response from ``POST /api/projects/{id}/analyze`` (placeholder).

    Has the ``FileCounts`` fields plus:

    Attributes:
        project_id: The analyzed project.
        run_id: ID of the saved analyze run.
        status: Always ``inventory_only`` for now.
        note: Says that dependency analysis is not built yet.
    """

    project_id: str
    run_id: str
    status: RunStatus
    note: str


class FileEquivalenceResponse(BaseModel):
    """One program's COBOL-versus-Python comparison in a verify response."""

    source_name: str
    python_name: str
    equivalent: bool
    cobol_stdout: str = ""
    python_stdout: str = ""
    error: str | None = None


class VerifyResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/verify``.

    Attributes:
        project_id: The project.
        run_id: ID of the saved verify run.
        status: ``verified``, ``mismatch``, or ``not_verified`` (no GnuCOBOL).
        passed: ``True`` if every program matched, ``False`` on mismatch,
            ``None`` if GnuCOBOL was unavailable.
        note: Short human-readable summary.
        files: Per-program equivalence details.
    """

    project_id: str
    run_id: str
    status: RunStatus
    passed: bool | None
    note: str
    files: list[FileEquivalenceResponse] = []


class RunsResponse(BaseModel):
    """Response from ``GET /api/projects/{id}/runs``.

    Attributes:
        project_id: The project.
        runs: Every run, oldest first, without generated files.
    """

    project_id: str
    runs: list[RunSummary]
