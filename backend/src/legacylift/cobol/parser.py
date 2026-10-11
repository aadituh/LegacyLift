"""Fixed-format COBOL text parser: divisions, fields, paragraphs, COPY/CALL.

Reads source only — never compiles or runs the program. Column rules match
IBM fixed format:

* columns 1–6: sequence area (ignored)
* column 7: ``*`` / ``/`` comment, ``-`` continues the previous line, space = code
* columns 8+: Area A/B source text

Hand-off for the API and analyzer::

    parse_program(name, text) -> ParsedProgram
    ParsedProgram.fields: list[Field(level, name, picture, value, occurs, line)]
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel
from pydantic import Field as PydanticField

DivisionName = Literal[
    "IDENTIFICATION",
    "ENVIRONMENT",
    "DATA",
    "PROCEDURE",
]

_DIVISION_ORDER: tuple[DivisionName, ...] = (
    "IDENTIFICATION",
    "ENVIRONMENT",
    "DATA",
    "PROCEDURE",
)

_DIVISION_HEADER_RE = re.compile(
    r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b",
    re.IGNORECASE,
)

_PROGRAM_ID_RE = re.compile(
    r"PROGRAM-ID\.\s*([A-Z0-9][A-Z0-9-]*)",
    re.IGNORECASE,
)

_SECTION_HEADER_RE = re.compile(
    r"^([A-Z][A-Z0-9-]*)\s+SECTION\s*\.",
    re.IGNORECASE,
)

# Levels 01–49, 66, 77, 88 (copybooks often use 10 under a host 01/05).
_FIELD_START_RE = re.compile(
    r"^(0?[1-9]|[1-4]\d|66|77|88)\s+([A-Z0-9][A-Z0-9-]*|FILLER)\b",
    re.IGNORECASE,
)

_PIC_RE = re.compile(r"\bPIC(?:TURE)?\s+([^\s]+)", re.IGNORECASE)

_OCCURS_RE = re.compile(
    r"\bOCCURS\s+(\d+)(?:\s+TO\s+(\d+))?\s+TIMES\b",
    re.IGNORECASE,
)

_VALUE_KW_RE = re.compile(r"\bVALUE(?:\s+IS)?\s+", re.IGNORECASE)

_SIGN_SEPARATE_RE = re.compile(r"\bSIGN\b.+\bSEPARATE\b", re.IGNORECASE)

# One PIC symbol with optional repeat count, or V / P (no storage).
_PIC_TOKEN_RE = re.compile(
    r"([AX9Z*])(?:\((\d+)\))?|(DB|CR)|([-+.$,/CRB0]+)|V|P(?:\((\d+)\))?",
    re.IGNORECASE,
)

_PARAGRAPH_RE = re.compile(
    r"^([A-Z][A-Z0-9-]*)\s*\.\s*$",
    re.IGNORECASE,
)

_COPY_RE = re.compile(
    r"\bCOPY\s+([A-Z0-9][A-Z0-9-]*)\b",
    re.IGNORECASE,
)

_CALL_RE = re.compile(
    r"""\bCALL\s+(?:"([^"]+)"|'([^']+)'|([A-Z0-9][A-Z0-9-]*))""",
    re.IGNORECASE,
)

# Paragraph PERFORM (not PERFORM UNTIL / VARYING / n TIMES loops).
_PERFORM_RE = re.compile(
    r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]*)"
    r"(?:\s+(?:THRU|THROUGH)\s+([A-Z0-9][A-Z0-9-]*))?",
    re.IGNORECASE,
)

_PERFORM_LOOP_STARTERS = frozenset({"UNTIL", "VARYING", "WITH", "TEST"})

_SKIP_PARAGRAPH_NAMES = frozenset(
    {
        "IDENTIFICATION",
        "ENVIRONMENT",
        "DATA",
        "PROCEDURE",
        "WORKING-STORAGE",
        "LINKAGE",
        "FILE",
        "CONFIGURATION",
        "INPUT-OUTPUT",
        "FILE-CONTROL",
        "DIVISION",
        "SECTION",
        "PROGRAM",
        "STOP",
    }
)


class SourceLine(BaseModel):
    """One non-comment source line with its original 1-based file line number."""

    number: int
    text: str


class Division(BaseModel):
    """A COBOL division span within the source file."""

    name: DivisionName
    start_line: int
    end_line: int
    lines: list[SourceLine] = PydanticField(default_factory=list)


class Field(BaseModel):
    """A data-item declaration with PIC / VALUE / OCCURS when present.

    Level-88 condition names set ``parent`` to the elementary field above them.
    """

    level: str
    name: str
    picture: str | None = None
    value: str | None = None
    occurs: int | None = None
    line: int
    parent: str | None = None
    sign_separate: bool = False
    section: str | None = None


class Paragraph(BaseModel):
    """A PROCEDURE DIVISION paragraph (name in column 8, ends before the next).

    ``body`` is the source between the header and the next paragraph (optional
    for callers that only need ``name`` / ``start_line`` / ``end_line``).
    """

    name: str
    start_line: int
    end_line: int
    body: str = ""


class CopyRef(BaseModel):
    """A ``COPY`` copybook reference."""

    name: str
    line: int


class CallRef(BaseModel):
    """A ``CALL`` program reference."""

    name: str
    line: int


class PerformRef(BaseModel):
    """A paragraph ``PERFORM`` (optional ``THRU``) inside PROCEDURE DIVISION."""

    caller: str | None
    name: str
    thru: str | None = None
    line: int


class ParsedProgram(BaseModel):
    """Structured view of one COBOL program or copybook for the API / analyzer."""

    name: str
    program_id: str
    divisions: list[Division] = PydanticField(default_factory=list)
    fields: list[Field] = PydanticField(default_factory=list)
    paragraphs: list[Paragraph] = PydanticField(default_factory=list)
    copies: list[CopyRef] = PydanticField(default_factory=list)
    calls: list[CallRef] = PydanticField(default_factory=list)
    performs: list[PerformRef] = PydanticField(default_factory=list)


def _code_area(raw: str) -> tuple[str, str] | None:
    """Return ``(indicator, code)`` for a physical line, or ``None`` if blank.

    Comments (``*`` / ``/`` in column 7) return ``None`` so callers skip them.
    Lines shorter than 7 characters are treated as free-format code with a
    blank indicator.
    """
    line = raw.rstrip("\r\n").rstrip()
    if not line.strip():
        return None

    if len(line) >= 7:
        indicator = line[6]
        code = line[7:]
        if indicator in {"*", "/"}:
            return None
        return indicator, code

    stripped = line.lstrip()
    if stripped.startswith("*"):
        return None
    return " ", line


def _physical_lines(text: str) -> list[SourceLine]:
    """Map file text to non-comment code lines, applying ``-`` continuations.

    Continued fragments keep the *first* line's number for the merged text so
    statements stay anchored where they begin.
    """
    result: list[SourceLine] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        parsed = _code_area(raw)
        if parsed is None:
            continue
        indicator, code = parsed
        if indicator == "-" and result:
            prev = result[-1]
            result[-1] = SourceLine(number=prev.number, text=prev.text + code)
            continue
        result.append(SourceLine(number=number, text=code))
    return result


def _match_division(text: str) -> DivisionName | None:
    match = _DIVISION_HEADER_RE.match(text.strip())
    if not match:
        return None
    return match.group(1).upper()  # type: ignore[return-value]


def _split_divisions(lines: list[SourceLine]) -> list[Division]:
    """Group source lines under IDENTIFICATION / ENVIRONMENT / DATA / PROCEDURE."""
    starts: list[tuple[int, DivisionName]] = []
    for idx, line in enumerate(lines):
        name = _match_division(line.text)
        if name is not None:
            starts.append((idx, name))

    if not starts:
        return []

    divisions: list[Division] = []
    for i, (start_idx, name) in enumerate(starts):
        end_idx = starts[i + 1][0] - 1 if i + 1 < len(starts) else len(lines) - 1
        chunk = lines[start_idx : end_idx + 1]
        divisions.append(
            Division(
                name=name,
                start_line=chunk[0].number,
                end_line=chunk[-1].number,
                lines=chunk,
            )
        )
    order = {n: i for i, n in enumerate(_DIVISION_ORDER)}
    divisions.sort(key=lambda d: (order.get(d.name, 99), d.start_line))
    return divisions


def _extract_program_id(lines: list[SourceLine], fallback: str) -> str:
    for line in lines:
        match = _PROGRAM_ID_RE.search(line.text)
        if match:
            return match.group(1).upper()
    stem = fallback.rsplit(".", 1)[0]
    return stem.upper() if stem else "UNKNOWN"


def _division_by_name(
    divisions: list[Division], name: DivisionName
) -> Division | None:
    for division in divisions:
        if division.name == name:
            return division
    return None


def _normalize_level(raw: str) -> str:
    """Normalize a level number to two digits (``5`` → ``05``)."""
    return f"{int(raw):02d}"


def _clause_ends_field(text: str) -> bool:
    """True when the accumulated field clause ends with a period."""
    return text.rstrip().endswith(".")


def _is_field_start(text: str) -> bool:
    return _FIELD_START_RE.match(text.strip()) is not None


def _extract_value(clause: str) -> str | None:
    """Pull the VALUE operand from a field clause (quotes preserved)."""
    match = _VALUE_KW_RE.search(clause)
    if not match:
        return None

    rest = clause[match.end() :].rstrip().rstrip(".")
    parts: list[str] = []
    i = 0
    while i < len(rest):
        ch = rest[i]
        if ch in " \t":
            i += 1
            continue
        if ch == ",":
            parts.append(",")
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            j = i + 1
            while j < len(rest):
                if rest[j] == quote:
                    if j + 1 < len(rest) and rest[j + 1] == quote:
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            parts.append(rest[i:j])
            i = j
            continue

        m = re.match(r"[^\s,]+", rest[i:])
        if not m:
            break
        token = m.group(0)
        upper = token.upper()
        if upper in {"OCCURS", "SIGN", "ASCENDING", "DESCENDING", "INDEXED", "REDEFINES"}:
            break
        parts.append(token)
        i += m.end()

    if not parts:
        return None
    value = " ".join(parts)
    value = re.sub(r"\s*,\s*", ", ", value).strip()
    return value or None


def _extract_occurs(clause: str) -> int | None:
    match = _OCCURS_RE.search(clause)
    if not match:
        return None
    low = int(match.group(1))
    high = match.group(2)
    return int(high) if high else low


def _extract_picture(clause: str) -> str | None:
    match = _PIC_RE.search(clause)
    if not match:
        return None
    return match.group(1).upper().rstrip(".")


def picture_size(picture: str, *, sign_separate: bool = False) -> int:
    """Return DISPLAY storage bytes for a PIC string.

    ``V`` (implied decimal) and ``P`` (scaling) take no storage. A leading
    ``S`` takes one extra byte only when ``sign_separate`` is true (SIGN
    LEADING/TRAILING SEPARATE).
    """
    pic = re.sub(r"\s+", "", picture.upper())
    signed = pic.startswith("S")
    if signed:
        pic = pic[1:]

    size = 0
    pos = 0
    for match in _PIC_TOKEN_RE.finditer(pic):
        if match.start() != pos:
            # Unrecognized character (edited insertion); count it
            size += match.start() - pos
        pos = match.end()
        token = match.group(0)
        if token.startswith("V") or token.startswith("P"):
            continue
        if match.group(1):
            count = int(match.group(2)) if match.group(2) else 1
            size += count
            continue
        if match.group(3):  # DB / CR
            size += len(match.group(3))
            continue
        if match.group(4):  # edited symbols run
            size += len(match.group(4))
            continue
    if pos < len(pic):
        size += len(pic) - pos

    if signed and sign_separate:
        size += 1
    return size


def record_byte_length(fields: list[Field]) -> int:
    """Sum elementary field sizes (with OCCURS); skip groups and level 88."""
    total = 0
    for field in fields:
        if field.level == "88" or not field.picture:
            continue
        size = picture_size(field.picture, sign_separate=field.sign_separate)
        if field.occurs is not None:
            size *= field.occurs
        total += size
    return total


def _parse_field_clause(
    clause: str,
    *,
    line: int,
    section: str | None,
    parent: str | None,
) -> Field | None:
    match = _FIELD_START_RE.match(clause.strip())
    if not match:
        return None

    level = _normalize_level(match.group(1))
    name = match.group(2).upper()
    picture = _extract_picture(clause)
    value = _extract_value(clause)
    occurs = _extract_occurs(clause)
    sign_separate = bool(_SIGN_SEPARATE_RE.search(clause))

    return Field(
        level=level,
        name=name,
        picture=picture,
        value=value,
        occurs=occurs,
        line=line,
        parent=parent if level == "88" else None,
        sign_separate=sign_separate,
        section=section,
    )


def _extract_fields_from_lines(lines: list[SourceLine]) -> list[Field]:
    """Parse data-item declarations from DATA DIVISION or copybook lines."""
    fields: list[Field] = []
    section: str | None = None
    last_data_name: str | None = None
    i = 0
    while i < len(lines):
        stripped = lines[i].text.strip()
        if not stripped:
            i += 1
            continue

        section_match = _SECTION_HEADER_RE.match(stripped)
        if section_match:
            section = section_match.group(1).upper()
            i += 1
            continue

        if _match_division(stripped):
            i += 1
            continue

        if not _is_field_start(stripped):
            i += 1
            continue

        start_line = lines[i].number
        clause = stripped
        i += 1
        while i < len(lines) and not _clause_ends_field(clause):
            nxt = lines[i].text.strip()
            if not nxt:
                i += 1
                continue
            if (
                _is_field_start(nxt)
                or _SECTION_HEADER_RE.match(nxt)
                or _match_division(nxt)
            ):
                break
            clause = f"{clause} {nxt}"
            i += 1

        field = _parse_field_clause(
            clause,
            line=start_line,
            section=section,
            parent=last_data_name,
        )
        if field is None:
            continue
        fields.append(field)
        if field.level != "88":
            last_data_name = field.name
    return fields


def _is_paragraph_header(line: SourceLine) -> str | None:
    """Return the paragraph name if ``line`` is a header in column 8.

    A paragraph name begins in column 8 (first character of the code area)
    and is a single word ending with a period, e.g. ``MAIN-LOGIC.``.
    """
    text = line.text
    # Column 8 == index 0 of the code area; Area B (indented) is not a header.
    if not text or text[0] in " \t":
        return None
    match = _PARAGRAPH_RE.match(text.rstrip())
    if not match:
        return None
    name = match.group(1).upper()
    if name in _SKIP_PARAGRAPH_NAMES:
        return None
    if name.endswith("-DIVISION") or name.endswith("-SECTION"):
        return None
    return name


def _extract_paragraphs(procedure: Division | None) -> list[Paragraph]:
    """List PROCEDURE DIVISION paragraphs with start/end file line numbers.

    Each paragraph starts on its header line and ends on the line before the
    next paragraph header (or at the end of the PROCEDURE DIVISION).
    """
    if procedure is None:
        return []

    # Drop the PROCEDURE DIVISION header line itself
    body_lines = procedure.lines[1:] if procedure.lines else []
    headers: list[tuple[int, str]] = []
    for i, line in enumerate(body_lines):
        name = _is_paragraph_header(line)
        if name is not None:
            headers.append((i, name))

    paragraphs: list[Paragraph] = []
    for i, (start_i, name) in enumerate(headers):
        start_line = body_lines[start_i].number
        if i + 1 < len(headers):
            # Ends where the next paragraph starts
            end_line = body_lines[headers[i + 1][0]].number - 1
            end_i = headers[i + 1][0] - 1
        else:
            end_line = procedure.end_line
            end_i = len(body_lines) - 1
        chunk = body_lines[start_i : end_i + 1]
        body = "\n".join(sl.text.rstrip() for sl in chunk[1:]).strip()
        paragraphs.append(
            Paragraph(
                name=name,
                start_line=start_line,
                end_line=end_line,
                body=body,
            )
        )
    return paragraphs


def _extract_copies(lines: list[SourceLine]) -> list[CopyRef]:
    refs: list[CopyRef] = []
    seen: set[tuple[str, int]] = set()
    for line in lines:
        for match in _COPY_RE.finditer(line.text):
            name = match.group(1).upper()
            key = (name, line.number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(CopyRef(name=name, line=line.number))
    return refs


def _extract_calls(lines: list[SourceLine]) -> list[CallRef]:
    refs: list[CallRef] = []
    seen: set[tuple[str, int]] = set()
    for line in lines:
        for match in _CALL_RE.finditer(line.text):
            name = (match.group(1) or match.group(2) or match.group(3) or "").upper()
            if not name:
                continue
            key = (name, line.number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(CallRef(name=name, line=line.number))
    return refs


def _paragraph_at(paragraphs: list[Paragraph], line_no: int) -> str | None:
    """Return the paragraph that contains ``line_no``, if any."""
    for paragraph in paragraphs:
        if paragraph.start_line <= line_no <= paragraph.end_line:
            return paragraph.name
    return None


def _extract_performs(
    lines: list[SourceLine], paragraphs: list[Paragraph]
) -> list[PerformRef]:
    """Collect ``PERFORM name`` / ``PERFORM a THRU b`` (skip loop forms)."""
    refs: list[PerformRef] = []
    seen: set[tuple[str, str | None, int]] = set()
    for line in lines:
        for match in _PERFORM_RE.finditer(line.text):
            name = match.group(1).upper()
            if name in _PERFORM_LOOP_STARTERS or name.isdigit():
                continue
            thru = match.group(2).upper() if match.group(2) else None
            key = (name, thru, line.number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(
                PerformRef(
                    caller=_paragraph_at(paragraphs, line.number),
                    name=name,
                    thru=thru,
                    line=line.number,
                )
            )
    return refs


def parse_program(name: str, text: str) -> ParsedProgram:
    """Parse fixed-format COBOL text into a ``ParsedProgram``.

    Works on programs (``.cbl`` / ``.cob``) and copybooks (``.cpy``). Copybooks
    have no divisions; their field lines are parsed directly.

    Args:
        name: Program/file name (e.g. ``BANKMAIN.cbl`` or ``ACCTDEF.cpy``).
            Used as a fallback when ``PROGRAM-ID`` is missing.
        text: Full source text. Never executed.

    Returns:
        Structured divisions, fields, paragraphs, COPY, CALL, and PERFORM
        references with original file line numbers.
    """
    lines = _physical_lines(text)
    divisions = _split_divisions(lines)
    program_id = _extract_program_id(lines, name)
    data = _division_by_name(divisions, "DATA")
    procedure = _division_by_name(divisions, "PROCEDURE")

    # Programs: fields live in DATA DIVISION. Copybooks: whole file is data.
    if data is not None:
        field_lines = data.lines
    else:
        field_lines = lines

    paragraphs = _extract_paragraphs(procedure)
    return ParsedProgram(
        name=name,
        program_id=program_id,
        divisions=divisions,
        fields=_extract_fields_from_lines(field_lines),
        paragraphs=paragraphs,
        copies=_extract_copies(lines),
        calls=_extract_calls(lines),
        performs=_extract_performs(lines, paragraphs),
    )
