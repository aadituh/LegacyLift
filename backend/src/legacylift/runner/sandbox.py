r"""Run COBOL (GnuCOBOL) or Python in a temporary folder with time and output limits.

Each call makes a temporary folder with ``src/`` (programs, copybooks), ``bin/``
(the compiled program), and ``run/`` (the working folder: data files, scripts),
runs one process at a time there (list arguments, no shell), and deletes it. COBOL
opens data files by name relative to the working folder. A process is stopped
when it runs past its time limit or prints more than ``Limits.max_output_bytes``.

Example:
    >>> result = run_python({"hello.py": "print('hi')"}, main="hello.py")
    >>> result.ok, result.stdout, result.stage
    (True, 'hi\n', 'run')
"""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO, NamedTuple

# A plain file name: no folders, no leading dot.
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}")
CHUNK_BYTES = 65_536


class RunnerInputError(ValueError):
    """The request names a bad file or a main file that isn't in it."""


@dataclass(frozen=True)
class Limits:
    """Limits for one run.

    Attributes:
        timeout_seconds: Wall-clock limit for running the program.
        compile_timeout_seconds: Wall-clock limit for ``cobc``.
        max_output_bytes: Most bytes kept from stdout, and from stderr; past
            this the program is stopped.
    """

    timeout_seconds: float = 10.0
    compile_timeout_seconds: float = 60.0
    max_output_bytes: int = 256_000


class RunResult(NamedTuple):
    r"""What one compile-and-run, or one Python run, produced.

    Attributes:
        ok: ``True`` when it compiled (COBOL) and exited with code 0 within the limits.
        stage: ``"compile"`` if it stopped while compiling, else ``"run"``.
        exit_code: The process exit code; ``None`` if it was stopped or never started.
        stdout: Standard output, ``\r\n`` turned into ``\n``.
        stderr: Standard error (compiler messages when ``stage`` is ``"compile"``).
        timed_out: Stopped by the time limit.
        output_truncated: Stopped by the output limit.
    """

    ok: bool
    stage: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    output_truncated: bool = False


def check_name(name: str) -> str:
    """Return ``name`` if it is a plain file name.

    Args:
        name: A file name from the request.

    Returns:
        The same name.

    Raises:
        RunnerInputError: If it has a folder, starts with a dot, or uses other characters.

    Example:
        >>> check_name("BANKMAIN.cbl")
        'BANKMAIN.cbl'
        >>> check_name("../etc/passwd")
        Traceback (most recent call last):
            ...
        legacylift.runner.sandbox.RunnerInputError: Bad file name: '../etc/passwd'
    """
    if not SAFE_NAME.fullmatch(name):
        raise RunnerInputError(f"Bad file name: {name!r}")
    return name


def run_cobol(
    programs: Mapping[str, str],
    *,
    main: str,
    copybooks: Mapping[str, str] | None = None,
    data_files: Mapping[str, str] | None = None,
    limits: Limits | None = None,
    cobc: str = "cobc",
) -> RunResult:
    """Compile COBOL programs into one executable with ``cobc -x`` and run it.

    ``main`` is compiled first, so it is the entry point; the other programs are
    linked in for its ``CALL`` statements. Copybooks are found with ``-I``.

    Args:
        programs: File name → source for the main program and the programs it calls.
        main: The name in ``programs`` to run.
        copybooks: File name → text for ``COPY``.
        data_files: File name → text, placed in the working folder.
        limits: Time and output limits; ``Limits()`` when ``None``.
        cobc: The GnuCOBOL compiler to call.

    Returns:
        The result. A compile error has ``stage="compile"`` and the messages in ``stderr``.

    Raises:
        RunnerInputError: A bad file name, or ``main`` is not in ``programs``.
    """
    if main not in programs:
        raise RunnerInputError(f"The main program {main!r} is not in the request.")
    limits = limits or Limits()
    with tempfile.TemporaryDirectory(prefix="legacylift-run-") as tmp:
        src, run_dir = _make_folders(Path(tmp), {**(copybooks or {}), **programs}, data_files)
        binary = Path(tmp) / "bin" / ("program.exe" if sys.platform == "win32" else "program")
        sources = [main, *(name for name in programs if name != main)]
        command = [cobc, "-x", "-o", str(binary), "-I", str(src), *(str(src / s) for s in sources)]
        compiled = _execute(command, run_dir, limits.compile_timeout_seconds, limits, "compile")
        if not compiled.ok or not binary.is_file():
            # Show "PROG.cbl:4: error" instead of the temporary folder's path.
            stderr = compiled.stderr.replace(f"{src}{os.sep}", "")
            return compiled._replace(ok=False, stderr=stderr)
        return _execute([str(binary)], run_dir, limits.timeout_seconds, limits, "run")


def run_python(
    scripts: Mapping[str, str],
    *,
    main: str,
    data_files: Mapping[str, str] | None = None,
    limits: Limits | None = None,
    python: str = sys.executable,
) -> RunResult:
    """Run a Python script in isolated mode (``python -I``).

    Args:
        scripts: File name → source; ``main`` is the one started.
        main: The name in ``scripts`` to run.
        data_files: File name → text, placed in the working folder.
        limits: Time and output limits; ``Limits()`` when ``None``.
        python: The Python interpreter to call.

    Returns:
        The result; ``stage`` is always ``"run"``.

    Raises:
        RunnerInputError: A bad file name, or ``main`` is not in ``scripts``.
    """
    if main not in scripts:
        raise RunnerInputError(f"The main script {main!r} is not in the request.")
    limits = limits or Limits()
    with tempfile.TemporaryDirectory(prefix="legacylift-run-") as tmp:
        _, run_dir = _make_folders(Path(tmp), {}, {**scripts, **(data_files or {})})
        command = [python, "-I", "-X", "utf8", main]
        return _execute(command, run_dir, limits.timeout_seconds, limits, "run")


def _make_folders(
    root: Path, sources: Mapping[str, str], run_files: Mapping[str, str] | None
) -> tuple[Path, Path]:
    r"""Create ``src/``, ``bin/``, and ``run/`` under ``root`` and write the files (``\n`` endings).

    Returns:
        The ``src`` and ``run`` folders.
    """
    folders = [root / "src", root / "bin", root / "run"]
    for folder in folders:
        folder.mkdir()
    for folder, files in ((folders[0], sources), (folders[2], run_files or {})):
        for name, text in files.items():
            path = folder / check_name(name)
            path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    return folders[0], folders[2]


def _child_env(run_dir: Path) -> dict[str, str]:
    """A small environment: no API settings or secrets reach the program."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(run_dir), "LANG": "C.UTF-8"}
    for name in ("SYSTEMROOT", "TMPDIR", "TEMP", "TMP"):  # Windows needs SYSTEMROOT
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _execute(
    command: list[str], run_dir: Path, timeout: float, limits: Limits, stage: str
) -> RunResult:
    """Run ``command`` in ``run_dir``; stop it at the time or output limit."""
    try:
        process = subprocess.Popen(
            command,
            cwd=run_dir,
            env=_child_env(run_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=sys.platform != "win32",  # own process group for _kill
        )
    except OSError as error:
        return RunResult(False, stage, None, "", f"Could not start {command[0]}: {error}")
    assert process.stdout is not None and process.stderr is not None
    overflow = threading.Event()
    outputs: tuple[list[bytes], list[bytes]] = ([], [])
    readers = [
        threading.Thread(
            target=_read_capped,
            args=(stream, sink, limits.max_output_bytes, overflow, process),
            daemon=True,
        )
        for stream, sink in zip((process.stdout, process.stderr), outputs, strict=True)
    ]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    _kill(process)  # also ends anything the program left running
    exit_code = process.wait()
    for reader in readers:
        reader.join(timeout=5)
    stopped = timed_out or overflow.is_set()
    stdout, stderr = (_decode(chunks) for chunks in outputs)
    return RunResult(
        ok=exit_code == 0 and not stopped,
        stage=stage,
        exit_code=None if stopped else exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        output_truncated=overflow.is_set(),
    )


def _read_capped(
    stream: IO[bytes],
    sink: list[bytes],
    max_bytes: int,
    overflow: threading.Event,
    process: subprocess.Popen[bytes],
) -> None:
    """Copy ``stream`` into ``sink`` up to ``max_bytes``; past that, stop the process."""
    kept = 0
    while chunk := os.read(stream.fileno(), CHUNK_BYTES):
        room = max_bytes - kept
        sink.append(chunk[:room])
        kept += min(len(chunk), room)
        if len(chunk) > room:
            overflow.set()
            _kill(process)
            break
    stream.close()


def _kill(process: subprocess.Popen[bytes]) -> None:
    """Stop the process and, outside Windows, its whole process group."""
    if sys.platform != "win32":
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)
    elif process.poll() is None:
        process.kill()


def _decode(chunks: list[bytes]) -> str:
    r"""Join output chunks as text, with ``\n`` line endings."""
    return b"".join(chunks).decode("utf-8", errors="replace").replace("\r\n", "\n")
