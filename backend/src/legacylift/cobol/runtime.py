"""COBOL-like storage and DISPLAY helpers for generated Python (issue #21).

GnuCOBOL / standard DISPLAY rules this module mirrors
----------------------------------------------------
These ten cases are the team's written record of real COBOL behaviour
(compare with recorded fixtures under ``tests/data/recorded/`` and issue #36):

1. ``PIC 9(4)`` holding 14 **DISPLAY**s as ``0014`` (leading zeros).
2. ``PIC 9(3)`` holding 1234 **stores/displays** ``234`` (leftmost digits drop).
3. ``PIC 9(3)`` receiving ``-5`` **stores/displays** ``005`` (unsigned drops sign).
4. ``PIC S9(3)`` receiving ``-5`` **DISPLAY**s ``-005`` (sign kept).
5. ``PIC X(10)`` holding ``"HI"`` **DISPLAY**s ``HI        `` (space pad on the right).
6. ``PIC X(10)`` holding ``"ABCDEFGHIJKLMN"`` **DISPLAY**s ``ABCDEFGHIJ`` (cut on the right).
7. ``PIC 9V99`` stores with two fractional places; ``1.239`` without ``ROUNDED``
   becomes ``1.23`` (extra digits cut / truncated toward zero).
8. ``PIC 9V99`` with ``ROUNDED`` and ``1.235`` becomes ``1.24`` (half up / away from 0).
9. ``PIC 9(3)`` ``VALUE 35`` **DISPLAY**s ``035`` (FEESCHED overdraft fee).
10. ``PIC 9(4)`` total ``65`` **DISPLAY**s ``0065`` (FEESCHED all-fees line).

INTCALC interest (case used by BANKMAIN): for balance ``1250.05``, rate
``0.0250``, ``30`` days, ``365``-day year, ``COMPUTE … ROUNDED`` to
``S9(7)V99`` yields ``2.57``.

Generated drafts import::

    from legacylift.cobol.runtime import cobol_number, cobol_text, display_number
"""

from __future__ import annotations

import re
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import NamedTuple

_TEXT_PIC = re.compile(r"^X(?:\((\d+)\))?$|^X+$", re.IGNORECASE)
_NINE = re.compile(r"9(?:\((\d+)\))?")


class NumericPicture(NamedTuple):
    """Parsed numeric PIC: digit counts and sign."""

    integers: int
    decimals: int
    signed: bool


def analyze_numeric_picture(picture: str) -> NumericPicture | None:
    """Parse ``9(n)``, ``S9(7)V99``, ``9V9999``, etc. Return ``None`` if not numeric."""
    pic = re.sub(r"\s+", "", picture.upper())
    signed = pic.startswith("S")
    if signed:
        pic = pic[1:]
    if not pic or pic[0] != "9":
        return None
    if "V" in pic:
        left, right = pic.split("V", 1)
    else:
        left, right = pic, ""
    return NumericPicture(_count_nines(left), _count_nines(right), signed)


def analyze_text_length(picture: str) -> int | None:
    """Return length for ``PIC X`` / ``XX`` / ``X(n)``, else ``None``."""
    pic = re.sub(r"\s+", "", picture.upper())
    match = _TEXT_PIC.fullmatch(pic)
    if match is None:
        return None
    if match.group(1):
        return int(match.group(1))
    return pic.count("X")


def _count_nines(chunk: str) -> int:
    total = 0
    for match in _NINE.finditer(chunk):
        total += int(match.group(1)) if match.group(1) else 1
    return total


def cobol_text(value: object, length: int) -> str:
    """Fit a value into ``PIC X(length)``: pad right with spaces or truncate.

    Args:
        value: Any value; converted with ``str``.
        length: Picture length (must be >= 0).

    Returns:
        A string of exactly ``length`` characters.
    """
    if length < 0:
        raise ValueError("text length must be non-negative")
    text = "" if value is None else str(value)
    if len(text) >= length:
        return text[:length]
    return text.ljust(length)


def cobol_number(
    value: object,
    *,
    integers: int,
    decimals: int = 0,
    signed: bool = False,
    rounded: bool = False,
) -> Decimal:
    """Fit a value into a numeric PIC (overflow, unsigned sign drop, scale).

    Args:
        value: Number-like value (``int``, ``float``, ``str``, ``Decimal``).
        integers: Count of ``9`` digits left of the implied decimal.
        decimals: Count of ``9`` digits right of ``V`` (0 for whole numbers).
        signed: ``True`` for ``S9…`` pictures; unsigned drops a leading minus.
        rounded: ``True`` for ``ROUNDED`` (half away from zero); otherwise
            truncate toward zero.

    Returns:
        A ``Decimal`` quantized to ``decimals`` places and reduced modulo
        ``10**integers`` on the integer side (left digits discarded on overflow).
    """
    if integers < 0 or decimals < 0:
        raise ValueError("digit counts must be non-negative")
    number = Decimal(str(value))
    if not signed and number < 0:
        number = -number

    quant = Decimal(1).scaleb(-decimals) if decimals else Decimal(1)
    mode = ROUND_HALF_UP if rounded else ROUND_DOWN
    number = number.quantize(quant, rounding=mode)

    # Split integer / fractional; overflow keeps the rightmost ``integers`` digits.
    sign = Decimal(-1) if number < 0 else Decimal(1)
    magnitude = abs(number)
    integer_part = int(magnitude.to_integral_value(rounding=ROUND_DOWN))
    frac = magnitude - integer_part
    modulus = 10**integers if integers > 0 else 1
    integer_part %= modulus
    result = sign * (Decimal(integer_part) + frac)
    return result.quantize(quant, rounding=ROUND_DOWN)


def display_number(
    value: object,
    *,
    integers: int,
    decimals: int = 0,
    signed: bool = False,
) -> str:
    """Format a stored number the way COBOL ``DISPLAY`` prints a numeric PIC.

    Whole numbers are zero-padded to ``integers`` digits. Decimals include a
    decimal point and exactly ``decimals`` fractional digits. Signed negatives
    get a leading ``-``; positives have no ``+`` (plain DISPLAY, not
    ``SIGN LEADING SEPARATE``).
    """
    number = cobol_number(value, integers=integers, decimals=decimals, signed=signed)
    negative = number < 0
    magnitude = abs(number)
    if decimals == 0:
        body = f"{int(magnitude):0{max(integers, 1)}d}"
    else:
        # e.g. integers=1, decimals=2, value 1.5 → "1.50"
        as_str = f"{magnitude:.{decimals}f}"
        whole, frac = as_str.split(".")
        body = f"{int(whole):0{max(integers, 1)}d}.{frac}"
    if signed and negative:
        return f"-{body}"
    return body
