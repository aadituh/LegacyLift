"""Short-lived copies of ``POST /api/convert`` results.

Batch conversion is not a project and is not written to disk. The copy exists
so Export can download the ``.py`` file from the API. It lasts until the
process restarts, or until older copies are dropped to stay under the limit.
IDs are unguessable, because this API is open to anyone who can reach it.
"""

import secrets
import threading

from legacylift.errors import NotFoundError
from legacylift.models import ConvertedFile

MAX_BATCH_DOWNLOADS = 100


class BatchDownloadStore:
    """Keep recent batch conversions in memory, newest last.

    Example:
        >>> store = BatchDownloadStore(max_entries=1)
        >>> first = store.save([ConvertedFile(
        ...     source_name="a.cbl", python_name="a.py", program_name="A", python="x", notes=[]
        ... )])
        >>> second = store.save([ConvertedFile(
        ...     source_name="b.cbl", python_name="b.py", program_name="B", python="y", notes=[]
        ... )])
        >>> store.python_file(first, "a.py")
        Traceback (most recent call last):
            ...
        legacylift.errors.NotFoundError: Download not found. Convert the files again.
        >>> store.python_file(second, "b.py").python
        'y'
    """

    def __init__(self, max_entries: int = MAX_BATCH_DOWNLOADS) -> None:
        """Create an empty store.

        Args:
            max_entries: How many conversions to keep. The oldest is dropped
                past this limit.
        """
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._files: dict[str, list[ConvertedFile]] = {}
        self._order: list[str] = []

    def save(self, files: list[ConvertedFile]) -> str:
        """Remember one batch conversion.

        Args:
            files: The converted files, in upload order.

        Returns:
            An ID to use in the download URL.
        """
        download_id = secrets.token_urlsafe(16)
        with self._lock:
            self._files[download_id] = files
            self._order.append(download_id)
            while len(self._order) > self._max_entries:
                oldest = self._order.pop(0)
                del self._files[oldest]
        return download_id

    def python_file(self, download_id: str, python_name: str) -> ConvertedFile:
        """Return one generated file from a batch conversion.

        Args:
            download_id: The ID returned by ``save``.
            python_name: The generated file name, such as ``PAY.py``.

        Returns:
            The matching converted file.

        Raises:
            NotFoundError: The ID is unknown, or that conversion has no file
                with this name.
        """
        with self._lock:
            files = self._files.get(download_id)
        if files is None:
            raise NotFoundError("Download not found. Convert the files again.")
        for converted in files:
            if converted.python_name == python_name:
                return converted
        raise NotFoundError("Python file not found.")
