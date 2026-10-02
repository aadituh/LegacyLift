"""Project routes. Service errors become 4xx responses through the handler in main.py.

Route docstrings: the text before ``\\f`` appears on the /docs page; the rest is
for developers only. Every route with ``{project_id}`` gets the project through
``ProjectDep``, which answers 404 when it does not exist.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from legacylift.dependencies import ProjectDep, ProjectServiceDep
from legacylift.models import Project, Run
from legacylift.schemas import (
    AnalyzeResponse,
    ConvertResponse,
    CreateProjectRequest,
    ProjectResponse,
    RunsResponse,
    UploadResponse,
    VerifyResponse,
)
from legacylift.services.uploads import read_uploads

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    responses={404: {"description": "Project or run not found"}},
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


@router.post("/demo", response_model=ProjectResponse, status_code=201)
def create_demo_project(service: ProjectServiceDep) -> Project:
    """Create a new project with sample files for API exploration."""
    return service.create_demo_project()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project: ProjectDep) -> Project:
    """Return a project and the content of its files."""
    return project


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
    added = service.add_files(project, await read_uploads(files))
    return UploadResponse(project_id=project.id, files=added)


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
    """Placeholder: record a verify run without comparing COBOL and Python output.

    \f
    Raises:
        ProjectStateError: The project has never been converted (400).
    """
    run = service.verify(project)
    return VerifyResponse(
        project_id=project.id,
        run_id=run.id,
        status=run.status,
        passed=None,
        note="Demo response only; COBOL and Python outputs were not compared.",
    )


@router.get("/{project_id}/runs")
def list_runs(project: ProjectDep) -> RunsResponse:
    """List the project's runs, oldest first, without generated files."""
    return RunsResponse(project_id=project.id, runs=list(project.runs))


@router.get("/{project_id}/runs/{run_id}")
def get_run(project: ProjectDep, service: ProjectServiceDep, run_id: str) -> Run:
    """Return one run. For a convert run, this includes the generated Python."""
    return service.get_run(project, run_id)
