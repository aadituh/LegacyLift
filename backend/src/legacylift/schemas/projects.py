"""JSON shapes shared with the frontend."""

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FileResponse(BaseModel):
    id: str
    name: str
    kind: str
    content: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    files: list[FileResponse]


class UploadResponse(BaseModel):
    project_id: str
    files: list[FileResponse]


class GeneratedFileResponse(BaseModel):
    source_file_id: str
    source_name: str
    python_name: str
    program_name: str
    python: str
    notes: list[str]
    status: str  # draft or review_required; never verified here


class ConversionResponse(BaseModel):
    project_id: str
    run_id: str
    status: str
    files: list[GeneratedFileResponse]


class AnalysisResponse(BaseModel):
    project_id: str
    run_id: str
    status: str
    program_count: int
    copybook_count: int
    data_file_count: int
    note: str


class VerifyResponse(BaseModel):
    project_id: str
    run_id: str
    status: str
    passed: bool | None
    note: str


class RunResponse(BaseModel):
    id: str
    kind: str
    status: str


class RunsResponse(BaseModel):
    project_id: str
    runs: list[RunResponse]
