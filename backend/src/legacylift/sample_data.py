"""Built-in files for the demo project created by ``POST /api/projects/demo``.

``DEMO_FILES`` holds ``(name, kind, content)`` tuples; the project service
turns each into a ``SourceFile``. They are the sample bank in ``data/``: five
programs, three copybooks, and two data files, the most one project holds.
``docs/walkthrough.md`` follows these files step by step.

Example:
    >>> DEMO_NAME, len(DEMO_FILES), DEMO_FILES[0][:2]
    ('October close', 10, ('BANKMAIN.cbl', <FileKind.PROGRAM: 'program'>))
"""

from pathlib import Path

from legacylift.models import FileKind

_DATA = Path(__file__).parent / "data"

DEMO_NAME = "October close"
DEMO_FILES = tuple(
    (name, kind, (_DATA / name).read_text(encoding="utf-8"))
    for name, kind in (
        ("BANKMAIN.cbl", FileKind.PROGRAM),
        ("TXNPOST.cbl", FileKind.PROGRAM),
        ("INTCALC.cbl", FileKind.PROGRAM),
        ("FEESCHED.cbl", FileKind.PROGRAM),
        ("MONTHEND.cbl", FileKind.PROGRAM),
        ("ACCTDEF.cpy", FileKind.COPYBOOK),
        ("TXNDEF.cpy", FileKind.COPYBOOK),
        ("FEERATES.cpy", FileKind.COPYBOOK),
        ("accounts.dat", FileKind.DATA),
        ("transactions.dat", FileKind.DATA),
    )
)
