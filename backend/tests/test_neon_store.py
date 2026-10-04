"""Neon rows match the project models, and the schema file is the one the API runs."""

from datetime import UTC, datetime
from pathlib import Path

from legacylift.models import (
    ConvertedProjectFile,
    FileKind,
    Project,
    Run,
    RunKind,
    RunStatus,
    SourceFile,
)
from legacylift.neon_store import SCHEMA_PATH, project_from_parts

REPO_SCHEMA = Path(__file__).parents[2] / "database" / "schema.sql"


def test_rows_round_trip_to_the_project_model():
    created = datetime(2026, 10, 3, tzinfo=UTC)
    project = Project(
        id="1",
        name="Payroll",
        created_at=created,
        files_added=1,
        files=[SourceFile(id="1", name="PAY.cbl", kind=FileKind.PROGRAM, content="STOP RUN.")],
        runs=[
            Run(
                id="1",
                kind=RunKind.CONVERT,
                status=RunStatus.REVIEW_REQUIRED,
                created_at=created,
                files=[
                    ConvertedProjectFile(
                        source_file_id="1",
                        source_name="PAY.cbl",
                        python_name="PAY.py",
                        program_name="PAY",
                        python="print(1)\n",
                        notes=["Line 9: STOP RUN"],
                        status=RunStatus.REVIEW_REQUIRED,
                    )
                ],
            )
        ],
    )
    restored = project_from_parts(
        {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at,
            "files_added": project.files_added,
        },
        [{"id": "1", "name": "PAY.cbl", "kind": "program", "content": "STOP RUN."}],
        [{"id": "1", "kind": "convert", "status": "review_required", "created_at": created}],
        [
            {
                "run_id": "1",
                "source_file_id": "1",
                "source_name": "PAY.cbl",
                "python_name": "PAY.py",
                "program_name": "PAY",
                "python": "print(1)\n",
                "notes": ["Line 9: STOP RUN"],
                "status": "review_required",
            }
        ],
    )
    assert restored == project


def test_api_reads_the_database_folder_schema():
    assert REPO_SCHEMA.resolve() == SCHEMA_PATH
