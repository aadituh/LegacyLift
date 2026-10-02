"""Request and response bodies for the routes.

Stored data lives in ``models.py``; these classes only shape what goes over
HTTP. Several reuse the stored models directly.
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
        files: One result per uploaded file, in upload order.
    """

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


class VerifyResponse(BaseModel):
    """Response from ``POST /api/projects/{id}/verify`` (placeholder).

    Attributes:
        project_id: The project.
        run_id: ID of the saved verify run.
        status: Always ``not_verified`` for now.
        passed: Always ``None`` until outputs are compared.
        note: Says that no comparison was made.
    """

    project_id: str
    run_id: str
    status: RunStatus
    passed: bool | None
    note: str


class RunsResponse(BaseModel):
    """Response from ``GET /api/projects/{id}/runs``.

    Attributes:
        project_id: The project.
        runs: Every run, oldest first, without generated files.
    """

    project_id: str
    runs: list[RunSummary]
