"""Small project workflow. Parsing and verification will be added later."""

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from legacylift.converter import convert_source
from legacylift.models.project import Project, Run, SourceFile
from legacylift.repositories.projects import ProjectRepository

MAX_PROJECT_FILES = 10
MAX_FILE_BYTES = 100_000
FILE_KINDS = {".cbl": "program", ".cob": "program", ".cpy": "copybook", ".dat": "data"}


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create_project(self, name: str) -> Project:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be blank.")
        return self.repository.create(name)

    def get_project(self, project_id: str) -> Project | None:
        return self.repository.get(project_id)

    async def add_files(self, project: Project, uploads: list[UploadFile]) -> list[SourceFile]:
        if not uploads or len(project.files) + len(uploads) > MAX_PROJECT_FILES:
            raise ValueError(f"A project needs 1 to {MAX_PROJECT_FILES} files.")

        names = {file.name.casefold() for file in project.files}
        output_names = {
            Path(file.name).stem.casefold() for file in project.files if file.kind == "program"
        }
        new_files: list[SourceFile] = []
        for upload in uploads:
            name = Path((upload.filename or "").replace("\\", "/")).name
            suffix = Path(name).suffix.lower()
            if suffix not in FILE_KINDS:
                raise ValueError(f"{name or 'File'} must be .cbl, .cob, .cpy, or .dat.")
            if name.casefold() in names:
                raise ValueError(f"{name} is already in this project.")
            names.add(name.casefold())
            if FILE_KINDS[suffix] == "program":
                stem = Path(name).stem.casefold()
                if stem in output_names:
                    raise ValueError("COBOL program names must produce unique Python file names.")
                output_names.add(stem)

            raw = await upload.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError(f"{name} is larger than 100 KB.")
            try:
                content = raw.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise ValueError(f"{name} must be UTF-8 text.") from error
            if not content.strip() or "\x00" in content:
                raise ValueError(f"{name} is empty or binary.")
            new_files.append(SourceFile(
                id=str(uuid4()), name=name, kind=FILE_KINDS[suffix], content=content
            ))

        # Commit only after every file has passed validation.
        project.files.extend(new_files)
        return new_files

    def convert(self, project: Project) -> tuple[Run, list[dict]]:
        programs = [file for file in project.files if file.kind == "program"]
        if not programs:
            raise ValueError("Upload a .cbl or .cob program before converting.")

        results = []
        for file in programs:
            try:
                draft = convert_source(file.content)
            except ValueError as error:
                raise ValueError(f"{file.name}: {error}") from error
            results.append({
                "source_file_id": file.id,
                "source_name": file.name,
                "python_name": f"{Path(file.name).stem}.py",
                "program_name": draft["program_name"],
                "python": draft["python"],
                "notes": draft["notes"],
                "status": "review_required" if draft["notes"] else "draft",
            })

        status = "review_required" if any(file["notes"] for file in results) else "draft"
        run = Run(id=str(uuid4()), kind="convert", status=status)
        project.runs.append(run)
        return run, results
