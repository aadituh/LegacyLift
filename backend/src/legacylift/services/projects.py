"""Project workflow: store files, and record analyze, convert, and verify runs.

Every change follows the same pattern: change the ``Project``, then
``store.save(project)``. A lock makes changes happen one at a time, because
FastAPI runs routes on several threads.

Dependency analysis and COBOL-versus-Python verification are not built yet;
their runs say so in their status instead of reporting success.
"""

import threading

from legacylift.errors import InvalidInputError, NotFoundError, ProjectStateError
from legacylift.models import (
    ConvertedProjectFile,
    FileCounts,
    FileKind,
    Project,
    Run,
    RunKind,
    RunStatus,
    SourceFile,
)
from legacylift.sample_data import DEMO_FILES
from legacylift.services.conversion import convert_file, python_file_name
from legacylift.services.uploads import RawUpload, decode_upload
from legacylift.storage import ProjectStore

MAX_PROJECT_FILES = 10
KIND_BY_SUFFIX = {
    ".cbl": FileKind.PROGRAM,
    ".cob": FileKind.PROGRAM,
    ".cpy": FileKind.COPYBOOK,
    ".dat": FileKind.DATA,
}


def conversion_status(notes: list[str]) -> RunStatus:
    """Pick the status for converted code.

    Args:
        notes: Review notes; one per line that was not converted.

    Returns:
        ``REVIEW_REQUIRED`` if there are notes, otherwise ``DRAFT``.

    Example:
        >>> conversion_status(["Line 6: PERFORM PRINT-TOTAL"])
        <RunStatus.REVIEW_REQUIRED: 'review_required'>
    """
    return RunStatus.REVIEW_REQUIRED if notes else RunStatus.DRAFT


class ProjectService:
    """The project workflow: create, upload, analyze, convert, verify.

    Routes call these methods. Each step is saved as a ``Run`` on the project;
    a convert run also keeps the generated Python.

    Example:
        >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
        >>> project = service.create_demo_project()
        >>> run = service.convert(project)
        >>> run.kind, run.status, run.files[0].python_name
        (<RunKind.CONVERT: 'convert'>, <RunStatus.DRAFT: 'draft'>, 'store_report.py')
        >>> service.get_run(project, run.id) is run
        True
    """

    def __init__(self, store: ProjectStore) -> None:
        """Create the service.

        Args:
            store: Where projects are kept and saved.
        """
        self.store = store
        self._lock = threading.Lock()

    def create_project(self, name: str) -> Project:
        """Create and save an empty project.

        Args:
            name: The project name. Spaces at either end are removed.

        Returns:
            The new project.

        Raises:
            InvalidInputError: If the name is blank.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> service.create_project("  Payroll ").name
            'Payroll'
        """
        name = name.strip()
        if not name:
            raise InvalidInputError("Project name cannot be blank.")
        project = Project(name=name)
        with self._lock:
            self.store.add(project)
        return project

    def create_demo_project(self) -> Project:
        """Create and save a project holding the files in ``sample_data.DEMO_FILES``.

        Returns:
            A project with ``store_report.cbl``, ``order.cpy``, and ``orders.dat``.
        """
        files = [
            SourceFile(name=name, kind=kind, content=content) for name, kind, content in DEMO_FILES
        ]
        project = Project(name="LegacyLift demo", files=files)
        with self._lock:
            self.store.add(project)
        return project

    def get_project(self, project_id: str) -> Project:
        """Look up a project.

        Args:
            project_id: The ID returned when the project was created.

        Returns:
            The project.

        Raises:
            NotFoundError: If no project has that ID. Routes return 404.
        """
        project = self.store.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def get_run(self, project: Project, run_id: str) -> Run:
        """Look up one of a project's runs, including any generated Python.

        Args:
            project: The project.
            run_id: The ID returned when the step ran.

        Returns:
            The run.

        Raises:
            NotFoundError: If the project has no run with that ID.
        """
        for run in project.runs:
            if run.id == run_id:
                return run
        raise NotFoundError("Run not found.")

    def add_files(self, project: Project, uploads: list[RawUpload]) -> list[SourceFile]:
        """Check uploaded files, then add and save all of them, or none.

        Args:
            project: The project to add to.
            uploads: The uploaded files.

        Returns:
            The new files, in upload order.

        Raises:
            InvalidInputError: If the project would have more than 10 files, a
                type is not ``.cbl``/``.cob``/``.cpy``/``.dat``, a name is already
                used (ignoring case), two programs would make the same ``.py``
                name, or a file fails ``decode_upload``.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> project = service.create_project("Payroll")
            >>> upload = RawUpload(name="PAY.cpy", data=b"01 PAY PIC 9.")
            >>> service.add_files(project, [upload])[0].kind
            <FileKind.COPYBOOK: 'copybook'>
            >>> service.add_files(project, [RawUpload(name="notes.txt", data=b"hi")])
            Traceback (most recent call last):
                ...
            legacylift.errors.InvalidInputError: notes.txt must be .cbl, .cob, .cpy, or .dat.
        """
        with self._lock:
            if not uploads or len(project.files) + len(uploads) > MAX_PROJECT_FILES:
                raise InvalidInputError(f"A project needs 1 to {MAX_PROJECT_FILES} files.")

            # Names are compared in lowercase, so PAY.cbl and pay.CBL clash.
            taken_names = {file.name.casefold() for file in project.files}
            taken_python_names = {
                python_file_name(file.name).casefold()
                for file in project.files
                if file.kind == FileKind.PROGRAM
            }
            new_files = []
            for upload in uploads:
                kind = KIND_BY_SUFFIX.get(upload.suffix)
                if kind is None:
                    raise InvalidInputError(
                        f"{upload.name or 'File'} must be .cbl, .cob, .cpy, or .dat."
                    )
                if upload.name.casefold() in taken_names:
                    raise InvalidInputError(f"{upload.name} is already in this project.")
                taken_names.add(upload.name.casefold())
                if kind == FileKind.PROGRAM:
                    python_name = python_file_name(upload.name).casefold()
                    if python_name in taken_python_names:
                        raise InvalidInputError(
                            "COBOL program names must produce unique Python file names."
                        )
                    taken_python_names.add(python_name)
                content = decode_upload(upload)
                new_files.append(SourceFile(name=upload.name, kind=kind, content=content))

            project.files.extend(new_files)
            self.store.save(project)
        return new_files

    def analyze(self, project: Project) -> tuple[Run, FileCounts]:
        """Count a project's files by kind and save an analyze run.

        A placeholder until dependency analysis is built, which is why the run
        status is ``INVENTORY_ONLY``.

        Args:
            project: The project to analyze.

        Returns:
            The saved run, and the file counts.

        Raises:
            ProjectStateError: If the project has no files.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> run, counts = service.analyze(service.create_demo_project())
            >>> run.status, counts.program_count, counts.copybook_count, counts.data_file_count
            (<RunStatus.INVENTORY_ONLY: 'inventory_only'>, 1, 1, 1)
        """
        if not project.files:
            raise ProjectStateError("Upload files before analyzing.")
        kinds = [file.kind for file in project.files]
        counts = FileCounts(
            program_count=kinds.count(FileKind.PROGRAM),
            copybook_count=kinds.count(FileKind.COPYBOOK),
            data_file_count=kinds.count(FileKind.DATA),
        )
        run = self._save_run(project, Run(kind=RunKind.ANALYZE, status=RunStatus.INVENTORY_ONLY))
        return run, counts

    def convert(self, project: Project) -> Run:
        """Convert every program in a project and save the results in a convert run.

        Copybooks and data files are skipped.

        Args:
            project: The project to convert.

        Returns:
            The saved run. ``run.files`` holds one result per program. The run's
            status is ``REVIEW_REQUIRED`` if any file has notes, otherwise ``DRAFT``.

        Raises:
            ProjectStateError: If the project has no ``.cbl`` or ``.cob`` files.
            ConversionError: If a program cannot be converted.
        """
        programs = [file for file in project.files if file.kind == FileKind.PROGRAM]
        if not programs:
            raise ProjectStateError("Upload a .cbl or .cob program before converting.")

        converted_files = []
        for program in programs:
            converted = convert_file(program.name, program.content)
            converted_files.append(
                ConvertedProjectFile(
                    **converted.model_dump(),
                    source_file_id=program.id,
                    status=conversion_status(converted.notes),
                )
            )
        all_notes = [note for converted in converted_files for note in converted.notes]
        run = Run(kind=RunKind.CONVERT, status=conversion_status(all_notes), files=converted_files)
        return self._save_run(project, run)

    def verify(self, project: Project) -> Run:
        """Save a verify run without comparing anything yet.

        A placeholder: the status is always ``NOT_VERIFIED`` until COBOL and
        Python outputs are compared with GnuCOBOL.

        Args:
            project: The project to verify.

        Returns:
            The saved run.

        Raises:
            ProjectStateError: If the project has never been converted.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> project = service.create_demo_project()
            >>> service.verify(project)
            Traceback (most recent call last):
                ...
            legacylift.errors.ProjectStateError: Convert the project before requesting verification.
            >>> _ = service.convert(project)
            >>> service.verify(project).status
            <RunStatus.NOT_VERIFIED: 'not_verified'>
        """
        if not any(run.kind == RunKind.CONVERT for run in project.runs):
            raise ProjectStateError("Convert the project before requesting verification.")
        return self._save_run(project, Run(kind=RunKind.VERIFY, status=RunStatus.NOT_VERIFIED))

    def _save_run(self, project: Project, run: Run) -> Run:
        """Append a run to the project, save the project, and return the run."""
        with self._lock:
            project.runs.append(run)
            self.store.save(project)
        return run
