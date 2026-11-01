"""Errors that the API returns as ``{"detail": message}`` with a 4xx status.

Services raise these instead of FastAPI's ``HTTPException``, so they don't
depend on the web framework. ``main.py`` registers one handler that turns any
of them into a response with the class's ``status_code``.

Example:
    >>> error = NotFoundError("Project not found.")
    >>> error.status_code, str(error)
    (404, 'Project not found.')
"""


class LegacyLiftError(Exception):
    """Base class for every error the API reports to the client.

    Attributes:
        status_code: HTTP status the handler sends. Subclasses override it.
    """

    status_code = 400


class InvalidInputError(LegacyLiftError):
    """A project name, file, or file list failed validation (400)."""


class ProjectStateError(LegacyLiftError):
    """The project is not ready for the requested step (400).

    For example, converting a project that has no programs.
    """


class ConversionError(LegacyLiftError):
    """A COBOL program cannot be converted (400)."""


class NotFoundError(LegacyLiftError):
    """The requested project does not exist (404)."""

    status_code = 404


class UnauthenticatedError(LegacyLiftError):
    """The login token is missing, wrong, or expired (401)."""

    status_code = 401


class ConflictError(LegacyLiftError):
    """The email is already registered (409)."""

    status_code = 409


class InputError(LegacyLiftError):
    """A sign-up field failed validation (422)."""

    status_code = 422
