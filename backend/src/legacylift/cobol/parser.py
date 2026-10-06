"""Fixed-format COBOL text parser: divisions, fields, paragraphs, COPY/CALL.

Reads source only — never compiles or runs the program. Column rules match
IBM fixed format:

* columns 1–6: sequence area (ignored)
* column 7: ``*`` / ``/`` comment, ``-`` continues the previous line, space = code
* columns 8+: Area A/B source text

Hand-off for the API and analyzer::

    parse_program(name, text) -> ParsedProgram
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

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

_FIELD_RE = re.compile(
    r"^(0[1-9]|[1-4]\d|66|77|88)\s+"
    r"([A-Z0-9][A-Z0-9-]*|FILLER)"
    r"(?:\s+.*?PIC(?:TURE)?\s+([\w()V+\-./]+))?",
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
    lines: list[SourceLine] = Field(default_factory=list)


class DataField(BaseModel):
    """A data-item declaration (level + name, optional PIC)."""

    name: str
    level: str
    pic: str | None = None
    line: int
    section: str | None = None


class Paragraph(BaseModel):
    """A PROCEDURE DIVISION paragraph and its body text."""

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


class ParsedProgram(BaseModel):
    """Structured view of one COBOL program for the API / analyzer."""

    name: str
    program_id: str
    divisions: list[Division] = Field(default_factory=list)
    fields: list[DataField] = Field(default_factory=list)
    paragraphs: list[Paragraph] = Field(default_factory=list)
    copies: list[CopyRef] = Field(default_factory=list)
    calls: list[CallRef] = Field(default_factory=list)


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

    # Free-format / truncated line: no sequence area
    stripped = line.lstrip()
    if stripped.startswith("*"):
        return None
    return " ", line


def _physical_lines(text: str) -> list[SourceLine]:
    """Map file text to non-comment code lines, applying ``-`` continuations.

    Continued fragments keep the *first* line's number for the merged text so
    statements stay anchored where they begin; each physical non-comment line
    still appears separately when it is not a continuation.
    """
    result: list[SourceLine] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        parsed = _code_area(raw)
        if parsed is None:
            continue
        indicator, code = parsed
        if indicator == "-" and result:
            # Continuation: append Area B text to the previous logical line
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
    # Stable order for callers that expect the usual COBOL sequence
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


def _extract_fields(data: Division | None) -> list[DataField]:
    if data is None:
        return []

    fields: list[DataField] = []
    section: str | None = None
    for line in data.lines:
        stripped = line.text.strip()
        if not stripped:
            continue

        section_match = _SECTION_HEADER_RE.match(stripped)
        if section_match:
            section = section_match.group(1).upper()
            continue

        field_match = _FIELD_RE.match(stripped)
        if not field_match:
            continue

        level = field_match.group(1)
        name = field_match.group(2).upper()
        pic = field_match.group(3)
        fields.append(
            DataField(
                name=name,
                level=level,
                pic=pic.upper() if pic else None,
                line=line.number,
                section=section,
            )
        )
    return fields


def _extract_paragraphs(procedure: Division | None) -> list[Paragraph]:
    if procedure is None:
        return []

    # Drop the PROCEDURE DIVISION header line itself
    body_lines = procedure.lines[1:] if procedure.lines else []
    headers: list[tuple[int, str]] = []
    for i, line in enumerate(body_lines):
        stripped = line.text.strip()
        match = _PARAGRAPH_RE.match(stripped)
        if not match:
            continue
        name = match.group(1).upper()
        if name in _SKIP_PARAGRAPH_NAMES:
            continue
        if name.endswith("-DIVISION") or name.endswith("-SECTION"):
            continue
        # Area A is code-area columns 0–3 (physical 8–11). Area B statements
        # like ``GOBACK.`` / ``END-PERFORM.`` start at column 4+.
        leading = len(line.text) - len(line.text.lstrip(" "))
        if leading > 3:
            continue
        headers.append((i, name))

    paragraphs: list[Paragraph] = []
    for i, (start_i, name) in enumerate(headers):
        end_i = headers[i + 1][0] - 1 if i + 1 < len(headers) else len(body_lines) - 1
        chunk = body_lines[start_i : end_i + 1]
        # Body excludes the paragraph-name line
        body = "\n".join(sl.text.rstrip() for sl in chunk[1:]).strip()
        paragraphs.append(
            Paragraph(
                name=name,
                start_line=chunk[0].number,
                end_line=chunk[-1].number,
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


def parse_program(name: str, text: str) -> ParsedProgram:
    """Parse fixed-format COBOL text into a ``ParsedProgram``.

    Args:
        name: Program/file name (e.g. ``BANKMAIN.cbl``). Used as a fallback
            when ``PROGRAM-ID`` is missing.
        text: Full source text. Never executed.

    Returns:
        Structured divisions, fields, paragraphs, COPY and CALL references
        with original file line numbers.
    """
    lines = _physical_lines(text)
    divisions = _split_divisions(lines)
    program_id = _extract_program_id(lines, name)
    data = _division_by_name(divisions, "DATA")
    procedure = _division_by_name(divisions, "PROCEDURE")

    return ParsedProgram(
        name=name,
        program_id=program_id,
        divisions=divisions,
        fields=_extract_fields(data),
        paragraphs=_extract_paragraphs(procedure),
        copies=_extract_copies(lines),
        calls=_extract_calls(lines),
    )
