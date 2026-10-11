"""Fixed-format COBOL parser: divisions, fields, line numbers, comments skipped."""

from pathlib import Path

import pytest

from legacylift.cobol.parser import parse_program, picture_size, record_byte_length

DATA = Path(__file__).parents[1] / "src" / "legacylift" / "data"

PROGRAMS = ("BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl", "FEESCHED.cbl")


def _load(name: str) -> tuple[str, str]:
    text = (DATA / name).read_text(encoding="utf-8")
    return name, text


@pytest.mark.parametrize("filename", PROGRAMS)
def test_sample_programs_parse(filename: str) -> None:
    name, text = _load(filename)
    parsed = parse_program(name, text)
    assert parsed.program_id == filename.replace(".cbl", "")
    assert parsed.name == name
    names = {d.name for d in parsed.divisions}
    assert "IDENTIFICATION" in names
    assert "DATA" in names
    assert "PROCEDURE" in names


def test_comments_skipped_and_line_numbers_match_file() -> None:
    name, text = _load("BANKMAIN.cbl")
    raw = text.splitlines()
    parsed = parse_program(name, text)

    seen_numbers = {line.number for d in parsed.divisions for line in d.lines}
    # Comment block at lines 3–9 must not appear
    assert not any(3 <= n <= 9 for n in seen_numbers)

    for division in parsed.divisions:
        for line in division.lines:
            physical = raw[line.number - 1]
            assert len(physical) < 7 or physical[6] not in {"*", "/"}
            assert not line.text.lstrip().startswith("*")
            assert physical[7:].rstrip() == line.text.rstrip()

    by_name = {d.name: d for d in parsed.divisions}
    assert by_name["IDENTIFICATION"].start_line == 1
    assert "IDENTIFICATION DIVISION" in raw[0].upper()
    assert by_name["ENVIRONMENT"].start_line == 10
    assert "ENVIRONMENT DIVISION" in raw[9].upper()
    assert by_name["DATA"].start_line == 18
    assert "DATA DIVISION" in raw[17].upper()
    assert by_name["PROCEDURE"].start_line == 71
    assert "PROCEDURE DIVISION" in raw[70].upper()


def test_bankmain_copies_calls_paragraphs() -> None:
    parsed = parse_program(*_load("BANKMAIN.cbl"))

    assert [(c.name, c.line) for c in parsed.copies] == [
        ("ACCTDEF", 41),
        ("TXNDEF", 44),
    ]
    assert [(c.name, c.line) for c in parsed.calls] == [
        ("TXNPOST", 116),
        ("INTCALC", 156),
    ]


def test_bankmain_every_paragraph_with_start_and_end_lines() -> None:
    """Every PROCEDURE paragraph in BANKMAIN: name in col 8, contiguous spans."""
    name, text = _load("BANKMAIN.cbl")
    raw = text.splitlines()
    parsed = parse_program(name, text)

    expected = [
        ("MAIN-LOGIC", 72, 78),
        ("LOAD-ACCOUNTS", 79, 92),
        ("POST-TRANSACTIONS", 93, 110),
        ("POST-ONE-TRANSACTION", 111, 141),
        ("FIND-ACCOUNT", 142, 150),
        ("PRINT-STATEMENT", 151, 172),
    ]
    assert [(p.name, p.start_line, p.end_line) for p in parsed.paragraphs] == expected

    for para in parsed.paragraphs:
        header = raw[para.start_line - 1]
        # Name begins in column 8 (1-based) and ends with a period
        assert header[7] not in " \t"
        assert header[7:].strip() == f"{para.name}."
        assert para.end_line >= para.start_line

    # Each paragraph ends where the next one starts
    for prev, nxt in zip(
        parsed.paragraphs, parsed.paragraphs[1:], strict=False
    ):
        assert prev.end_line + 1 == nxt.start_line

    assert "PERFORM LOAD-ACCOUNTS" in parsed.paragraphs[0].body


def test_paragraph_requires_column_8() -> None:
    text = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. P.\n"
        "       PROCEDURE DIVISION.\n"
        "       REAL-PARA.\n"
        "           DISPLAY \"HI\".\n"
        "           FAKE-PARA.\n"
        "           DISPLAY \"NO\".\n"
        "       NEXT-PARA.\n"
        "           STOP RUN.\n"
    )
    parsed = parse_program("P.cbl", text)
    assert [(p.name, p.start_line, p.end_line) for p in parsed.paragraphs] == [
        ("REAL-PARA", 4, 7),
        ("NEXT-PARA", 8, 9),
    ]


def test_fields_keep_picture_value_occurs_and_line() -> None:
    parsed = parse_program(*_load("BANKMAIN.cbl"))
    by_name = {f.name: f for f in parsed.fields if f.name != "FILLER"}
    assert by_name["WS-DAYS"].line == 31
    assert by_name["WS-DAYS"].picture == "999"
    assert by_name["WS-DAYS"].level == "01"
    assert by_name["WS-DAYS"].value == "30"
    assert by_name["WS-ACCOUNT"].occurs == 10
    assert by_name["WS-ACCOUNT"].picture is None
    assert by_name["END-OF-FILE"].level == "88"
    assert by_name["END-OF-FILE"].line == 27
    assert by_name["END-OF-FILE"].parent == "WS-END-OF-FILE"
    assert by_name["END-OF-FILE"].value == '"Y"'
    fillers = [f for f in parsed.fields if f.name == "FILLER"]
    assert any(f.value == "SPACES" for f in fillers)


@pytest.mark.parametrize(
    ("filename", "expected_bytes"),
    [
        ("ACCTDEF.cpy", 43),
        ("TXNDEF.cpy", 16),
    ],
)
def test_copybook_record_byte_length(filename: str, expected_bytes: int) -> None:
    parsed = parse_program(*_load(filename))
    assert parsed.divisions == []
    assert parsed.fields
    assert record_byte_length(parsed.fields) == expected_bytes


def test_acctdef_fields_and_level_88_parents() -> None:
    parsed = parse_program(*_load("ACCTDEF.cpy"))
    by_name = {f.name: f for f in parsed.fields}
    assert by_name["ACCT-ID"].level == "10"
    assert by_name["ACCT-ID"].picture == "X(6)"
    assert by_name["ACCT-BALANCE"].picture == "S9(7)V99"
    assert by_name["ACCT-BALANCE"].sign_separate is True
    assert picture_size("S9(7)V99", sign_separate=True) == 10
    assert by_name["ACCT-SAVINGS"].level == "88"
    assert by_name["ACCT-SAVINGS"].parent == "ACCT-TYPE"
    assert by_name["ACCT-SAVINGS"].value == '"S"'
    assert by_name["ACCT-ACTIVE"].parent == "ACCT-STATUS"


def test_continuation_dash_merges_onto_previous_line() -> None:
    # Fixed-format: col 7 ``-`` continues the previous line; line number stays
    # on the first physical line of the statement.
    text = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. CONTDEMO.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        '       01  MSG PIC X(20) VALUE\n'
        '      -    "HELLO".\n'
        "       PROCEDURE DIVISION.\n"
        "       MAIN.\n"
        "           DISPLAY MSG.\n"
        "           STOP RUN.\n"
    )
    parsed = parse_program("CONTDEMO.cbl", text)
    msgs = [f for f in parsed.fields if f.name == "MSG"]
    assert len(msgs) == 1
    assert msgs[0].line == 5
    # Merged text should include the continued fragment
    data = next(d for d in parsed.divisions if d.name == "DATA")
    joined = " ".join(sl.text for sl in data.lines)
    assert "HELLO" in joined
    assert parsed.paragraphs[0].name == "MAIN"


def test_comment_indicator_never_becomes_code() -> None:
    text = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. CMT.\n"
        "      *THIS IS A COMMENT WITH CALL \"FAKE\" AND COPY BOGUS.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        "       01  X PIC 9.\n"
        "       PROCEDURE DIVISION.\n"
        "           DISPLAY X.\n"
    )
    parsed = parse_program("CMT.cbl", text)
    assert parsed.copies == []
    assert parsed.calls == []
    assert all(d.name != "ENVIRONMENT" or d.lines for d in parsed.divisions)


@pytest.mark.parametrize(
    ("filename", "copies", "calls", "paragraphs"),
    [
        ("TXNPOST.cbl", ["ACCTDEF", "TXNDEF"], [], ["POST-TRANSACTION"]),
        ("INTCALC.cbl", ["ACCTDEF"], [], ["CALCULATE-INTEREST"]),
        ("FEESCHED.cbl", [], [], []),
    ],
)
def test_other_samples_refs(
    filename: str,
    copies: list[str],
    calls: list[str],
    paragraphs: list[str],
) -> None:
    parsed = parse_program(*_load(filename))
    assert [c.name for c in parsed.copies] == copies
    assert [c.name for c in parsed.calls] == calls
    assert [p.name for p in parsed.paragraphs] == paragraphs
