"""Convert a small, explicit subset of COBOL into draft Python.

Unsupported lines become TODO comments in the output. This keeps the demo
honest while giving the team one place to add the next conversion rule.
"""

from __future__ import annotations

import keyword
import re

PROGRAM_ID = re.compile(r"\bPROGRAM-ID\s*\.\s*([A-Z][A-Z0-9-]*)", re.IGNORECASE)
PROCEDURE = re.compile(r"\bPROCEDURE\s+DIVISION\b", re.IGNORECASE)
# This first demo supports only flat text and whole-number fields.
FIELD = re.compile(
    r"^(?:01|77)\s+([A-Z][A-Z0-9-]*)\s+PIC\s+"
    r"(X(?:\(\d+\))?|9(?:\(\d+\))?)"
    r"(?:\s+VALUE\s+(.+))?$",
    re.IGNORECASE,
)
DISPLAY_PART = re.compile(
    r'"[^"]*"|\'[^\']*\'|[-+]?\d+(?:\.\d+)?|[A-Z][A-Z0-9-]*',
    re.IGNORECASE,
)
NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?$")


def clean_line(raw: str) -> str:
    """Remove fixed-form line numbers and full-line comments when present."""
    if len(raw) > 6 and (not raw[:6].strip() or raw[:6].strip().isdigit()):
        if raw[6] in "*/":
            return ""
        if raw[6] == " ":
            raw = raw[7:]
    line = raw.strip()
    return "" if line.startswith("*>") else line


def python_name(cobol_name: str) -> str:
    name = cobol_name.lower().replace("-", "_")
    return name + "_" if keyword.iskeyword(name) else name


def python_value(value: str, fields: dict[str, str]) -> str | None:
    """Read one literal or declared field, without guessing at expressions."""
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return repr(value[1:-1])
    if NUMBER.fullmatch(value):
        return value
    if value.upper() in {"ZERO", "ZEROS", "ZEROES"}:
        return "0"
    if value.upper() in {"SPACE", "SPACES"}:
        return "''"
    return fields.get(value.upper())


def convert_statement(line: str, fields: dict[str, str]) -> str | None:
    """Return one Python statement, or None for unsupported COBOL."""
    if line.upper().startswith("DISPLAY "):
        arguments = line[8:].strip()
        parts = DISPLAY_PART.findall(arguments)
        if not parts or DISPLAY_PART.sub("", arguments).strip():
            return None
        values = [python_value(part, fields) for part in parts]
        if any(value is None for value in values):
            return None
        return f"print({', '.join(values)}, sep='')"

    for verb, word, operator in (
        ("MOVE", "TO", "="),
        ("ADD", "TO", "+="),
        ("SUBTRACT", "FROM", "-="),
    ):
        match = re.fullmatch(
            rf"{verb}\s+(.+?)\s+{word}\s+([A-Z][A-Z0-9-]*)",
            line,
            re.IGNORECASE,
        )
        if match:
            value = python_value(match.group(1), fields)
            target = fields.get(match.group(2).upper())
            if value is not None and target is not None:
                return f"{target} {operator} {value}"
    return None


def convert_source(source: str) -> dict:
    """Return a program name, Python draft, and notes for one COBOL file."""
    lines = [
        (number, clean_line(raw).removesuffix("."))
        for number, raw in enumerate(source.splitlines(), start=1)
    ]
    cleaned_source = "\n".join(line for _, line in lines)
    name_match = PROGRAM_ID.search(cleaned_source)
    if not name_match or not PROCEDURE.search(cleaned_source):
        raise ValueError("File needs PROGRAM-ID and PROCEDURE DIVISION.")

    fields: dict[str, str] = {}
    body: list[str] = []
    notes: list[str] = []
    in_storage = False
    in_procedure = False
    has_code = False

    def needs_review(number: int, line: str) -> None:
        body.append(f"    # TODO: COBOL line {number}: {line}")
        notes.append(f"Line {number}: {line}")

    for number, line in lines:
        if not line:
            continue
        upper = line.upper()
        if upper == "WORKING-STORAGE SECTION":
            in_storage = True
            continue
        if upper.startswith("PROCEDURE DIVISION"):
            in_storage = False
            in_procedure = True
            continue

        # Data declarations become Python variables before procedure statements.
        if in_storage:
            match = FIELD.fullmatch(line)
            if match:
                cobol_name, picture, initial = match.groups()
                variable = python_name(cobol_name)
                fields[cobol_name.upper()] = variable
                value = python_value(initial, fields) if initial else None
                if initial and value is None:
                    needs_review(number, line)
                default = "''" if picture.upper().startswith("X") else "0"
                body.append(f"    {variable} = {value if value is not None else default}")
                has_code = True
            elif re.match(r"^(?:01|05|77)\b|^COPY\b", line, re.IGNORECASE):
                needs_review(number, line)
            continue

        if not in_procedure:
            continue
        if upper == "STOP RUN":
            body.append("    return")
            has_code = True
            continue
        converted = convert_statement(line, fields)
        if converted is None:
            needs_review(number, line)
        else:
            body.append(f"    {converted}")
            has_code = True

    if not has_code:
        body.append("    pass")
    python_code = "\n".join([
        f"# Draft conversion of {name_match.group(1)}. Review TODO lines before use.",
        "def main():",
        *body,
        "",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ])
    return {"program_name": name_match.group(1), "python": python_code, "notes": notes}
