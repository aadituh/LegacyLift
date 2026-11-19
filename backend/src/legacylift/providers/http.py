"""Small urllib helper shared by Groq, OpenRouter, and the model catalog.

Tests replace :func:`urlopen_transport`. Nothing here reads environment variables.
"""

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

# Cloudflare rejects urllib's default agent with HTTP 403 error 1010.
USER_AGENT = "LegacyLift/0.2"


@dataclass(frozen=True)
class HttpResult:
    """A completed HTTP response.

    Attributes:
        status: HTTP status code.
        body: Decoded response body.
        headers: Header names lower-cased.
    """

    status: int
    body: str
    headers: dict[str, str]


class HttpFailure(Exception):
    """The transport could not return a successful body.

    Attributes:
        kind: ``timeout``, ``server``, ``http``, or ``rate_limit``.
        status: HTTP status when the server answered.
        headers: Lower-cased response headers.
        body: Response body, possibly empty.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status: int | None = None,
        headers: dict[str, str] | None = None,
        body: str = "",
    ) -> None:
        """Store the failure without including request headers.

        Args:
            message: Short description. Must not include an API key.
            kind: ``timeout``, ``server``, ``http``, or ``rate_limit``.
            status: HTTP status when the server answered.
            headers: Lower-cased response headers.
            body: Response body, possibly empty.
        """
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.headers = headers or {}
        self.body = body


Transport = Callable[[urllib.request.Request, float], HttpResult]


def header_map(headers: object) -> dict[str, str]:
    """Copy headers with lower-cased names.

    Args:
        headers: A header mapping, an ``email.message.Message``, or ``None``.

    Returns:
        A new dict. Values are stripped. An object without ``items`` yields ``{}``.
    """
    items = getattr(headers, "items", None)
    if not callable(items):
        return {}
    copied: dict[str, str] = {}
    for key, value in items():
        copied[str(key).lower()] = str(value).strip()
    return copied


def urlopen_transport(request: urllib.request.Request, timeout: float) -> HttpResult:
    """Perform one HTTP request with urllib.

    Args:
        request: The request to send. The caller sets the URL and headers.
        timeout: Seconds to wait.

    Returns:
        The status, body, and lower-cased headers.

    Raises:
        HttpFailure: The connection failed, timed out, or the status was not 2xx.
    """
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
            status = getattr(response, "status", 200)
            return HttpResult(status=int(status), body=raw, headers=header_map(response.headers))
    except TimeoutError as error:
        raise HttpFailure("The request timed out.", kind="timeout") from error
    except urllib.error.HTTPError as error:
        headers = header_map(error.headers)
        try:
            body = error.read().decode(errors="replace")
        except OSError:
            body = ""
        if error.code == 429:
            kind = "rate_limit"
        elif error.code >= 500:
            kind = "server"
        else:
            kind = "http"
        raise HttpFailure(
            _http_failure_message(error.code, body),
            kind=kind,
            status=error.code,
            headers=headers,
            body=body,
        ) from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise HttpFailure("The request timed out.", kind="timeout") from error
        raise HttpFailure("The provider could not be reached.", kind="timeout") from error


def _http_failure_message(status: int, body: str) -> str:
    """Return a short provider error that does not include a request key."""
    message = ""
    try:
        payload = cast(object, json.loads(body))
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("error")
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            message = detail["message"]
        elif isinstance(detail, str):
            message = detail
    message = " ".join(message.split())
    if len(message) > 180:
        message = f"{message[:180]}..."
    if message:
        return f"The provider returned HTTP {status}: {message}"
    return f"The provider returned HTTP {status}."


def loads_object(raw: str) -> object:
    """Parse a JSON body.

    Args:
        raw: Response text.

    Returns:
        The decoded JSON value.

    Raises:
        json.JSONDecodeError: The body is not JSON.
    """
    return cast(object, json.loads(raw))
