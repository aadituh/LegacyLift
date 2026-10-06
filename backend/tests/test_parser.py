"""Fixed-format COBOL parser: divisions, line numbers, comments skipped."""

from pathlib import Path

import pytest

from legacylift.cobol.parser import parse_program

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
    para_names = [p.name for p in parsed.paragraphs]
    assert para_names == [
        "MAIN-LOGIC",
        "LOAD-ACCOUNTS",
        "POST-TRANSACTIONS",
        "POST-ONE-TRANSACTION",
        "FIND-ACCOUNT",
        "PRINT-STATEMENT",
    ]
    main = parsed.paragraphs[0]
    assert main.start_line == 72
    assert "PERFORM LOAD-ACCOUNTS" in main.body


def test_fields_keep_source_line_numbers() -> None:
    parsed = parse_program(*_load("BANKMAIN.cbl"))
    by_name = {f.name: f for f in parsed.fields if f.name != "FILLER"}
    assert by_name["WS-DAYS"].line == 31
    assert by_name["WS-DAYS"].pic == "999"
    assert by_name["WS-DAYS"].level == "01"
    assert by_name["END-OF-FILE"].level == "88"
    assert by_name["END-OF-FILE"].line == 27


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
