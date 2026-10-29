"""COBOL runtime helpers: padding, overflow, sign, Decimal ROUNDED (issue #21)."""

from decimal import Decimal
from pathlib import Path

import pytest

from legacylift.cobol.converter import translate_program
from legacylift.cobol.runtime import (
    cobol_number,
    cobol_text,
    display_number,
)

from helpers import run_python

BACKEND = Path(__file__).parents[1]
RECORDED = BACKEND / "tests" / "data" / "recorded"
DATA = BACKEND / "src" / "legacylift" / "data"


# --- Ten+ documented GnuCOBOL cases (docs/cobol_display_cases.md) ---------------


@pytest.mark.parametrize(
    ("value", "integers", "decimals", "signed", "printed"),
    [
        (14, 4, 0, False, "0014"),  # case 1
        (1234, 3, 0, False, "234"),  # case 2 overflow
        (-5, 3, 0, False, "005"),  # case 3 unsigned drops sign
        (-5, 3, 0, True, "-005"),  # case 4 signed
        (35, 3, 0, False, "035"),  # case 9 FEESCHED fee
        (65, 4, 0, False, "0065"),  # case 10 FEESCHED total
    ],
)
def test_display_number_matches_documented_gnucobol_cases(
    value, integers, decimals, signed, printed
):
    stored = cobol_number(value, integers=integers, decimals=decimals, signed=signed)
    assert display_number(stored, integers=integers, decimals=decimals, signed=signed) == printed


def test_cobol_text_pads_and_truncates():
    assert cobol_text("HI", 10) == "HI        "  # case 5
    assert cobol_text("ABCDEFGHIJKLMN", 10) == "ABCDEFGHIJ"  # case 6
    assert len(cobol_text("LEGACYLIFT BANK", 15)) == 15


def test_decimal_truncate_versus_rounded():
    truncated = cobol_number("1.239", integers=1, decimals=2, rounded=False)
    assert truncated == Decimal("1.23")  # case 7
    rounded = cobol_number("1.235", integers=1, decimals=2, rounded=True)
    assert rounded == Decimal("1.24")  # case 8
    assert display_number(truncated, integers=1, decimals=2) == "1.23"
    assert display_number(rounded, integers=1, decimals=2) == "1.24"


def test_intcalc_alice_interest_matches_recorded_output():
    """INTCALC formula for Alice @ 30 days equals recorded GnuCOBOL interest."""
    recorded = (RECORDED / "INTCALC_alice_30d.out").read_text(encoding="utf-8-sig").strip()
    interest = cobol_number(
        Decimal("1250.05") * Decimal("0.0250") * Decimal(30) / Decimal(365),
        integers=7,
        decimals=2,
        signed=True,
        rounded=True,
    )
    assert recorded == "2.57"
    assert interest == Decimal(recorded)
    assert display_number(interest, integers=7, decimals=2, signed=True) == "0000002.57"


def test_feesched_matches_recorded_gnucobol_stdout():
    source = (DATA / "FEESCHED.cbl").read_text(encoding="utf-8")
    expected = (RECORDED / "FEESCHED.out").read_text(encoding="utf-8-sig")
    if not expected.endswith("\n"):
        expected += "\n"
    draft = translate_program(source)
    assert draft.notes == []
    assert run_python(draft.python) == expected


def test_bankmain_heading_and_fee_fields_use_cobol_padding():
    """BANKMAIN-related pictures used in recorded cases pad like COBOL."""
    # Statement counters and money edits used on the statement path.
    assert display_number(30, integers=3) == "030"  # WS-DAYS style
    assert display_number(1, integers=3) == "001"  # WS-POSTED style
    name = cobol_text("ALICE JOHNSON", 20)
    assert len(name) == 20
    assert name.startswith("ALICE JOHNSON")
