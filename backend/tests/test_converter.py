"""Converter rules, especially the cases that used to produce crashing Python."""

from pathlib import Path

import pytest

from legacylift.cobol.converter import translate_program

from helpers import run_python

PROTOTYPE_DATA = Path(__file__).parents[1] / "prototype" / "data"


def program(storage: str, procedure: str) -> str:
    """Build a small COBOL program from its WORKING-STORAGE and PROCEDURE lines."""
    return (
        f"PROGRAM-ID. T.\nWORKING-STORAGE SECTION.\n{storage}\n"
        f"PROCEDURE DIVISION.\n{procedure}\nSTOP RUN.\n"
    )


def test_field_named_like_a_python_builtin_still_runs():
    draft = translate_program(program('01 PRINT PIC X(5) VALUE "hi".', "DISPLAY PRINT."))
    assert draft.notes == []
    assert "print_ = 'hi'" in draft.python
    assert run_python(draft.python) == "hi\n"


def test_number_with_leading_zeros_is_valid_python():
    draft = translate_program(program("01 N PIC 9(3) VALUE 007.", "DISPLAY N."))
    assert run_python(draft.python) == "7\n"


@pytest.mark.parametrize(
    ("storage", "statement"),
    [
        ("01 N PIC 9(2).", 'MOVE "ab" TO N.'),  # text into a number
        ("01 S PIC X(2).", "MOVE 5 TO S."),  # number into text
        ("01 S PIC X(2).", 'ADD "a" TO S.'),  # ADD on text
        ("01 N PIC 9(3).", "ADD 0.1 TO N."),  # decimals are not supported yet
        ("01 N PIC 9(3).", "ADD UNKNOWN-FIELD TO N."),
    ],
)
def test_type_mismatch_goes_to_review_instead_of_crashing(storage, statement):
    draft = translate_program(program(storage, statement))
    assert any(statement.removesuffix(".") in note for note in draft.notes)
    run_python(draft.python)  # must not raise


def test_spaces_and_zero_follow_the_field_type():
    draft = translate_program(
        program("01 S PIC X(3).\n01 N PIC 9.", "MOVE SPACES TO S.\nMOVE ZERO TO N.")
    )
    assert draft.notes == []
    assert "s = ''" in draft.python
    assert "n = 0" in draft.python


def test_display_of_an_expression_goes_to_review():
    draft = translate_program(program("01 N PIC 9.", "DISPLAY N + 1."))
    assert draft.notes == ["Line 5: DISPLAY N + 1"]


def test_value_that_does_not_fit_the_picture_goes_to_review():
    draft = translate_program(program('01 N PIC 9 VALUE "ten".', "DISPLAY N."))
    assert draft.notes == ['Line 3: 01 N PIC 9 VALUE "ten"', "Line 5: DISPLAY N"]
    run_python(draft.python)


def test_every_unsupported_storage_line_is_reported():
    storage = "01 ACCOUNT.\n   05 BALANCE PIC 9(5).\n88 IS-OPEN VALUE 'Y'."
    draft = translate_program(program(storage, "DISPLAY 1."))
    assert len(draft.notes) == 3


@pytest.mark.parametrize("path", sorted(PROTOTYPE_DATA.glob("*.cbl")), ids=lambda path: path.name)
def test_sample_programs_convert_to_python_that_runs(path):
    draft = translate_program(path.read_text(encoding="utf-8"))
    compile(draft.python, path.name, "exec")
    run_python(draft.python)
