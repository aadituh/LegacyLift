"""Converter rules: what converts and runs, what goes to review, and speed."""

import time
from pathlib import Path

import pytest

from legacylift.cobol.converter import translate_program

from helpers import run_python

BACKEND = Path(__file__).parents[1]
SAMPLES = sorted((BACKEND / "prototype" / "data").glob("*.cbl"))
SAMPLES += sorted((BACKEND / "src" / "legacylift" / "data").glob("*.cbl"))


def program(storage: str, procedure: str) -> str:
    """A small COBOL program. Storage starts on line 3; the procedure on line 5."""
    return (
        f"PROGRAM-ID. T.\nWORKING-STORAGE SECTION.\n{storage}\n"
        f"PROCEDURE DIVISION.\n{procedure}\nSTOP RUN.\n"
    )


@pytest.mark.parametrize(
    ("storage", "procedure", "printed"),
    [
        ('01 PRINT PIC X(5) VALUE "hi".', "DISPLAY PRINT.", "hi\n"),  # name of a built-in
        ("01 N PIC 9(3) VALUE 007.", "DISPLAY N.", "7\n"),  # leading zeros
        ("01 S PIC X(3).\n01 N PIC 9.", "MOVE SPACES TO S.\nMOVE ZERO TO N.\nDISPLAY S N.", "0\n"),
        ("01 N PIC 99 VALUE 5.", "ADD 1 TO N.\nDISPLAY N.", "6\n"),
        ("01 N PIC 999 VALUE 10.", "SUBTRACT 3 FROM N.\nDISPLAY N.", "7\n"),
        ('01 S PIC XX VALUE "AB".', "DISPLAY S.", "AB\n"),
        ("01 S PIC X(20).", 'MOVE "GO  TO IT" TO S.\nDISPLAY S.', "GO  TO IT\n"),
        ("01 S PIC X(9).", 'DISPLAY "It""s".', 'It"s\n'),  # a doubled quote is one quote
        ("01 S PIC X(9).", "DISPLAY 'It''s'.", "It's\n"),
        ("01 S PIC X(9).", 'MOVE "It""s" TO S.\nDISPLAY S.', 'It"s\n'),
    ],
)
def test_supported_code_converts_and_runs(storage, procedure, printed):
    draft = translate_program(program(storage, procedure))
    assert draft.notes == []
    assert run_python(draft.python) == printed


@pytest.mark.parametrize(
    ("storage", "procedure", "notes"),
    [
        ("01 N PIC 9(2).", 'MOVE "ab" TO N.', ['Line 5: MOVE "ab" TO N']),  # text into a number
        ("01 S PIC X(2).", "MOVE 5 TO S.", ["Line 5: MOVE 5 TO S"]),  # number into text
        ("01 S PIC X(2).", 'ADD "a" TO S.', ['Line 5: ADD "a" TO S']),
        ("01 N PIC 9(3).", "ADD 0.1 TO N.", ["Line 5: ADD 0.1 TO N"]),  # decimals
        ("01 N PIC 9(3).", "ADD OTHER TO N.", ["Line 5: ADD OTHER TO N"]),  # unknown field
        ("01 N PIC 9.", "DISPLAY N + 1.", ["Line 5: DISPLAY N + 1"]),  # expression
        ("01 S PIC X(9).", 'MOVE "A" "B" TO S.', ['Line 5: MOVE "A" "B" TO S']),
        (
            '01 N PIC 9 VALUE "ten".',
            "DISPLAY N.",
            ['Line 3: 01 N PIC 9 VALUE "ten"', "Line 5: DISPLAY N"],
        ),
        (
            "01 ACCOUNT.\n   05 BALANCE PIC 9(5).\n88 IS-OPEN VALUE 'Y'.",  # group and level 88
            "DISPLAY 1.",
            ["Line 3: 01 ACCOUNT", "Line 4: 05 BALANCE PIC 9(5)", "Line 5: 88 IS-OPEN VALUE 'Y'"],
        ),
        (
            "01 WS-DAYS PIC 999 VALUE 30.\nLINKAGE SECTION.\n01 LS-DAYS PIC 999.",  # parameters
            "",
            ["Line 4: LINKAGE SECTION", "Line 5: 01 LS-DAYS PIC 999"],
        ),
    ],
)
def test_unsupported_code_goes_to_review_and_still_runs(storage, procedure, notes):
    draft = translate_program(program(storage, procedure))
    assert draft.notes == notes
    run_python(draft.python)


@pytest.mark.parametrize("verb", ["MOVE", "ADD", "SUBTRACT"])
def test_very_long_line_converts_quickly(verb):
    started = time.perf_counter()
    draft = translate_program(program("01 N PIC 9.", verb + " " * 100_000 + "X."))
    assert time.perf_counter() - started < 2
    assert len(draft.notes) == 1


@pytest.mark.parametrize("path", SAMPLES, ids=lambda path: path.name)
def test_sample_programs_convert_to_python_that_runs(path):
    run_python(translate_program(path.read_text(encoding="utf-8")).python)
