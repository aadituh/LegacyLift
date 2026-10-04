"""Save projects in Neon Postgres.

Used when ``DATABASE_URL`` is set. The tables match ``models.py``: a project,
its source files, and its runs (including generated Python). ``ProjectService``
calls the same methods as ``ProjectStore``.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from legacylift.models import (
    ConvertedProjectFile,
    FileKind,
    Project,
    Run,
    RunKind,
    RunStatus,
    SourceFile,
)


def find_schema() -> Path:
    """Return ``database/schema.sql`` from the repository that contains this file.

    Returns:
        The schema file.

    Raises:
        FileNotFoundError: If this checkout has no ``database/schema.sql``.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "database" / "schema.sql"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("database/schema.sql")


SCHEMA_PATH = find_schema()
ProjectConnection = Connection[dict[str, Any]]


def _datetime(value: object) -> datetime:
    """Return ``value`` when Postgres sent a datetime."""
    if isinstance(value, datetime):
        return value
    raise TypeError("expected a datetime from Postgres")


def _int(value: object) -> int:
    """Return ``value`` when Postgres sent an int."""
    if isinstance(value, int):
        return value
    raise TypeError("expected an int from Postgres")


def _notes(value: object) -> list[str]:
    """Return review notes stored as a JSON array."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def connection_string(database_url: str) -> str:
    """Turn a Neon or SQLAlchemy URL into a psycopg connection string.

    Args:
        database_url: A ``postgresql://`` URL, or ``postgresql+psycopg://``.

    Returns:
        A URL psycopg can open.
    """
    url = database_url.strip()
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url.removeprefix("postgresql+psycopg://")
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def project_from_parts(
    project_row: dict[str, Any],
    file_rows: list[dict[str, Any]],
    run_rows: list[dict[str, Any]],
    converted_rows: list[dict[str, Any]],
) -> Project:
    """Build a ``Project`` from the rows stored for it.

    Args:
        project_row: The ``projects`` row.
        file_rows: Its ``source_files`` rows, in upload order.
        run_rows: Its ``runs`` rows, oldest first.
        converted_rows: Generated files for those runs, in file order.

    Returns:
        The project those rows describe.
    """
    files_by_run: dict[str, list[ConvertedProjectFile]] = {}
    for row in converted_rows:
        run_id = str(row["run_id"])
        files_by_run.setdefault(run_id, []).append(
            ConvertedProjectFile(
                source_file_id=str(row["source_file_id"]),
                source_name=str(row["source_name"]),
                python_name=str(row["python_name"]),
                program_name=str(row["program_name"]),
                python=str(row["python"]),
                notes=_notes(row["notes"]),
                status=RunStatus(str(row["status"])),
            )
        )
    return Project(
        id=str(project_row["id"]),
        name=str(project_row["name"]),
        created_at=_datetime(project_row["created_at"]),
        files_added=_int(project_row["files_added"]),
        files=[
            SourceFile(
                id=str(row["id"]),
                name=str(row["name"]),
                kind=FileKind(str(row["kind"])),
                content=str(row["content"]),
            )
            for row in file_rows
        ],
        runs=[
            Run(
                id=str(row["id"]),
                kind=RunKind(str(row["kind"])),
                status=RunStatus(str(row["status"])),
                created_at=_datetime(row["created_at"]),
                files=files_by_run.get(str(row["id"]), []),
            )
            for row in run_rows
        ],
    )


class NeonProjectStore:
    """Projects, files, and runs in Neon Postgres.

    ``database/schema.sql`` is applied on startup. IDs come from ``project_id_counter``
    and are never reused. Not thread-safe on its own: ``ProjectService`` makes
    one change at a time.
    """

    def __init__(self, database_url: str, max_projects: int) -> None:
        """Connect and make sure the tables exist.

        Args:
            database_url: Neon connection string.
            max_projects: How many projects to keep.
        """
        self.max_projects = max_projects
        self._pool = ConnectionPool(
            connection_string(database_url),
            min_size=1,
            max_size=4,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        with self._rows() as connection:
            self._apply_schema(connection)
            connection.commit()

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.close()

    def next_id(self) -> str:
        """Hand out the next project ID, one higher than any ID given before.

        Returns:
            ``"1"`` for the first project, then ``"2"``, ``"3"``, ...
        """
        with self._rows() as connection:
            row = connection.execute(
                """
                UPDATE project_id_counter
                SET last_number = last_number + 1
                WHERE singleton
                RETURNING last_number
                """
            ).fetchone()
            connection.commit()
        if row is None:
            raise RuntimeError("project_id_counter is missing")
        return str(row["last_number"])

    def get(self, project_id: str) -> Project | None:
        """Find a project by ID.

        Args:
            project_id: The project's ID.

        Returns:
            The project, or ``None`` if there is none with that ID.
        """
        with self._rows() as connection:
            return self._load(connection, project_id)

    def all(self) -> list[Project]:
        """Return every stored project, oldest first.

        Returns:
            The projects in the order they were created.
        """
        with self._rows() as connection:
            rows = connection.execute("SELECT id FROM projects ORDER BY created_at, id").fetchall()
            return [
                project
                for row in rows
                if (project := self._load(connection, str(row["id"]))) is not None
            ]

    def delete(self, project_id: str) -> None:
        """Remove a project, its files, and its runs.

        Args:
            project_id: The project's ID.
        """
        with self._rows() as connection:
            connection.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            connection.commit()

    def add(self, project: Project) -> None:
        """Insert a project, then drop the oldest projects past the limit.

        Args:
            project: The new project.
        """
        with self._rows() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, name, created_at, files_added)
                VALUES (%s, %s, %s, %s)
                """,
                (project.id, project.name, project.created_at, project.files_added),
            )
            self._replace_children(connection, project)
            self._trim(connection)
            connection.commit()

    def save(self, project: Project) -> None:
        """Write a changed project. Does nothing if it was already deleted.

        Args:
            project: The changed project.
        """
        with self._rows() as connection:
            updated = connection.execute(
                """
                UPDATE projects
                SET name = %s, created_at = %s, files_added = %s
                WHERE id = %s
                """,
                (project.name, project.created_at, project.files_added, project.id),
            )
            if updated.rowcount == 0:
                connection.rollback()
                return
            self._replace_children(connection, project)
            connection.commit()

    @contextmanager
    def _rows(self) -> Iterator[ProjectConnection]:
        """Lend a connection whose rows are dictionaries."""
        with self._pool.connection() as connection:
            yield cast(ProjectConnection, connection)

    def _apply_schema(self, connection: ProjectConnection) -> None:
        """Create the tables and the ID counter if they are not there yet."""
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in schema.split(";"):
            sql = statement.strip()
            if sql:
                connection.execute(sql)
        connection.execute(
            """
            INSERT INTO project_id_counter (singleton, last_number)
            VALUES (TRUE, 0)
            ON CONFLICT (singleton) DO NOTHING
            """
        )
        connection.execute(
            """
            UPDATE project_id_counter
            SET last_number = GREATEST(
                last_number,
                COALESCE(
                    (SELECT MAX(id::integer) FROM projects WHERE id ~ '^[0-9]+$'),
                    0
                )
            )
            WHERE singleton
            """
        )

    def _load(self, connection: ProjectConnection, project_id: str) -> Project | None:
        """Read one project and its files and runs."""
        project_row = connection.execute(
            """
            SELECT id, name, created_at, files_added
            FROM projects
            WHERE id = %s
            """,
            (project_id,),
        ).fetchone()
        if project_row is None:
            return None
        file_rows = connection.execute(
            """
            SELECT id, name, kind, content
            FROM source_files
            WHERE project_id = %s
            ORDER BY position
            """,
            (project_id,),
        ).fetchall()
        run_rows = connection.execute(
            """
            SELECT id, kind, status, created_at
            FROM runs
            WHERE project_id = %s
            ORDER BY position
            """,
            (project_id,),
        ).fetchall()
        converted_rows = connection.execute(
            """
            SELECT run_id, source_file_id, source_name, python_name,
                   program_name, python, notes, status
            FROM converted_files
            WHERE project_id = %s
            ORDER BY run_id, position
            """,
            (project_id,),
        ).fetchall()
        return project_from_parts(project_row, file_rows, run_rows, converted_rows)

    def _replace_children(self, connection: ProjectConnection, project: Project) -> None:
        """Replace a project's files and runs with what it holds now."""
        connection.execute("DELETE FROM source_files WHERE project_id = %s", (project.id,))
        connection.execute("DELETE FROM runs WHERE project_id = %s", (project.id,))
        for position, source in enumerate(project.files):
            connection.execute(
                """
                INSERT INTO source_files (project_id, id, name, kind, content, position)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (project.id, source.id, source.name, source.kind.value, source.content, position),
            )
        for position, run in enumerate(project.runs):
            connection.execute(
                """
                INSERT INTO runs (project_id, id, kind, status, created_at, position)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    project.id,
                    run.id,
                    run.kind.value,
                    run.status.value,
                    run.created_at,
                    position,
                ),
            )
            for file_position, generated in enumerate(run.files):
                connection.execute(
                    """
                    INSERT INTO converted_files (
                        project_id, run_id, position, source_file_id, source_name,
                        python_name, program_name, python, notes, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        project.id,
                        run.id,
                        file_position,
                        generated.source_file_id,
                        generated.source_name,
                        generated.python_name,
                        generated.program_name,
                        generated.python,
                        Json(generated.notes),
                        generated.status.value,
                    ),
                )

    def _trim(self, connection: ProjectConnection) -> None:
        """Delete the oldest projects until at most ``max_projects`` remain."""
        connection.execute(
            """
            DELETE FROM projects
            WHERE id IN (
                SELECT id FROM projects
                ORDER BY created_at, id
                LIMIT GREATEST((SELECT count(*) FROM projects) - %s, 0)
            )
            """,
            (self.max_projects,),
        )
