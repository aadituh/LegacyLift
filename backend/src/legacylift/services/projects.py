"""Project workflow: ``ProjectService`` and its helpers.

Create, list, and delete projects; add and remove files; record analyze,
convert, and verify runs.

Every change follows the same pattern: change the ``Project``, then
``store.save(project)``. A lock makes changes happen one at a time, because
FastAPI runs routes on several threads. New files and runs get the project's
next number as their ID (``"1"``, ``"2"``, ...).

Analyze only counts files for now (``inventory_only``). Verify compiles each
program with GnuCOBOL, runs it beside the generated Python, and records whether
stdout matches (``verified`` / ``mismatch`` / ``not_verified`` if ``cobc`` is
missing).
"""

import threading

from legacylift.cobol.equivalence import check_functional_equivalence
from legacylift.errors import InvalidInputError, NotFoundError, ProjectStateError
from legacylift.models import (
    ConvertedProjectFile,
    EquivalenceCheck,
    FileCounts,
    FileKind,
    Project,
    Run,
    RunKind,
    RunStatus,
    SourceFile,
)
from legacylift.sample_data import DEMO_FILES
from legacylift.services.conversion import conversion_status, convert_file, python_file_name
from legacylift.services.uploads import KIND_BY_SUFFIX, RawUpload, decode_upload
from legacylift.storage import ProjectRepository, ProjectStore  # noqa: F401

MAX_PROJECT_FILES = 10


def _cobc_missing(check: EquivalenceCheck) -> bool:
    """True when a check failed only because GnuCOBOL was not installed."""
    if check.error is None:
        return False
    text = check.error.lower()
    return "cobc" in text and "not found" in text


def _verify_status(checks: list[EquivalenceCheck]) -> RunStatus:
    """Pick the verify-run status from per-program equivalence checks."""
    if not checks:
        return RunStatus.NOT_VERIFIED
    if all(_cobc_missing(check) for check in checks):
        return RunStatus.NOT_VERIFIED
    if all(check.equivalent for check in checks):
        return RunStatus.VERIFIED
    return RunStatus.MISMATCH


def file_counts(project: Project) -> FileCounts:
    """Count a project's files by kind.

    Args:
        project: The project.

    Returns:
        How many programs, copybooks, and data files it has.

    Example:
        >>> file_counts(Project(id="1", name="Empty"))
        FileCounts(program_count=0, copybook_count=0, data_file_count=0)
    """
    kinds = [file.kind for file in project.files]
    return FileCounts(
        program_count=kinds.count(FileKind.PROGRAM),
        copybook_count=kinds.count(FileKind.COPYBOOK),
        data_file_count=kinds.count(FileKind.DATA),
    )


class ProjectService:
    """The project workflow: create, list, upload, analyze, convert, verify, delete.

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

    def __init__(self, store: ProjectRepository, *, cobc_path: str | None = None) -> None:
        """Create the service.

        Args:
            store: Where projects are kept and saved.
            cobc_path: Optional path to GnuCOBOL ``cobc`` for verify runs.
        """
        self.store = store
        self.cobc_path = cobc_path
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
            >>> project = service.create_project("  Payroll ")
            >>> project.id, project.name
            ('1', 'Payroll')
        """
        name = name.strip()
        if not name:
            raise InvalidInputError("Project name cannot be blank.")
        with self._lock:
            project = Project(id=self.store.next_id(), name=name)
            self.store.add(project)
        return project

    def create_demo_project(self) -> Project:
        """Create and save a project holding the files in ``sample_data.DEMO_FILES``.

        Returns:
            A project with ``store_report.cbl``, ``order.cpy``, and ``orders.dat``
            (file IDs ``"1"`` to ``"3"``).
        """
        with self._lock:
            project = Project(id=self.store.next_id(), name="LegacyLift demo")
            for name, kind, content in DEMO_FILES:
                self._attach_file(project, name, kind, content)
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

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> service.get_project(service.create_project("Payroll").id).name
            'Payroll'
        """
        project = self.store.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def list_projects(self) -> list[Project]:
        """Return every project, newest first.

        Returns:
            The projects, most recently created first.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> _ = service.create_project("Old"), service.create_project("New")
            >>> [project.name for project in service.list_projects()]
            ['New', 'Old']
        """
        with self._lock:
            return self.store.all()[::-1]

    def delete_project(self, project: Project) -> None:
        """Delete a project, its files, and its runs.

        Args:
            project: The project to delete.
        """
        with self._lock:
            self.store.delete(project.id)

    def delete_file(self, project: Project, file_id: str) -> None:
        """Remove one file from a project. Earlier runs keep their results.

        Args:
            project: The project.
            file_id: The ID returned when the file was uploaded.

        Raises:
            NotFoundError: If the project has no file with that ID.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> project = service.create_demo_project()
            >>> service.delete_file(project, project.files[2].id)
            >>> [file.name for file in project.files]
            ['store_report.cbl', 'order.cpy']
        """
        with self._lock:
            for file in project.files:
                if file.id == file_id:
                    project.files.remove(file)
                    self.store.save(project)
                    return
        raise NotFoundError("File not found.")

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

    def python_file(self, project: Project, run_id: str, python_name: str) -> ConvertedProjectFile:
        """Return one generated Python file from a convert run.

        Args:
            project: The project.
            run_id: The convert run's ID.
            python_name: The generated file name, such as ``PAY.py``.

        Returns:
            The saved conversion for that file.

        Raises:
            NotFoundError: The run does not exist, is not a convert run, or has
                no file with that name.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> project = service.create_demo_project()
            >>> analyze_run, _counts = service.analyze(project)
            >>> service.python_file(project, analyze_run.id, "store_report.py")
            Traceback (most recent call last):
                ...
            legacylift.errors.NotFoundError: That run has no generated Python.
            >>> run = service.convert(project)
            >>> service.python_file(project, run.id, "store_report.py").program_name
            'STORE-REPORT'
        """
        run = self.get_run(project, run_id)
        for converted in run.files:
            if converted.python_name == python_name:
                return converted
        if run.kind is not RunKind.CONVERT:
            raise NotFoundError("That run has no generated Python.")
        raise NotFoundError("Python file not found.")

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
            checked: list[tuple[str, FileKind, str]] = []  # (name, kind, text)
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
                checked.append((upload.name, kind, decode_upload(upload)))

            new_files = [self._attach_file(project, *file) for file in checked]
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
        run = self._save_run(project, RunKind.ANALYZE, RunStatus.INVENTORY_ONLY)
        return run, file_counts(project)

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
        return self._save_run(
            project, RunKind.CONVERT, conversion_status(all_notes), converted_files
        )

    def verify(self, project: Project) -> Run:
        """Run each converted program under GnuCOBOL and compare stdout to Python.

        Uses the latest convert run's drafts. Copybooks in the project are
        written beside the program for ``COPY``. Status is ``verified`` when
        every program matches, ``mismatch`` when any differs or fails, and
        ``not_verified`` when ``cobc`` is not installed.

        Args:
            project: The project to verify.

        Returns:
            The saved verify run (with ``checks`` filled in).

        Raises:
            ProjectStateError: If the project has never been converted.

        Example:
            >>> service = ProjectService(ProjectStore(data_dir=None, max_projects=10))
            >>> project = service.create_demo_project()
            >>> service.verify(project)
            Traceback (most recent call last):
                ...
            legacylift.errors.ProjectStateError: Convert the project before requesting verification.
        """
        convert_runs = [run for run in project.runs if run.kind == RunKind.CONVERT]
        if not convert_runs:
            raise ProjectStateError("Convert the project before requesting verification.")

        latest = convert_runs[-1]
        if not latest.files:
            raise ProjectStateError("The last convert run has no generated Python to verify.")

        by_id = {file.id: file for file in project.files}
        copybooks = {
            file.name: file.content for file in project.files if file.kind == FileKind.COPYBOOK
        }

        checks: list[EquivalenceCheck] = []
        for converted in latest.files:
            source = by_id.get(converted.source_file_id)
            if source is None or source.kind != FileKind.PROGRAM:
                checks.append(
                    EquivalenceCheck(
                        source_name=converted.source_name,
                        python_name=converted.python_name,
                        equivalent=False,
                        error=f"Source program {converted.source_name!r} is missing from the project.",
                    )
                )
                continue
            result = check_functional_equivalence(
                source_name=source.name,
                python_name=converted.python_name,
                cobol_source=source.content,
                python_source=converted.python,
                copybooks=copybooks,
                cobc_path=self.cobc_path,
            )
            checks.append(
                EquivalenceCheck(
                    source_name=result.source_name,
                    python_name=result.python_name,
                    equivalent=result.equivalent,
                    cobol_stdout=result.cobol_stdout,
                    python_stdout=result.python_stdout,
                    error=result.error,
                )
            )

        status = _verify_status(checks)
        return self._save_run(project, RunKind.VERIFY, status, checks=checks)

    def _attach_file(self, project: Project, name: str, kind: FileKind, content: str) -> SourceFile:
        """Add a file with the project's next file ID. The caller holds the lock and saves.

        Returns:
            The new file.
        """
        project.files_added += 1
        file = SourceFile(id=str(project.files_added), name=name, kind=kind, content=content)
        project.files.append(file)
        return file

    def _save_run(
        self,
        project: Project,
        kind: RunKind,
        status: RunStatus,
        files: list[ConvertedProjectFile] | None = None,
        checks: list[EquivalenceCheck] | None = None,
    ) -> Run:
        """Record a step as the project's next run (IDs ``"1"``, ``"2"``, ...) and save.

        Returns:
            The new run.
        """
        with self._lock:
            run = Run(
                id=str(len(project.runs) + 1),
                kind=kind,
                status=status,
                files=files or [],
                checks=checks or [],
            )
            project.runs.append(run)
            self.store.save(project)
        return run
