"""Recorded GnuCOBOL output for the sample bank (tests/data/recorded/).

Re-record with scripts/record_cobol_output.py after changing a case or a sample program.
"""

import shutil
from pathlib import Path

import pytest

from legacylift.runner.sandbox import run_cobol

BACKEND = Path(__file__).resolve().parents[1]
SAMPLE = BACKEND / "src" / "legacylift" / "data"
BANK = BACKEND / "tests" / "data" / "recorded" / "bank"
CASES = ["sample", "normal", "overdraft", "closed"]
RECORD_WIDTHS = {"accounts.dat": 43, "transactions.dat": 16}

needs_cobc = pytest.mark.skipif(shutil.which("cobc") is None, reason="GnuCOBOL is not installed")


def read(folder: Path, *names: str) -> dict[str, str]:
    return {name: (folder / name).read_text(encoding="utf-8") for name in names}


def case_data(case: str) -> dict[str, str]:
    """The case's .dat files; the sample case uses the shipped sample data."""
    return read(SAMPLE if case == "sample" else BANK / case, *RECORD_WIDTHS)


def recorded(case: str) -> str:
    return (BANK / case / "BANKMAIN.out").read_text(encoding="utf-8")


@pytest.mark.parametrize("case", CASES)
def test_case_records_have_the_copybook_widths(case: str):
    for name, text in case_data(case).items():
        widths = {len(line) for line in text.splitlines()}
        assert widths == {RECORD_WIDTHS[name]}, name


@pytest.mark.parametrize(
    ("case", "expected_lines"),
    [
        ("normal", ["POSTED:     5", "REJECTED:   0", "TOTAL INTEREST:            40.65"]),
        (
            "overdraft",
            [
                "  300001 W      150.00  POSTED, OVERDRAFT FEE   ",
                "300001 OMAR HASSAN          C A      -40.00       0.00",
                "300002 LENA BERG            C A        0.00       0.00",
            ],
        ),
        (
            "closed",
            [
                "  400001 W       50.00  REJECTED: ACCOUNT CLOSED",
                "400001 RUTH ADAMS           S C    2,500.00       0.00",
                "REJECTED:   4",
            ],
        ),
    ],
)
def test_recorded_output_shows_what_the_case_is_for(case: str, expected_lines: list[str]):
    lines = recorded(case).splitlines()
    for line in expected_lines:
        assert line in lines


@needs_cobc
@pytest.mark.parametrize("case", CASES)
def test_gnucobol_still_prints_the_recorded_output(case: str):
    result = run_cobol(
        read(SAMPLE, "BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl"),
        main="BANKMAIN.cbl",
        copybooks=read(SAMPLE, "ACCTDEF.cpy", "TXNDEF.cpy"),
        data_files=case_data(case),
    )
    assert result.ok, result.stderr
    assert result.stdout == recorded(case)
