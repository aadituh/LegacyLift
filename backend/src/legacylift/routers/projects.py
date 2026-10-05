"""Project routes under ``/api/projects``.

List, create, read, and delete projects; upload and remove files; analyze,
convert, and verify; read runs.

Each route reads the request, calls one ``ProjectService`` method, and returns
a body from ``schemas.py``. Service errors become 4xx responses through the
handler in ``main.py``.

Route docstrings: the text before ``\\f`` appears on the /docs page; the rest is
for developers only. Every route with ``{project_id}`` gets the project through
``ProjectDep``, which answers 404 when it does not exist.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from legacylift.dependencies import ProjectDep, ProjectServiceDep
from legacylift.models import Project, Run, RunStatus
from legacylift.responses import python_attachment
from legacylift.schemas import (
    AnalyzeResponse,
    ConvertResponse,
    CreateProjectRequest,
    FileEquivalenceResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
    RunsResponse,
    UploadResponse,
    VerifyResponse,
)
from legacylift.services.projects import file_counts
from legacylift.services.uploads import read_uploads

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    responses={404: {"description": "Project, file, or run not found"}},
)


# response_model=ProjectResponse sends the project without its runs.
@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: CreateProjectRequest, service: ProjectServiceDep) -> Project:
    """Create an empty project.

    \f
    Raises:
        InvalidInputError: The name is only spaces (400).
    """
    return service.create_project(body.name)


@router.get("")
def list_projects(service: ProjectServiceDep) -> ProjectListResponse:
    """List every project, newest first, with file counts and its last run."""
    summaries = [
        ProjectSummary(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            last_run=project.runs[-1] if project.runs else None,
            **file_counts(project).model_dump(),
        )
        for project in service.list_projects()
    ]
    return ProjectListResponse(projects=summaries)


@router.post("/demo", response_model=ProjectResponse, status_code=201)
def create_demo_project(service: ProjectServiceDep) -> Project:
    """Create a new project with sample files for API exploration."""
    return service.create_demo_project()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project: ProjectDep) -> Project:
    """Return a project and the content of its files."""
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project: ProjectDep, service: ProjectServiceDep) -> None:
    """Delete a project with its files and runs."""
    service.delete_project(project)


@router.post("/{project_id}/files")
async def upload_files(
    project: ProjectDep,
    service: ProjectServiceDep,
    files: Annotated[list[UploadFile], File()],
) -> UploadResponse:
    """Add .cbl, .cob, .cpy, or .dat files to a project.

    Send the files as multipart form data in the field `files`. If any file is
    rejected, none are added.

    \f
    Raises:
        InvalidInputError: See ``ProjectService.add_files`` (400).

    Example:
        ``curl -F files=@PAY.cbl -F files=@PAY.cpy http://127.0.0.1:8000/api/projects/<id>/files``
    """
    uploads = await read_uploads(files)
    added = await run_in_threadpool(service.add_files, project, uploads)
    return UploadResponse(project_id=project.id, files=added)


@router.delete("/{project_id}/files/{file_id}", status_code=204)
def delete_file(project: ProjectDep, service: ProjectServiceDep, file_id: str) -> None:
    """Remove one file from a project. Saved runs keep their results.

    \f
    Raises:
        NotFoundError: The project has no file with that ID (404).
    """
    service.delete_file(project, file_id)


@router.post("/{project_id}/analyze")
def analyze_project(project: ProjectDep, service: ProjectServiceDep) -> AnalyzeResponse:
    """Count the project's files by kind. Dependency analysis is not built yet.

    \f
    Raises:
        ProjectStateError: The project has no files (400).
    """
    run, counts = service.analyze(project)
    return AnalyzeResponse(
        project_id=project.id,
        run_id=run.id,
        status=run.status,
        **counts.model_dump(),
        note="File inventory only; dependency analysis is not implemented yet.",
    )


@router.post("/{project_id}/convert")
def convert_project(project: ProjectDep, service: ProjectServiceDep) -> ConvertResponse:
    """Convert every .cbl and .cob file in the project to Python.

    The result is saved; `GET /api/projects/{project_id}/runs/{run_id}` returns it again.

    \f
    Raises:
        ProjectStateError: The project has no programs (400).
        ConversionError: A program cannot be converted (400).
    """
    run = service.convert(project)
    return ConvertResponse(project_id=project.id, run_id=run.id, status=run.status, files=run.files)


@router.post("/{project_id}/verify")
def verify_project(project: ProjectDep, service: ProjectServiceDep) -> VerifyResponse:
    """Compile each program with GnuCOBOL and compare stdout to generated Python.

    Status is ``verified`` when every program matches, ``mismatch`` when any
    differ, and ``not_verified`` when ``cobc`` is not installed.

    \f
    Raises:
        ProjectStateError: The project has never been converted (400).
    """
    run = service.verify(project)
    if run.status == RunStatus.VERIFIED:
        passed: bool | None = True
        note = "COBOL and Python outputs matched for every program."
    elif run.status == RunStatus.MISMATCH:
        passed = False
        note = "COBOL and Python outputs differed, or a program failed to run."
    else:
        passed = None
        note = (
            "GnuCOBOL (cobc) was not available, so outputs were not compared. "
            "Install GnuCOBOL or set LEGACYLIFT_COBC_PATH."
        )
    return VerifyResponse(
        project_id=project.id,
        run_id=run.id,
        status=run.status,
        passed=passed,
        note=note,
        files=[
            FileEquivalenceResponse(
                source_name=check.source_name,
                python_name=check.python_name,
                equivalent=check.equivalent,
                cobol_stdout=check.cobol_stdout,
                python_stdout=check.python_stdout,
                error=check.error,
            )
            for check in run.checks
        ],
    )


@router.get("/{project_id}/runs")
def list_runs(project: ProjectDep) -> RunsResponse:
    """List the project's runs, oldest first, without generated files."""
    return RunsResponse(project_id=project.id, runs=list(project.runs))


@router.get("/{project_id}/runs/{run_id}")
def get_run(project: ProjectDep, service: ProjectServiceDep, run_id: str) -> Run:
    """Return one run. For a convert run, this includes the generated Python."""
    return service.get_run(project, run_id)


@router.get("/{project_id}/runs/{run_id}/files/{python_name}")
def download_run_file(
    project: ProjectDep,
    service: ProjectServiceDep,
    run_id: str,
    python_name: str,
) -> Response:
    """Download one Python file saved on a convert run.

    \f
    Args:
        project: The project from the URL.
        service: The project workflow.
        run_id: The convert run's ID.
        python_name: The generated file name, such as ``PAY.py``.

    Returns:
        The ``.py`` file as an attachment.

    Raises:
        NotFoundError: Unknown run, a run with no Python, or an unknown file (404).
    """
    converted = service.python_file(project, run_id, python_name)
    return python_attachment(converted.python_name, converted.python)
