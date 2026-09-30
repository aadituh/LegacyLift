"""Project routes and HTTP error handling."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from legacylift.dependencies import ProjectServiceDep
from legacylift.models.project import Project
from legacylift.schemas.projects import (
    AnalysisResponse,
    ConversionResponse,
    CreateProjectRequest,
    ProjectResponse,
    RunsResponse,
    UploadResponse,
    VerifyResponse,
)
from legacylift.services.projects import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def require_project(project_id: str, service: ProjectService) -> Project:
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(request: CreateProjectRequest, service: ProjectServiceDep) -> Project:
    try:
        return service.create_project(request.name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/demo", response_model=ProjectResponse, status_code=201)
def create_demo_project(service: ProjectServiceDep) -> Project:
    """Create a new project with sample files for API exploration."""
    return service.create_demo_project()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, service: ProjectServiceDep) -> Project:
    return require_project(project_id, service)


@router.post("/{project_id}/files", response_model=UploadResponse)
async def upload_files(
    project_id: str, service: ProjectServiceDep, files: list[UploadFile] = File(...)
) -> dict:
    project = require_project(project_id, service)
    try:
        uploaded = await service.add_files(project, files)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project_id": project.id, "files": uploaded}


@router.post("/{project_id}/analyze", response_model=AnalysisResponse)
def analyze(project_id: str, service: ProjectServiceDep) -> dict:
    project = require_project(project_id, service)
    try:
        run, counts = service.analyze(project)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "project_id": project.id,
        "run_id": run.id,
        "status": run.status,
        **counts,
        "note": "File inventory only; dependency analysis is not implemented yet.",
    }


@router.post("/{project_id}/convert", response_model=ConversionResponse)
def convert(project_id: str, service: ProjectServiceDep) -> dict:
    project = require_project(project_id, service)
    try:
        run, generated = service.convert(project)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project_id": project.id, "run_id": run.id, "status": run.status, "files": generated}


@router.post("/{project_id}/verify", response_model=VerifyResponse)
def verify(project_id: str, service: ProjectServiceDep) -> dict:
    project = require_project(project_id, service)
    try:
        run = service.verify(project)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "project_id": project.id,
        "run_id": run.id,
        "status": run.status,
        "passed": None,
        "note": "Demo response only; COBOL and Python outputs were not compared.",
    }


@router.get("/{project_id}/runs", response_model=RunsResponse)
def get_runs(project_id: str, service: ProjectServiceDep) -> dict:
    project = require_project(project_id, service)
    return {"project_id": project.id, "runs": project.runs}
