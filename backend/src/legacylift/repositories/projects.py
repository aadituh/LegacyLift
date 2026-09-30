"""Replace this repository with database access when persistence is added."""

from uuid import uuid4

from legacylift.models.project import Project


class ProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def create(self, name: str) -> Project:
        project = Project(id=str(uuid4()), name=name)
        self._projects[project.id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)
