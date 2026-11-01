"""Project storage: kept in memory and saved as one JSON file per project.

``ProjectService`` is the only caller. It asks the store for a new project ID,
adds the project, and calls ``save`` after every change. When ``DATABASE_URL``
is unset, ``ProjectStore`` writes JSON files. ``NeonProjectStore`` writes the
same projects to Postgres instead.
"""

import json
import logging
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from legacylift.errors import ConflictError
from legacylift.models import Project, User


class ProjectRepository(Protocol):
    """The methods ``ProjectService`` uses to keep projects."""

    def next_id(self) -> str:
        """Hand out the next project ID."""

    def get(self, project_id: str) -> Project | None:
        """Find a project by ID."""

    def all(self) -> list[Project]:
        """Return every stored project, oldest first."""

    def delete(self, project_id: str) -> None:
        """Remove a project."""

    def add(self, project: Project) -> None:
        """Store a new project."""

    def save(self, project: Project) -> None:
        """Write a changed project."""

    def add_user(self, user: User) -> None:
        """Save an account."""

    def get_user(self, user_id: str) -> User | None:
        """Find an account by ID."""

    def get_user_by_email(self, email: str) -> User | None:
        """Find an account by lowercase email."""


# Uvicorn already prints this logger, so messages appear in the server console.
logger = logging.getLogger("uvicorn.error")
LAST_ID_FILE = "last_id.txt"
USERS_FILE = "users.json"


class ProjectStore:
    """Holds projects in memory and writes each one to ``data_dir/<id>.json``.

    Projects are loaded from ``data_dir`` at startup, so they and their saved
    translations survive a restart. Only the newest ``max_projects`` are kept.
    Not thread-safe on its own: ``ProjectService`` makes one change at a time.

    Example:
        >>> store = ProjectStore(data_dir=None, max_projects=2)
        >>> for name in ("A", "B", "C"):
        ...     store.add(Project(id=store.next_id(), name=name))
        >>> [(project.id, project.name) for project in store.all()]
        [('2', 'B'), ('3', 'C')]
        >>> store.delete("2")
        >>> store.get("2") is None, store.next_id()
        (True, '4')
    """

    def __init__(self, data_dir: Path | None, max_projects: int) -> None:
        """Load any saved projects.

        Args:
            data_dir: Folder for the JSON files, created on first save. ``None``
                keeps everything in memory.
            max_projects: How many projects to keep.
        """
        self.data_dir = data_dir
        self.max_projects = max_projects
        self._projects: dict[str, Project] = {}  # oldest first
        for project in sorted(self._read_saved_projects(), key=lambda p: p.created_at):
            self._projects[project.id] = project
        numbers = [int(project_id) for project_id in self._projects if project_id.isdigit()]
        self._last_number = max([*numbers, self._read_last_number()], default=0)
        self._users = self._read_users()
        self._remove_oldest()

    def next_id(self) -> str:
        """Hand out the next project ID: one more than the highest ever given.

        The number is saved in ``data_dir/last_id.txt``, so an ID is never
        reused, even after the newest project is deleted and the app restarts.

        Returns:
            ``"1"`` for the first project, then ``"2"``, ``"3"``, ...
        """
        self._last_number += 1
        if self.data_dir is not None:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            (self.data_dir / LAST_ID_FILE).write_text(str(self._last_number), encoding="utf-8")
        return str(self._last_number)

    def get(self, project_id: str) -> Project | None:
        """Find a project by ID.

        Args:
            project_id: The project's ID.

        Returns:
            The project, or ``None`` if there is none with that ID.
        """
        return self._projects.get(project_id)

    def all(self) -> list[Project]:
        """Return every stored project, oldest first.

        Returns:
            The projects in the order they were added.
        """
        return list(self._projects.values())

    def delete(self, project_id: str) -> None:
        """Remove a project and its file. Does nothing if there is no such project.

        Args:
            project_id: The project's ID.
        """
        self._projects.pop(project_id, None)
        if self.data_dir is not None:
            (self.data_dir / f"{project_id}.json").unlink(missing_ok=True)

    def add(self, project: Project) -> None:
        """Store and save a new project, deleting the oldest if over the limit.

        Args:
            project: The new project.
        """
        self._projects[project.id] = project
        self.save(project)
        self._remove_oldest()

    def save(self, project: Project) -> None:
        """Write a project to its JSON file. Call after every change to it.

        Writes to a temporary file first, so a crash never leaves half a file.
        A project that was deleted, or dropped past the limit, is not written.

        Args:
            project: The changed project.
        """
        if self.data_dir is None or project.id not in self._projects:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.data_dir / f"{project.id}.tmp"
        temp_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(self.data_dir / f"{project.id}.json")  # atomic swap

    def add_user(self, user: User) -> None:
        """Save an account. The same email cannot be saved twice.

        Args:
            user: The account, including its password hash.

        Raises:
            ConflictError: An account with this email already exists.
        """
        if self.get_user_by_email(user.email) is not None:
            raise ConflictError("An account with this email already exists.")
        self._users[user.id] = user
        self._write_users()

    def get_user(self, user_id: str) -> User | None:
        """Find an account by ID.

        Args:
            user_id: The account's ID.

        Returns:
            The account, or ``None``.
        """
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        """Find an account by lowercase email.

        Args:
            email: Already lowercase.

        Returns:
            The account, or ``None``.
        """
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def _users_path(self) -> Path | None:
        """Path of the accounts file, or ``None`` when storage is memory only."""
        if self.data_dir is None:
            return None
        return self.data_dir / USERS_FILE

    def _read_users(self) -> dict[str, User]:
        """Load accounts from ``users.json``.

        Returns:
            Accounts keyed by ID. Unreadable files yield an empty dict.
        """
        path = self._users_path()
        if path is None or not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Skipped unreadable accounts file %s: %s", path.name, error)
            return {}
        if not isinstance(raw, list):
            return {}
        users: dict[str, User] = {}
        for item in raw:
            try:
                user = User.model_validate(item)
            except ValidationError as error:
                logger.warning("Skipped unreadable account: %s", error)
                continue
            users[user.id] = user
        return users

    def _write_users(self) -> None:
        """Write every account to ``users.json``. Memory-only stores skip this."""
        path = self._users_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [user.model_dump(mode="json") for user in self._users.values()]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _remove_oldest(self) -> None:
        """Delete the oldest projects, and their files, until at most ``max_projects`` remain."""
        while len(self._projects) > self.max_projects:
            self.delete(next(iter(self._projects)))

    def _read_last_number(self) -> int:
        """Read the highest ID ever given from ``last_id.txt``.

        Returns:
            The saved number, or 0 if there is no readable file.
        """
        path = self.data_dir / LAST_ID_FILE if self.data_dir is not None else None
        if path is None or not path.is_file():
            return 0
        text = path.read_text(encoding="utf-8").strip()
        return int(text) if text.isdigit() else 0

    def _read_saved_projects(self) -> list[Project]:
        """Read every ``<id>.json`` in ``data_dir``, skipping files that cannot be parsed.

        Returns:
            The projects that could be read, in no particular order.
        """
        if self.data_dir is None or not self.data_dir.is_dir():
            return []
        projects = []
        for path in self.data_dir.glob("*.json"):
            if path.name == USERS_FILE:
                continue
            try:
                projects.append(Project.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValidationError) as error:
                logger.warning("Skipped unreadable project file %s: %s", path.name, error)
        return projects
