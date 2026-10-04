"""Convert COBOL files into Python drafts and give each output file its name.

The translation itself is in ``cobol/converter.py``; this module adds file
names, upload checks, and logging around it. ``convert_uploads`` backs
``POST /api/convert``; ``convert_file`` is also used by ``ProjectService.convert``.
"""

import logging
from pathlib import PurePosixPath

from legacylift.cobol.converter import translate_program
from legacylift.errors import ConversionError, InvalidInputError
from legacylift.models import ConvertedFile, RunStatus
from legacylift.services.uploads import PROGRAM_SUFFIXES, RawUpload, decode_upload

MAX_BATCH_FILES = 5
# Uvicorn already prints this logger, so messages appear in the server console.
# Log file names and counts only, never source code.
logger = logging.getLogger("uvicorn.error")


def conversion_status(notes: list[str]) -> RunStatus:
    """Pick the status for converted code.

    Args:
        notes: Review notes; one per line that was not converted.

    Returns:
        ``REVIEW_REQUIRED`` if there are notes, otherwise ``DRAFT``.

    Example:
        >>> conversion_status(["Line 6: PERFORM PRINT-TOTAL"])
        <RunStatus.REVIEW_REQUIRED: 'review_required'>
    """
    return RunStatus.REVIEW_REQUIRED if notes else RunStatus.DRAFT


def python_file_name(source_name: str) -> str:
    """Name the Python file generated from a COBOL file.

    Args:
        source_name: A COBOL file name such as ``PAY.cbl``.

    Returns:
        The same name with a ``.py`` extension.

    Example:
        >>> python_file_name("PAY.cbl")
        'PAY.py'
    """
    return f"{PurePosixPath(source_name).stem}.py"


def convert_file(file_name: str, source: str) -> ConvertedFile:
    """Translate one COBOL program and name its output file.

    Args:
        file_name: The COBOL file name, used for the output name and in errors.
        source: The program's text.

    Returns:
        The converter's draft plus ``source_name`` and ``python_name``.

    Raises:
        ConversionError: If the program cannot be converted. The message
            starts with the file name.

    Example:
        >>> source = '''PROGRAM-ID. HELLO.
        ... PROCEDURE DIVISION.
        ... DISPLAY "Hi".
        ... STOP RUN.'''
        >>> converted = convert_file("hello.cbl", source)
        >>> converted.python_name, converted.program_name, converted.notes
        ('hello.py', 'HELLO', [])
        >>> convert_file("bad.cbl", "DISPLAY 1.")
        Traceback (most recent call last):
            ...
        legacylift.errors.ConversionError: bad.cbl: File needs PROGRAM-ID and PROCEDURE DIVISION.
    """
    try:
        draft = translate_program(source)
    except ConversionError as error:
        raise ConversionError(f"{file_name}: {error}") from error
    return ConvertedFile(
        source_name=file_name, python_name=python_file_name(file_name), **draft.model_dump()
    )


def convert_uploads(uploads: list[RawUpload]) -> list[ConvertedFile]:
    r"""Convert up to five uploaded programs without saving anything.

    This backs ``POST /api/convert``. Files are checked in order, and the first
    problem stops the whole batch.

    Args:
        uploads: The uploaded ``.cbl`` or ``.cob`` files.

    Returns:
        One ``ConvertedFile`` per upload, in the same order.

    Raises:
        InvalidInputError: If there are not 1 to 5 files, a file is not
            ``.cbl``/``.cob``, two files would produce the same ``.py`` name, or a
            file fails ``decode_upload``.
        ConversionError: If a program cannot be converted.

    Example:
        >>> source = b'PROGRAM-ID. HELLO.\nPROCEDURE DIVISION.\nSTOP RUN.'
        >>> uploads = [RawUpload(name="a.cbl", data=source), RawUpload(name="b.cob", data=source)]
        >>> [converted.python_name for converted in convert_uploads(uploads)]
        ['a.py', 'b.py']
    """
    if not 1 <= len(uploads) <= MAX_BATCH_FILES:
        raise InvalidInputError(f"Choose 1 to {MAX_BATCH_FILES} COBOL files.")
    logger.info("Received %d COBOL file(s)", len(uploads))

    converted_files = []
    taken_python_names: set[str] = set()  # lowercase, so PAY.cbl and pay.cob clash
    for upload in uploads:
        if upload.suffix not in PROGRAM_SUFFIXES:
            raise InvalidInputError(f"{upload.name or 'File'} must be .cbl or .cob.")
        python_name = python_file_name(upload.name).casefold()
        if python_name in taken_python_names:
            raise InvalidInputError("COBOL file names must be unique.")
        taken_python_names.add(python_name)

        converted = convert_file(upload.name, decode_upload(upload))
        logger.info("Converted %s with %d review notes", upload.name, len(converted.notes))
        converted_files.append(converted)
    return converted_files
