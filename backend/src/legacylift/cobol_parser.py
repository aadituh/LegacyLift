"""
COBOL preprocessing used by the notebooks and the web conversion pipeline.

Extracts:
  - PROGRAM-ID
  - DATA DIVISION items (potential class attributes)
  - PROCEDURE DIVISION paragraphs (potential methods)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Union

CobolSource = Union[str, Path]

# Division / section headers are not executable paragraphs
_SKIP_PARAGRAPH_NAMES = {
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

_FIELD_RE = re.compile(
    r"^\s*(0[1-9]|[1-4]\d)\s+([A-Z0-9][A-Z0-9-]*)\s+.*?PIC\s+([\w()V+\-]+)",
    re.IGNORECASE | re.MULTILINE,
)

_PARAGRAPH_RE = re.compile(
    r"(?m)^(?!\s)"  # start of line, not indented
    r"([A-Z][A-Z0-9-]*)\."  # paragraph name ending with .
    r"[ \t]*\r?\n"  # rest of line
    r"((?:(?!^[A-Z][A-Z0-9-]*\.).)*)",  # body until next paragraph
    re.IGNORECASE | re.DOTALL,
)


def _normalize_source(source: str) -> str:
    """Strip fixed-form sequence numbers / comment indicator when present."""
    lines: List[str] = []
    for raw in source.splitlines():
        line = raw.rstrip("\n")
        # Fixed-form only: columns 1-6 are a pure digit sequence number
        if len(line) >= 7 and line[:6].isdigit():
            indicator = line[6]
            line = line[7:] if indicator in {" ", "*", "/", "-"} else line[6:]
            if indicator == "*":
                continue
        stripped = line.lstrip()
        if stripped.startswith("*"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _extract_program_name(content: str) -> str:
    match = re.search(r"PROGRAM-ID\.\s*([A-Z0-9-]+)", content, re.IGNORECASE)
    return match.group(1).upper() if match else "UNKNOWN"


def _extract_fields(content: str) -> List[Dict[str, str]]:
    fields: List[Dict[str, str]] = []
    seen = set()
    for match in _FIELD_RE.finditer(content):
        name = match.group(2).upper()
        pic = (match.group(3) or "X").upper()
        if name in {"FILLER"} or name in seen:
            continue
        seen.add(name)
        fields.append({"name": name, "pic": pic})
    return fields


def _procedure_section(content: str) -> str:
    match = re.search(
        r"PROCEDURE\s+DIVISION[^\n]*\.\s*(.*)\Z",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else content


def _extract_paragraphs(content: str) -> List[Tuple[str, str]]:
    proc = _procedure_section(content)
    paragraphs: List[Tuple[str, str]] = []
    for match in _PARAGRAPH_RE.finditer(proc):
        name = match.group(1).upper()
        body = match.group(2).strip()
        if name in _SKIP_PARAGRAPH_NAMES:
            continue
        if name.endswith("-DIVISION") or name.endswith("-SECTION"):
            continue
        paragraphs.append((name, body))
    return paragraphs


def parse_cobol_source(source: str) -> Dict:
    """
    Parse COBOL text into the structure used by notebooks and the refactorer.

    Returns
    -------
    dict
        program_name, potential_attributes, potential_methods, raw_paragraphs
    """
    normalized = _normalize_source(source)
    content_upper = normalized.upper()

    fields = _extract_fields(content_upper)
    paragraphs = _extract_paragraphs(content_upper)

    return {
        "program_name": _extract_program_name(content_upper),
        "potential_attributes": fields,
        "potential_methods": [name for name, _ in paragraphs],
        "raw_paragraphs": paragraphs,
        "source": normalized,
    }


def parse_cobol(file_path: CobolSource) -> Dict:
    """
    Parse a COBOL file from disk (notebook / CLI entry point).

    Parameters
    ----------
    file_path:
        Path to a ``.cbl`` / ``.cob`` file.
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    result = parse_cobol_source(text)
    result["file_path"] = str(path)
    return result
