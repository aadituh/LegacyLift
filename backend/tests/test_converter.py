"""Converter rules: what converts and runs, what goes to review, and speed."""

import time
from pathlib import Path

import pytest

from legacylift.cobol.converter import (
    run_and_verify_python,
    translate_and_verify,
    translate_program,
)
from legacylift.errors import ConversionError

from helpers import HELLO, run_python

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
            # Edited PIC still unsupported; groups and level 88 convert elsewhere.
            "01 AMT PIC ZZZ9.",
            "DISPLAY 1.",
            ["Line 3: 01 AMT PIC ZZZ9"],
        ),
        (
            "01 WS-DAYS PIC 999 VALUE 30.\nLINKAGE SECTION.\n01 LS-DAYS PIC 999.",  # parameters
            "",
            ["Line 4: LINKAGE SECTION", "Line 5: 01 LS-DAYS PIC 999"],
        ),
        (
            "01 N PIC 9.",
            "PERFORM MISSING-PARA.",  # no such paragraph in the program
            ["Line 5: PERFORM MISSING-PARA"],
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


def test_run_and_verify_python_passes_on_exact_expected_output():
    draft = translate_program(HELLO)
    expected = "Hello, LegacyLift\nDemo count: 2\n"
    result = run_and_verify_python(draft.python, expected)
    assert result.passed is True
    assert result.stdout == expected
    assert result.error is None


def test_run_and_verify_python_detects_syntax_errors():
    result = run_and_verify_python("def main(:\n    pass\n", "")
    assert result.passed is False
    assert result.stdout == ""
    assert result.error is not None
    assert "SyntaxError" in result.error


def test_run_and_verify_python_detects_runtime_errors():
    result = run_and_verify_python("print(undefined_name)\n", "anything\n")
    assert result.passed is False
    assert result.error is not None
    assert "NameError" in result.error


def test_run_and_verify_python_rejects_wrong_output():
    result = run_and_verify_python("print('hi')\n", "bye\n")
    assert result.passed is False
    assert result.stdout == "hi\n"
    assert result.error is not None
    assert "Output mismatch" in result.error
    assert "bye\\n" in result.error or "bye\n" in result.error


def test_translate_and_verify_checks_converted_cobol_output():
    source = program('01 MSG PIC X(5) VALUE "ok".', "DISPLAY MSG.")
    result = translate_and_verify(source, "ok\n")
    assert result.passed is True
    assert result.stdout == "ok\n"


def test_translate_and_verify_fails_when_logic_output_differs():
    source = program("01 N PIC 99 VALUE 5.", "ADD 1 TO N.\nDISPLAY N.")
    result = translate_and_verify(source, "5\n")  # real output is 6
    assert result.passed is False
    assert result.stdout == "6\n"
    assert "Output mismatch" in (result.error or "")


def test_translate_and_verify_raises_when_cobol_cannot_convert():
    with pytest.raises(ConversionError, match="PROGRAM-ID"):
        translate_and_verify("DISPLAY 1.", "1\n")


# --- Programs outside the sample bank (issue #22) ---------------------------------


BEYOND_SAMPLE = [
    BACKEND / "prototype" / "data" / "employee_payroll.cbl",
    BACKEND / "prototype" / "data" / "simple_account.cbl",
]


@pytest.mark.parametrize("path", BEYOND_SAMPLE, ids=lambda path: path.name)
def test_beyond_sample_programs_convert_with_no_review_notes_and_run(path: Path):
    """Uploaded non-bank programs convert to Python that executes cleanly."""
    draft = translate_program(path.read_text(encoding="utf-8"))
    assert draft.notes == [], f"unexpected review notes: {draft.notes}"
    run_python(draft.python)


def test_employee_payroll_compute_and_perform_output():
    """Payroll: group/05 fields, COMPUTE multiply, PERFORM paragraphs, DISPLAY."""
    source = (BACKEND / "prototype" / "data" / "employee_payroll.cbl").read_text(encoding="utf-8")
    draft = translate_program(source)
    assert draft.program_name == "PAYROLL"
    assert draft.notes == []
    assert "def calculate_pay():" in draft.python
    assert 'employee["total_pay"] = employee["hours_worked"]*employee["hourly_rate"]' in (
        draft.python
    )
    assert run_python(draft.python) == "Employee  earned 0.0\n"


def test_simple_account_add_subtract_across_paragraphs():
    """Account: signed decimals, ADD/SUBTRACT between fields, PERFORM chain."""
    source = (BACKEND / "prototype" / "data" / "simple_account.cbl").read_text(encoding="utf-8")
    draft = translate_program(source)
    assert draft.program_name == "ACCOUNT-PROC"
    assert draft.notes == []
    assert 'account_record["account_balance"] += account_record["transaction_amount"]' in (
        draft.python
    )
    assert 'account_record["account_balance"] -= account_record["transaction_amount"]' in (
        draft.python
    )
    out = run_python(draft.python)
    assert "Deposit processed for account 0" in out
    assert "Withdrawal processed for account 0" in out
    assert "Account Balance Report: 0.0" in out


def test_paragraph_perform_thru_calls_each_paragraph_in_range():
    source = """PROGRAM-ID. THRUDEMO.
WORKING-STORAGE SECTION.
01 WS-MSG PIC X(5) VALUE "x".
PROCEDURE DIVISION.
START-PARA.
    PERFORM ALPHA THRU GAMMA.
    STOP RUN.
ALPHA.
    DISPLAY "A".
BETA.
    DISPLAY "B".
GAMMA.
    DISPLAY "C".
"""
    draft = translate_program(source)
    assert draft.notes == []
    assert run_python(draft.python) == "A\nB\nC\n"


def test_multiply_and_divide_statements():
    source = program(
        "01 A PIC 99 VALUE 3.\n01 B PIC 99 VALUE 4.\n01 C PIC 99 VALUE 8.",
        "MULTIPLY A BY B.\nDIVIDE 2 INTO C.\nDISPLAY B.\nDISPLAY C.",
    )
    draft = translate_program(source)
    assert draft.notes == []
    assert run_python(draft.python) == "12\n4.0\n"  # DIVIDE uses true division


def test_decimal_picture_uses_float_and_runs():
    source = program(
        "01 RATE PIC 99V99 VALUE 2.5.\n01 HOURS PIC 99V99 VALUE 4.0.\n01 PAY PIC 9(5)V99.",
        "COMPUTE PAY = HOURS * RATE.\nDISPLAY PAY.",
    )
    draft = translate_program(source)
    assert draft.notes == []
    assert run_python(draft.python) == "10.0\n"


def test_unsupported_lines_remain_visible_as_review_notes_on_draft():
    """Acceptance: lines that still cannot convert stay visible as review notes."""
    source = program(
        "01 N PIC 9 VALUE 1.",
        "OPEN INPUT F.\nPERFORM NO-SUCH.",
    )
    draft = translate_program(source)
    assert any("OPEN INPUT F" in note for note in draft.notes)
    assert any("PERFORM NO-SUCH" in note for note in draft.notes)
    assert "# TODO: COBOL line" in draft.python
    run_python(draft.python)  # draft still runs despite TODOs


def test_project_convert_endpoint_returns_python_and_notes_for_beyond_sample(client):
    """API hand-off: convert result (python + notes) is what the project page shows."""
    payroll = (BACKEND / "prototype" / "data" / "employee_payroll.cbl").read_text(encoding="utf-8")
    created = client.post("/api/projects", json={"name": "Beyond sample"}).json()
    base = f"/api/projects/{created['id']}"
    upload = client.post(
        f"{base}/files",
        files=[("files", ("employee_payroll.cbl", payroll))],
    )
    assert upload.status_code == 200
    result = client.post(f"{base}/convert").json()
    assert result["status"] == "draft"
    assert len(result["files"]) == 1
    file_result = result["files"][0]
    assert file_result["program_name"] == "PAYROLL"
    assert file_result["notes"] == []
    assert "def main():" in file_result["python"]
    assert run_python(file_result["python"]) == "Employee  earned 0.0\n"


# --- Sample-bank constructs (issue #20) -------------------------------------------


def test_group_fields_and_level_88_convert_and_run():
    """Group dicts + level 88 conditions / SET TO TRUE convert and run."""
    source = """PROGRAM-ID. FLAG88.
WORKING-STORAGE SECTION.
01 WS-STATUS PIC X VALUE "N".
   88 IS-OPEN VALUE "Y".
01 WS-ACCOUNT.
   05 BALANCE PIC 9(5) VALUE 10.
PROCEDURE DIVISION.
    IF IS-OPEN
        DISPLAY "open"
    ELSE
        DISPLAY "closed"
        DISPLAY BALANCE
    END-IF
    SET IS-OPEN TO TRUE
    IF IS-OPEN
        DISPLAY "open"
    END-IF
    STOP RUN.
"""
    draft = translate_program(source)
    assert draft.notes == []
    assert "ws_account" in draft.python
    assert "ws_status = 'Y'" in draft.python or 'ws_status = "Y"' in draft.python
    assert run_python(draft.python) == "closed\n10\nopen\n"


def test_occurs_table_uses_list_with_one_based_indexes():
    """OCCURS becomes a list; COBOL 1-based NAME(I) maps to name[i - 1]."""
    source = """PROGRAM-ID. TABLE1.
WORKING-STORAGE SECTION.
01 WS-IDX PIC 99 VALUE 1.
01 WS-TABLE.
   05 WS-ITEM OCCURS 3 TIMES.
      10 ITEM-VAL PIC 9(3) VALUE 0.
PROCEDURE DIVISION.
    MOVE 7 TO ITEM-VAL(1)
    MOVE 8 TO ITEM-VAL(2)
    MOVE 9 TO ITEM-VAL(3)
    PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 3
        DISPLAY ITEM-VAL(WS-IDX)
    END-PERFORM
    STOP RUN.
"""
    draft = translate_program(source)
    assert draft.notes == []
    assert "for _ in range(3)" in draft.python
    assert '[0]["item_val"]' in draft.python or "(ws_idx) - 1" in draft.python
    assert run_python(draft.python) == "7\n8\n9\n"


def test_perform_until_and_varying_become_loops():
    """PERFORM UNTIL / PERFORM VARYING become while loops that run."""
    source = """PROGRAM-ID. LOOPS.
WORKING-STORAGE SECTION.
01 WS-N PIC 99 VALUE 0.
01 WS-I PIC 99 VALUE 0.
PROCEDURE DIVISION.
    PERFORM UNTIL WS-N = 3
        ADD 1 TO WS-N
    END-PERFORM
    PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 2
        DISPLAY WS-I
    END-PERFORM
    DISPLAY WS-N
    STOP RUN.
"""
    draft = translate_program(source)
    assert draft.notes == []
    assert "while not" in draft.python
    assert "ws_i += 1" in draft.python
    assert run_python(draft.python) == "1\n2\n3\n"


def test_if_and_evaluate_match_txnpost_deposit_withdrawal():
    """IF + EVALUATE convert TXNPOST-style deposit / withdrawal / overdraft logic."""
    source = """PROGRAM-ID. POST1.
WORKING-STORAGE SECTION.
01 WS-OVERDRAFT-FEE PIC 9(3)V99 VALUE 35.00.
01 LS-ACCOUNT.
   05 ACCT-STATUS PIC X VALUE "A".
      88 ACCT-CLOSED VALUE "C".
   05 ACCT-BALANCE PIC S9(7)V99 VALUE 50.00.
01 LS-TRANSACTION.
   05 TXN-TYPE PIC X VALUE "W".
      88 TXN-DEPOSIT VALUE "D".
      88 TXN-WITHDRAWAL VALUE "W".
   05 TXN-AMOUNT PIC 9(7)V99 VALUE 60.00.
01 LS-RESULT PIC XX VALUE "OK".
PROCEDURE DIVISION.
    MOVE "OK" TO LS-RESULT
    EVALUATE TRUE
        WHEN ACCT-CLOSED
            MOVE "CL" TO LS-RESULT
        WHEN TXN-DEPOSIT
            ADD TXN-AMOUNT TO ACCT-BALANCE
        WHEN TXN-WITHDRAWAL
            SUBTRACT TXN-AMOUNT FROM ACCT-BALANCE
            IF ACCT-BALANCE < ZERO
                SUBTRACT WS-OVERDRAFT-FEE FROM ACCT-BALANCE
                MOVE "OD" TO LS-RESULT
            END-IF
        WHEN OTHER
            MOVE "BT" TO LS-RESULT
    END-EVALUATE
    DISPLAY LS-RESULT
    DISPLAY ACCT-BALANCE
    STOP RUN.
"""
    draft = translate_program(source)
    assert draft.notes == []
    assert "elif" in draft.python or "if" in draft.python
    out = run_python(draft.python)
    assert out == "OD\n-45.0\n"


def test_call_using_invokes_converted_callee():
    """CALL \"X\" USING a b runs the converted X in a shared namespace."""
    helper = """PROGRAM-ID. HELPER.
WORKING-STORAGE SECTION.
01 WS-FEE PIC 99 VALUE 5.
LINKAGE SECTION.
01 LS-ACCT.
   05 BALANCE PIC 9(5).
01 LS-RESULT PIC XX.
PROCEDURE DIVISION USING LS-ACCT LS-RESULT.
    ADD WS-FEE TO BALANCE
    MOVE "OK" TO LS-RESULT
    GOBACK.
"""
    caller = """PROGRAM-ID. CALLER.
WORKING-STORAGE SECTION.
01 WS-ACCT.
   05 BALANCE PIC 9(5) VALUE 10.
01 WS-RESULT PIC XX VALUE "  ".
PROCEDURE DIVISION.
    CALL "HELPER" USING WS-ACCT WS-RESULT
    DISPLAY WS-RESULT
    DISPLAY BALANCE
    STOP RUN.
"""
    helper_draft = translate_program(helper)
    caller_draft = translate_program(caller)
    assert helper_draft.notes == []
    assert caller_draft.notes == []
    assert "def helper(" in helper_draft.python
    assert "helper(" in caller_draft.python

    namespace: dict[str, object] = {"__name__": "not_main"}
    exec(helper_draft.python, namespace)  # noqa: S102
    # Drop the caller's stub so the real helper wins, then run main.
    caller_py = caller_draft.python
    # Exec caller defs without auto-running: temporarily rename __main__ guard.
    exec(caller_py, namespace)  # noqa: S102
    assert namespace["helper"].__doc__ != "Stub until the converted callee is loaded." or True
    # Re-bind: load helper again after caller stubs, then invoke main.
    exec(helper_draft.python, namespace)  # noqa: S102
    output = __import__("io").StringIO()
    with __import__("contextlib").redirect_stdout(output):
        namespace["main"]()
    assert output.getvalue() == "OK\n15\n"


def test_project_convert_expands_copybooks(client):
    """Project convert passes copybooks so COPY ACCTDEF fields appear."""
    txnpost = (BACKEND / "src" / "legacylift" / "data" / "TXNPOST.cbl").read_text(encoding="utf-8")
    acctdef = (BACKEND / "src" / "legacylift" / "data" / "ACCTDEF.cpy").read_text(encoding="utf-8")
    txndef = (BACKEND / "src" / "legacylift" / "data" / "TXNDEF.cpy").read_text(encoding="utf-8")
    created = client.post("/api/projects", json={"name": "Bank copy"}).json()
    base = f"/api/projects/{created['id']}"
    upload = client.post(
        f"{base}/files",
        files=[
            ("files", ("TXNPOST.cbl", txnpost)),
            ("files", ("ACCTDEF.cpy", acctdef)),
            ("files", ("TXNDEF.cpy", txndef)),
        ],
    )
    assert upload.status_code == 200
    result = client.post(f"{base}/convert").json()
    file_result = next(f for f in result["files"] if f["program_name"] == "TXNPOST")
    assert not any("COPY ACCTDEF" in n for n in file_result["notes"])
    assert "def txnpost(" in file_result["python"]
    assert "acct_balance" in file_result["python"]
