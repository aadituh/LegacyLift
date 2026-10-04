"""Settings, read from ``LEGACYLIFT_*`` environment variables or a ``.env`` file.

``main.create_app`` reads them once at startup. Real environment variables
override ``backend/.env``.

Example:
    >>> settings = Settings(_env_file=None, cors_origins="https://a.example, ,https://b.example")
    >>> settings.cors_origins
    ['https://a.example', 'https://b.example']
    >>> settings.all_cors_origins[-1]
    'https://b.example'
"""

from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Local Vite and the GitHub Pages frontend can always call the API.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://aadituh.github.io",
]


class Settings(BaseSettings):
    """Backend settings. Each field reads the variable ``LEGACYLIFT_<FIELD NAME>``.

    Attributes:
        cors_origins: Extra browser origins allowed to call the API, comma-separated.
        data_dir: Folder where each project is saved as ``<id>.json`` when
            ``database_url`` is unset. ``None`` keeps projects in memory only.
        database_url: Neon connection string. When set, projects are stored in
            Postgres instead of ``data_dir``.
        max_projects: How many projects to keep; the oldest is deleted first.
        max_request_bytes: Largest request body accepted; bigger ones get 413.
    """

    model_config = SettingsConfigDict(env_prefix="LEGACYLIFT_", env_file=".env", extra="ignore")

    cors_origins: Annotated[list[str], NoDecode] = []
    data_dir: Path | None = Path("data/projects")  # relative to where uvicorn starts
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("database_url", "DATABASE_URL", "LEGACYLIFT_DATABASE_URL"),
    )
    max_projects: int = 100
    max_request_bytes: int = 1_200_000  # 10 files x 100 KB, plus form overhead

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        """Accept ``"https://a.example,https://b.example"`` as well as a list.

        Args:
            value: The raw setting.

        Returns:
            A list of origins without blanks, or ``value`` unchanged if it isn't text.
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def all_cors_origins(self) -> list[str]:
        """Every origin the API allows.

        Returns:
            ``DEFAULT_CORS_ORIGINS`` followed by ``cors_origins``.
        """
        return [*DEFAULT_CORS_ORIGINS, *self.cors_origins]
