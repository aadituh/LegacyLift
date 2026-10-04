"""``POST /api/convert`` and the download for that result.

Reads the uploads, then runs ``services.conversion.convert_uploads`` in a
worker thread so other requests keep being answered. The Python is not saved
as a project. A copy is kept in memory so ``GET /api/convert/{download_id}/files/{name}``
can send the ``.py`` file.

Route docstrings: the text before ``\\f`` appears on the /docs page; the rest is
for developers only.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from legacylift.dependencies import BatchDownloadDep
from legacylift.responses import python_attachment
from legacylift.schemas import ConvertFilesResponse
from legacylift.services.conversion import convert_uploads
from legacylift.services.uploads import read_uploads

router = APIRouter(tags=["conversion"])


@router.post("/api/convert")
async def convert_files(
    files: Annotated[list[UploadFile], File()],
    downloads: BatchDownloadDep,
) -> ConvertFilesResponse:
    """Convert 1 to 5 .cbl or .cob files without creating a project.

    Send the files as multipart form data in the field `files`. The response
    includes `download_id` for `GET /api/convert/{download_id}/files/{python_name}`.
    That copy lasts until the API restarts.

    \f
    Args:
        files: The uploaded COBOL files.
        downloads: In-memory copies used by the download route.

    Returns:
        One ``ConvertedFile`` per upload, plus a download ID.

    Raises:
        InvalidInputError: Bad file count, type, name, size, or encoding (400).
        ConversionError: A program has no ``PROGRAM-ID`` or ``PROCEDURE DIVISION`` (400).

    Example:
        ``curl -F files=@PAY.cbl http://127.0.0.1:8000/api/convert``
    """
    uploads = await read_uploads(files)
    converted = await run_in_threadpool(convert_uploads, uploads)
    return ConvertFilesResponse(download_id=downloads.save(converted), files=converted)


@router.get("/api/convert/{download_id}/files/{python_name}")
def download_converted_file(
    download_id: str,
    python_name: str,
    downloads: BatchDownloadDep,
) -> Response:
    """Download one Python file from a batch conversion.

    \f
    Args:
        download_id: The ID from ``POST /api/convert``.
        python_name: The generated file name, such as ``PAY.py``.
        downloads: In-memory copies of batch conversions.

    Returns:
        The ``.py`` file as an attachment.

    Raises:
        NotFoundError: The ID is unknown, or that conversion has no such file (404).
    """
    converted = downloads.python_file(download_id, python_name)
    return python_attachment(converted.python_name, converted.python)
