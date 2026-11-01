"""HTTP server for the runner container: ``python -m legacylift.runner.server``.

JSON in, JSON out. Only the API can reach it (Compose puts it on an internal network).

| Route | Body | Result |
| --- | --- | --- |
| ``GET /health`` | none | ``{"status": "ok"}`` |
| ``POST /run/cobol`` | ``programs``, ``main``, optional ``copybooks``, ``data_files`` | ``RunResult`` fields |
| ``POST /run/python`` | ``scripts``, ``main``, optional ``data_files`` | ``RunResult`` fields |

Each file map is ``{"NAME.cbl": "text"}``. Errors are ``{"detail": message}`` with
400 (bad body), 404, 411 (no length), 413 (too large), or 500.

Settings come from ``RUNNER_HOST``, ``RUNNER_PORT``, ``RUNNER_TIMEOUT_SECONDS``,
``RUNNER_MAX_OUTPUT_BYTES``, and ``RUNNER_MAX_REQUEST_BYTES``.

Example:
    >>> import json, threading, urllib.request
    >>> server = make_server("127.0.0.1", 0)
    >>> _ = threading.Thread(target=server.serve_forever, daemon=True).start()
    >>> url = f"http://127.0.0.1:{server.server_port}"
    >>> json.load(urllib.request.urlopen(url + "/health"))
    {'status': 'ok'}
    >>> server.shutdown()
"""

from __future__ import annotations

import json
import os
import threading
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from legacylift.runner.sandbox import Limits, RunResult, run_cobol, run_python

DEFAULT_PORT = 8001
DEFAULT_MAX_REQUEST_BYTES = 2_000_000
# Programs run at the same time; more requests wait their turn.
RUN_SLOTS = threading.BoundedSemaphore(2)


class BadRequest(Exception):
    """The request body can't be used; sent back as 400."""


def make_server(
    host: str,
    port: int,
    *,
    limits: Limits | None = None,
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
) -> ThreadingHTTPServer:
    """Build the server; call ``serve_forever()`` on it to start.

    Args:
        host: Address to listen on, such as ``"0.0.0.0"``.
        port: Port to listen on; ``0`` picks a free one.
        limits: Limits for every run; ``Limits()`` when ``None``.
        max_request_bytes: Largest request body accepted.

    Returns:
        The server, already bound to the port.
    """
    run_limits = limits or Limits()

    class Handler(RunnerHandler):
        limits = run_limits
        max_body = max_request_bytes

    return ThreadingHTTPServer((host, port), Handler)


class RunnerHandler(BaseHTTPRequestHandler):
    """Routes requests to ``run_cobol`` and ``run_python``."""

    limits = Limits()
    max_body = DEFAULT_MAX_REQUEST_BYTES

    def do_GET(self) -> None:
        """Answer ``/health``."""
        if self.path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok"})
        else:
            self._send(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def do_POST(self) -> None:
        """Run COBOL or Python and send the ``RunResult``."""
        if self.path not in ("/run/cobol", "/run/python"):
            self._send(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return
        length = self.headers.get("Content-Length", "")
        if not length.isdigit():
            self._send(HTTPStatus.LENGTH_REQUIRED, {"detail": "Content-Length is required"})
            return
        if int(length) > self.max_body:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"detail": "Request too large"})
            return
        try:
            body = json.loads(self.rfile.read(int(length)))
            with RUN_SLOTS:
                result = self._run(body)
        except (ValueError, BadRequest) as error:  # bad JSON, RunnerInputError
            self._send(HTTPStatus.BAD_REQUEST, {"detail": str(error)})
        except Exception as error:  # noqa: BLE001 - answer instead of dropping the connection
            traceback.print_exc()
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": f"Runner error: {error}"})
        else:
            self._send(HTTPStatus.OK, result._asdict())

    def _run(self, body: object) -> RunResult:
        """Check the body and run what the path asks for."""
        if not isinstance(body, dict):
            raise BadRequest("The body must be a JSON object.")
        main = body.get("main")
        if not isinstance(main, str):
            raise BadRequest("'main' must be a file name.")
        data_files = _files(body, "data_files", required=False)
        if self.path == "/run/python":
            scripts = _files(body, "scripts")
            return run_python(scripts, main=main, data_files=data_files, limits=self.limits)
        return run_cobol(
            _files(body, "programs"),
            main=main,
            copybooks=_files(body, "copybooks", required=False),
            data_files=data_files,
            limits=self.limits,
        )

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _files(body: dict[str, Any], key: str, *, required: bool = True) -> dict[str, str]:
    """Read a ``{"name": "text"}`` map from the body."""
    value = body.get(key)
    if value is None and not required:
        return {}
    if not isinstance(value, dict) or not value:
        raise BadRequest(f"{key!r} must be a non-empty object of file name to text.")
    if not all(isinstance(name, str) and isinstance(text, str) for name, text in value.items()):
        raise BadRequest(f"{key!r} must map file names to text.")
    return value


def main() -> None:
    """Start the server with settings from ``RUNNER_*`` environment variables."""
    env = os.environ.get
    limits = Limits(
        timeout_seconds=float(env("RUNNER_TIMEOUT_SECONDS", "10")),
        max_output_bytes=int(env("RUNNER_MAX_OUTPUT_BYTES", "256000")),
    )
    server = make_server(
        env("RUNNER_HOST", "0.0.0.0"),  # inside the container only
        int(env("RUNNER_PORT", str(DEFAULT_PORT))),
        limits=limits,
        max_request_bytes=int(env("RUNNER_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES))),
    )
    print(f"LegacyLift runner listening on port {server.server_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
