"""Translate a small, explicit subset of COBOL into draft Python.

Supported:

- ``WORKING-STORAGE`` fields at level ``01`` or ``77`` with ``PIC X``/``PIC X(n)``
  (text) or ``PIC 9``/``PIC 9(n)`` (whole numbers), with an optional ``VALUE``.
- ``DISPLAY``, ``MOVE ... TO``, ``ADD ... TO``, ``SUBTRACT ... FROM``, ``STOP RUN``.

Every other line in ``WORKING-STORAGE`` or the ``PROCEDURE DIVISION`` becomes a
``# TODO`` comment and a review note. Statements that mix text and numbers, or
use decimals, also go to review, so the generated Python never fails with a
type error. New statement rules go in ``translate_statement``.

The entry point is ``translate_program``; the other functions each handle one
piece of it.
"""

import builtins
import keyword
import re
from typing import NamedTuple

from legacylift.errors import ConversionError
from legacylift.models import PythonDraft

PROGRAM_ID = re.compile(r"\bPROGRAM-ID\s*\.\s*([A-Z][A-Z0-9-]*)", re.IGNORECASE)
PROCEDURE_DIVISION = re.compile(r"\bPROCEDURE\s+DIVISION\b", re.IGNORECASE)
# A field entry: level, name, picture, and an optional VALUE.
FIELD_ENTRY = re.compile(
    r"^(?:01|77)\s+([A-Z][A-Z0-9-]*)\s+PIC\s+(X|9)(?:\(\d+\))?(?:\s+VALUE\s+(.+))?$",
    re.IGNORECASE,
)
# One DISPLAY item: a quoted string, a number, or a name.
DISPLAY_ITEM = re.compile(r'"[^"]*"|\'[^\']*\'|[-+]?\d+(?:\.\d+)?|[A-Z][A-Z0-9-]*', re.IGNORECASE)
WHOLE_NUMBER = re.compile(r"[-+]?\d+")
# The assignment verbs: COBOL verb, the word before the target, Python operator.
ASSIGNMENTS = (("MOVE", "TO", "="), ("ADD", "TO", "+="), ("SUBTRACT", "FROM", "-="))
# Names a field must not take: Python keywords, built-ins like print, and main().
RESERVED_NAMES = set(keyword.kwlist) | set(dir(builtins)) | {"main"}


class Value(NamedTuple):
    """A COBOL value or field, translated to Python.

    Attributes:
        code: Python source, such as ``'Hi'``, ``5``, or ``ws_total``.
        is_number: ``True`` for whole numbers, ``False`` for text.
    """

    code: str
    is_number: bool


def clean_line(raw_line: str) -> str:
    """Strip one raw COBOL line down to its code.

    Fixed-format COBOL keeps sequence numbers in columns 1-6 and a comment
    marker (``*`` or ``/``) in column 7. Free-format comments start with ``*>``.

    Args:
        raw_line: One line exactly as it appears in the file.

    Returns:
        The code with surrounding spaces removed, or ``""`` for comments.

    Example:
        >>> clean_line("000100 DISPLAY 'HI'.")
        "DISPLAY 'HI'."
        >>> clean_line("000200*This line is a comment")
        ''
        >>> clean_line("    *> So is this one")
        ''
    """
    sequence_area = raw_line[:6].strip()
    if len(raw_line) > 6 and (not sequence_area or sequence_area.isdigit()):
        if raw_line[6] in "*/":
            return ""
        if raw_line[6] == " ":
            raw_line = raw_line[7:]
    line = raw_line.strip()
    return "" if line.startswith("*>") else line


def variable_name(cobol_name: str) -> str:
    """Turn a COBOL data name into a Python variable name.

    Args:
        cobol_name: A COBOL name such as ``WS-TOTAL``.

    Returns:
        Lowercase with ``_`` for ``-``. Names that would hide a Python keyword
        or built-in (such as ``print``) get a trailing ``_``.

    Example:
        >>> variable_name("WS-TOTAL")
        'ws_total'
        >>> variable_name("PRINT")
        'print_'
    """
    name = cobol_name.lower().replace("-", "_")
    return f"{name}_" if name in RESERVED_NAMES else name


def translate_value(text: str, fields: dict[str, Value]) -> Value | None:
    """Translate one COBOL value: a literal, ``ZERO``/``SPACES``, or a field name.

    Args:
        text: The value as written in COBOL.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        The translated value, or ``None`` for anything unsupported, such as a
        decimal, an expression, or an undeclared field.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", is_number=True)}
        >>> translate_value('"Hi"', fields)
        Value(code="'Hi'", is_number=False)
        >>> translate_value("007", fields)
        Value(code='7', is_number=True)
        >>> translate_value("ws-total", fields)
        Value(code='ws_total', is_number=True)
        >>> translate_value("1.5", fields) is None
        True
    """
    text = text.strip()
    upper = text.upper()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
        return Value(repr(text[1:-1]), is_number=False)
    if WHOLE_NUMBER.fullmatch(text):
        return Value(str(int(text)), is_number=True)  # int() drops leading zeros
    if upper in {"ZERO", "ZEROS", "ZEROES"}:
        return Value("0", is_number=True)
    if upper in {"SPACE", "SPACES"}:
        return Value("''", is_number=False)
    return fields.get(upper)


def translate_field(line: str, fields: dict[str, Value]) -> str | None:
    """Translate one ``WORKING-STORAGE`` entry and remember the field.

    Args:
        line: The entry after ``clean_line``, without its final period.
        fields: Declared fields so far. A supported field is added to it.

    Returns:
        A Python assignment, or ``None`` if the entry is not supported or its
        ``VALUE`` does not fit the picture (text in a number, or the reverse).

    Example:
        >>> fields = {}
        >>> translate_field("01 WS-TOTAL PIC 9(4) VALUE 10", fields)
        'ws_total = 10'
        >>> translate_field("01 WS-NAME PIC X(10)", fields)
        "ws_name = ''"
        >>> translate_field('01 WS-COUNT PIC 9 VALUE "ten"', fields) is None
        True
        >>> sorted(fields)
        ['WS-NAME', 'WS-TOTAL']
    """
    match = FIELD_ENTRY.fullmatch(line)
    if match is None:
        return None
    cobol_name, picture, initial_text = match.groups()
    is_number = picture == "9"
    if initial_text is None:
        initial: Value | None = Value("0" if is_number else "''", is_number)
    else:
        initial = translate_value(initial_text, fields)
    if initial is None or initial.is_number != is_number:
        return None
    variable = variable_name(cobol_name)
    fields[cobol_name.upper()] = Value(variable, is_number)
    return f"{variable} = {initial.code}"


def translate_statement(line: str, fields: dict[str, Value]) -> str | None:
    """Translate one ``PROCEDURE DIVISION`` statement into one Python statement.

    Args:
        line: The statement after ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        One line of Python, or ``None`` if the statement is not supported.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", True)}
        >>> translate_statement("ADD 5 TO WS-TOTAL", fields)
        'ws_total += 5'
        >>> translate_statement("STOP RUN", fields)
        'return'
        >>> translate_statement("PERFORM PRINT-TOTAL", fields) is None
        True
    """
    upper = line.upper()
    if upper == "STOP RUN":
        return "return"
    if upper.startswith("DISPLAY "):
        return translate_display(line[len("DISPLAY ") :], fields)
    return translate_assignment(line, fields)


def translate_display(items_text: str, fields: dict[str, Value]) -> str | None:
    """Translate the items after ``DISPLAY`` into a ``print`` call.

    Args:
        items_text: Everything after the word ``DISPLAY``.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        A ``print(..., sep='')`` call, or ``None`` if an item is not a literal
        or a declared field (an expression, for example).

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", True)}
        >>> translate_display('"Total: " WS-TOTAL', fields)
        "print('Total: ', ws_total, sep='')"
        >>> translate_display("WS-TOTAL + 1", fields) is None
        True
    """
    items_text = items_text.strip()
    items = DISPLAY_ITEM.findall(items_text)
    if not items or DISPLAY_ITEM.sub("", items_text).strip():
        return None  # something other than literals and names
    codes = []
    for item in items:
        value = translate_value(item, fields)
        if value is None:
            return None
        codes.append(value.code)
    return f"print({', '.join(codes)}, sep='')"


def translate_assignment(line: str, fields: dict[str, Value]) -> str | None:
    """Translate ``MOVE x TO y``, ``ADD x TO y``, or ``SUBTRACT x FROM y``.

    ``MOVE`` needs a value of the same type as its target. ``ADD`` and
    ``SUBTRACT`` need numbers on both sides.

    Args:
        line: The statement after ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        A Python assignment such as ``ws_total += 5``, or ``None`` if the
        statement is not one of the three or the types do not fit.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", True), "WS-NAME": Value("ws_name", False)}
        >>> translate_assignment("SUBTRACT 2 FROM WS-TOTAL", fields)
        'ws_total -= 2'
        >>> translate_assignment('MOVE "abc" TO WS-TOTAL', fields) is None
        True
    """
    for verb, target_word, operator in ASSIGNMENTS:
        match = re.fullmatch(
            rf"{verb}\s+(.+?)\s+{target_word}\s+([A-Z][A-Z0-9-]*)", line, re.IGNORECASE
        )
        if match is None:
            continue
        value_text, target_name = match.groups()
        value = translate_value(value_text, fields)
        target = fields.get(target_name.upper())
        if value is None or target is None or value.is_number != target.is_number:
            return None
        if verb != "MOVE" and not target.is_number:
            return None  # ADD and SUBTRACT need numbers
        return f"{target.code} {operator} {value.code}"
    return None


def translate_program(source: str) -> PythonDraft:
    """Translate one COBOL program into a Python draft.

    Lines before ``WORKING-STORAGE SECTION`` are skipped. After it, every line
    becomes Python or a ``# TODO`` comment with a review note.

    Args:
        source: The full text of one ``.cbl`` or ``.cob`` file.

    Returns:
        The program name, the generated script, and the review notes.

    Raises:
        ConversionError: If the source has no ``PROGRAM-ID`` or ``PROCEDURE DIVISION``.

    Example:
        >>> draft = translate_program('''PROGRAM-ID. TAX.
        ... WORKING-STORAGE SECTION.
        ... 01 WS-TOTAL PIC 9(4) VALUE 10.
        ... PROCEDURE DIVISION.
        ... ADD 5 TO WS-TOTAL.
        ... PERFORM PRINT-TOTAL.
        ... STOP RUN.''')
        >>> draft.program_name, draft.notes
        ('TAX', ['Line 6: PERFORM PRINT-TOTAL'])
        >>> print(draft.python)
        # Draft conversion of TAX. Review TODO lines before use.
        def main():
            ws_total = 10
            ws_total += 5
            # TODO: COBOL line 6: PERFORM PRINT-TOTAL
            return
        <BLANKLINE>
        <BLANKLINE>
        if __name__ == '__main__':
            main()
        <BLANKLINE>
    """
    numbered_lines = [
        (number, clean_line(raw_line).removesuffix("."))
        for number, raw_line in enumerate(source.splitlines(), start=1)
    ]
    all_code = "\n".join(line for _, line in numbered_lines)
    program_id = PROGRAM_ID.search(all_code)
    if program_id is None or not PROCEDURE_DIVISION.search(all_code):
        raise ConversionError("File needs PROGRAM-ID and PROCEDURE DIVISION.")

    fields: dict[str, Value] = {}
    body: list[str] = []
    notes: list[str] = []
    section = ""  # becomes "storage", then "procedure"
    for number, line in numbered_lines:
        upper = line.upper()
        if upper == "WORKING-STORAGE SECTION":
            section = "storage"
        elif upper.startswith("PROCEDURE DIVISION"):
            section = "procedure"
        elif line and section:
            if section == "storage":
                translated = translate_field(line, fields)
            else:
                translated = translate_statement(line, fields)
            if translated is None:
                body.append(f"# TODO: COBOL line {number}: {line}")
                notes.append(f"Line {number}: {line}")
            else:
                body.append(translated)

    program_name = program_id.group(1)
    return PythonDraft(
        program_name=program_name, python=build_script(program_name, body), notes=notes
    )


def build_script(program_name: str, body: list[str]) -> str:
    """Wrap translated lines in a runnable script with a ``main()`` function.

    Args:
        program_name: Used in the header comment.
        body: Python lines and ``# TODO`` comments, not yet indented.

    Returns:
        The full script. ``pass`` is added if the body has no real statements.

    Example:
        >>> print(build_script("EMPTY", []))
        # Draft conversion of EMPTY. Review TODO lines before use.
        def main():
            pass
        <BLANKLINE>
        <BLANKLINE>
        if __name__ == '__main__':
            main()
        <BLANKLINE>
    """
    if all(line.startswith("#") for line in body):
        body = [*body, "pass"]
    return "\n".join(
        [
            f"# Draft conversion of {program_name}. Review TODO lines before use.",
            "def main():",
            *(f"    {line}" for line in body),
            "",
            "",
            "if __name__ == '__main__':",
            "    main()",
            "",
        ]
    )
