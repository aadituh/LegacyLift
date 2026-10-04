"""File responses for generated Python.

Routes that download a ``.py`` file use ``python_attachment`` so the browser
saves the script instead of showing it as a page.
"""

from fastapi.responses import Response


def python_attachment(python_name: str, python: str) -> Response:
    """Return generated Python as a file download.

    Args:
        python_name: The file name to suggest, such as ``PAY.py``.
        python: The script text.

    Returns:
        A response with ``Content-Disposition: attachment``. A name that is
        not a plain file name is sent as ``converted.py``.

    Example:
        >>> response = python_attachment("hello.py", "print(1)")
        >>> response.headers["content-disposition"]
        'attachment; filename="hello.py"'
        >>> response.body
        b'print(1)'
        >>> python_attachment('bad"name.py', "x").headers["content-disposition"]
        'attachment; filename="converted.py"'
    """
    safe_name = python_name
    if (
        not safe_name.isascii()
        or any(character in safe_name for character in '"\\\r\n/')
        or safe_name in {".", ".."}
    ):
        safe_name = "converted.py"
    return Response(
        content=python,
        media_type="text/x-python; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
