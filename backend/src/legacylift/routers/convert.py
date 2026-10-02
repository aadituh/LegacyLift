"""Stateless conversion route used by the React demo's file picker.

Route docstrings: the text before ``\\f`` appears on the /docs page; the rest is
for developers only.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from legacylift.schemas import ConvertFilesResponse
from legacylift.services.conversion import convert_uploads
from legacylift.services.uploads import read_uploads

router = APIRouter(tags=["conversion"])


@router.post("/api/convert")
async def convert_files(files: Annotated[list[UploadFile], File()]) -> ConvertFilesResponse:
    """Convert 1 to 5 .cbl or .cob files without creating a project.

    Send the files as multipart form data in the field `files`.

    \f
    Args:
        files: The uploaded COBOL files.

    Returns:
        One ``ConvertedFile`` per upload.

    Raises:
        InvalidInputError: Bad file count, type, name, size, or encoding (400).
        ConversionError: A program has no ``PROGRAM-ID`` or ``PROCEDURE DIVISION`` (400).

    Example:
        ``curl -F files=@PAY.cbl http://127.0.0.1:8000/api/convert``
    """
    return ConvertFilesResponse(files=convert_uploads(await read_uploads(files)))
