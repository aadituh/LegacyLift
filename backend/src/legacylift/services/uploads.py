"""Read uploaded files and check them. Shared by every route that accepts uploads."""

from pathlib import PurePosixPath

from fastapi import UploadFile
from pydantic import BaseModel

from legacylift.errors import InvalidInputError

MAX_FILE_BYTES = 100_000


class RawUpload(BaseModel):
    """One uploaded file, read into memory but not yet checked.

    Attributes:
        name: File name without any folder path, such as ``PAY.cbl``.
        data: The file's bytes, at most ``MAX_FILE_BYTES + 1`` long.
    """

    name: str
    data: bytes

    @property
    def suffix(self) -> str:
        """The lowercase extension, used to decide the file kind.

        Example:
            >>> RawUpload(name="PAY.CBL", data=b"").suffix
            '.cbl'
        """
        return PurePosixPath(self.name).suffix.lower()


async def read_uploads(files: list[UploadFile]) -> list[RawUpload]:
    r"""Read multipart uploads into ``RawUpload`` objects.

    Reads one byte past the limit, so ``decode_upload`` can reject large files
    without reading all of them.

    Args:
        files: The uploads FastAPI received in the multipart field ``files``.

    Returns:
        One ``RawUpload`` per file, in the same order. Folder paths that a
        client sent with the name, Windows or Unix style, are removed.

    Example:
        >>> import asyncio, io
        >>> upload = UploadFile(io.BytesIO(b"DISPLAY 1."), filename="C:\\code\\PAY.cbl")
        >>> asyncio.run(read_uploads([upload]))
        [RawUpload(name='PAY.cbl', data=b'DISPLAY 1.')]
    """
    return [
        RawUpload(
            name=PurePosixPath((file.filename or "").replace("\\", "/")).name,
            data=await file.read(MAX_FILE_BYTES + 1),
        )
        for file in files
    ]


def decode_upload(upload: RawUpload) -> str:
    r"""Check an upload and return its text.

    Args:
        upload: The file to check.

    Returns:
        The file decoded as UTF-8, without a byte-order mark if it had one.

    Raises:
        InvalidInputError: If the file is over 100 KB, is not UTF-8, is empty
            or only whitespace, or contains a null byte (a sign of binary data).

    Example:
        >>> decode_upload(RawUpload(name="a.cbl", data=b"DISPLAY 'HI'."))
        "DISPLAY 'HI'."
        >>> decode_upload(RawUpload(name="a.cbl", data=b"\xff"))
        Traceback (most recent call last):
            ...
        legacylift.errors.InvalidInputError: a.cbl must be UTF-8 text.
    """
    if len(upload.data) > MAX_FILE_BYTES:
        raise InvalidInputError(f"{upload.name} is larger than 100 KB.")
    try:
        text = upload.data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidInputError(f"{upload.name} must be UTF-8 text.") from error
    if not text.strip() or "\x00" in text:
        raise InvalidInputError(f"{upload.name} is empty or binary.")
    return text
