"""Project storage: kept in memory and saved as one JSON file per project.

This stands in for PostgreSQL until the API has a host with a database. Files
on Render's disk last until the service restarts or redeploys.
"""

import logging
from pathlib import Path

from pydantic import ValidationError

from legacylift.models import Project

# Uvicorn already prints this logger, so messages appear in the server console.
logger = logging.getLogger("uvicorn.error")


class ProjectStore:
    """Holds projects in memory and writes each one to ``data_dir/<id>.json``.

    Projects are loaded from ``data_dir`` at startup, so they and their saved
    translations survive a restart. Only the newest ``max_projects`` are kept.
    Not thread-safe on its own: ``ProjectService`` makes one change at a time.

    Example:
        >>> store = ProjectStore(data_dir=None, max_projects=2)
        >>> first, second, third = Project(name="A"), Project(name="B"), Project(name="C")
        >>> for project in (first, second, third):
        ...     store.add(project)
        >>> store.get(first.id) is None, store.get(third.id) is third
        (True, True)
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
        self._remove_oldest()

    def get(self, project_id: str) -> Project | None:
        """Find a project by ID.

        Args:
            project_id: The project's ID.

        Returns:
            The project, or ``None`` if there is none with that ID.
        """
        return self._projects.get(project_id)

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

        Args:
            project: The changed project.
        """
        if self.data_dir is None:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.data_dir / f"{project.id}.tmp"
        temp_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(self.data_dir / f"{project.id}.json")  # atomic swap

    def _remove_oldest(self) -> None:
        """Delete the oldest projects, and their files, until at most ``max_projects`` remain."""
        while len(self._projects) > self.max_projects:
            oldest_id = next(iter(self._projects))
            del self._projects[oldest_id]
            if self.data_dir is not None:
                (self.data_dir / f"{oldest_id}.json").unlink(missing_ok=True)

    def _read_saved_projects(self) -> list[Project]:
        """Read every ``<id>.json`` in ``data_dir``, skipping files that cannot be parsed."""
        if self.data_dir is None or not self.data_dir.is_dir():
            return []
        projects = []
        for path in self.data_dir.glob("*.json"):
            try:
                projects.append(Project.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValidationError) as error:
                logger.warning("Skipped unreadable project file %s: %s", path.name, error)
        return projects
