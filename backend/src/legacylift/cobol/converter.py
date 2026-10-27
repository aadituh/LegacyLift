"""Translate a practical subset of COBOL into draft Python that runs.

Supported (WORKING-STORAGE and PROCEDURE DIVISION)
-------------------------------------------------
**Data items**

- Elementary fields at levels ``01``–``49`` and ``77`` with:
  - text: ``PIC X``, ``XX``, ``X(n)``
  - whole numbers: ``PIC 9``, ``99``, ``9(n)``, optional leading ``S``
  - decimals: ``PIC …V…`` (e.g. ``99V99``, ``S9(10)V99``) as Python ``float``
- Optional ``VALUE`` (literals, ``ZERO``/``ZEROS``, ``SPACE``/``SPACES``).
- Text literals may use doubled quotes (``"It""s"``).
- Group headers (level + name, no ``PIC``) are skipped (structure only).

**Procedure**

- ``DISPLAY`` items (literals and declared fields)
- ``MOVE … TO …``, ``ADD … TO …``, ``SUBTRACT … FROM …``
- ``MULTIPLY … BY …``, ``DIVIDE … INTO …`` (no ``GIVING``)
- ``COMPUTE name =`` expression with ``+ - * /``, numbers, field names, ``( )``
- Paragraph headers (``NAME.``) become nested functions inside ``main()``
- ``PERFORM name`` / ``PERFORM a THRU b`` call those functions
- ``STOP RUN`` → ``return`` (exits the current paragraph or ``main``)

Unsupported lines become ``# TODO`` comments and review notes so the draft
still runs. ``LINKAGE`` and other post-storage data sections stay as notes.

How it works: ``translate_program`` (called from ``services.conversion``)
cleans each line, classifies storage vs procedure, builds fields and
paragraph bodies, then ``build_script`` wraps them in ``main()``. After
conversion, ``run_and_verify_python`` can check stdout.

Outside the sample bank, typical gaps before this expansion were group
``05`` fields, ``PIC …V…``, paragraphs/``PERFORM``, and ``COMPUTE`` — those
are what ``employee_payroll.cbl`` and ``simple_account.cbl`` needed.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import keyword
import re
import traceback
from typing import NamedTuple

from legacylift.errors import ConversionError
from legacylift.models import PythonDraft

PROGRAM_ID = re.compile(r"\bPROGRAM-ID\s*\.\s*([A-Z][A-Z0-9-]*)", re.IGNORECASE)
PROCEDURE_DIVISION = re.compile(r"\bPROCEDURE\s+DIVISION\b", re.IGNORECASE)

# Elementary item: level, name, PIC, optional VALUE.
FIELD_ENTRY = re.compile(
    r"^(0[1-9]|[1-4]\d|77)\s+([A-Z][A-Z0-9-]*)\s+"
    r"PIC\s+(S?9+(?:\(\d+\))?(?:V9+(?:\(\d+\))?)?|X+(?:\(\d+\))?)"
    r"(?:\s+VALUE\s+(.+))?$",
    re.IGNORECASE,
)
# Group item: level + name only (no PIC).
GROUP_ENTRY = re.compile(
    r"^(0[1-9]|[1-4]\d)\s+([A-Z][A-Z0-9-]*)$",
    re.IGNORECASE,
)

TEXT_LITERAL = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'')
DISPLAY_ITEM = re.compile(
    rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?|[A-Z][A-Z0-9-]*", re.IGNORECASE
)
WHOLE_NUMBER = re.compile(r"[-+]?\d+")
DECIMAL_NUMBER = re.compile(r"[-+]?\d+\.\d+")
FIELD_NAME = re.compile(r"[A-Z][A-Z0-9-]*", re.IGNORECASE)
COMPUTE_STMT = re.compile(
    r"^COMPUTE\s+([A-Z][A-Z0-9-]*)\s*=\s*(.+)$",
    re.IGNORECASE,
)
# Safe COMPUTE right-hand side tokens only.
COMPUTE_TOKEN = re.compile(
    rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?|[A-Z][A-Z0-9-]*|[()+*/\-]",
    re.IGNORECASE,
)
PERFORM_STMT = re.compile(
    r"^PERFORM\s+([A-Z][A-Z0-9-]*)"
    r"(?:\s+(?:THRU|THROUGH)\s+([A-Z][A-Z0-9-]*))?$",
    re.IGNORECASE,
)
MULTIPLY_STMT = re.compile(
    r"^MULTIPLY\s+(.+?)\s+BY\s+([A-Z][A-Z0-9-]*)$",
    re.IGNORECASE,
)
DIVIDE_STMT = re.compile(
    r"^DIVIDE\s+(.+?)\s+INTO\s+([A-Z][A-Z0-9-]*)$",
    re.IGNORECASE,
)

ASSIGNMENT_OPERATORS = {
    ("MOVE", "TO"): "=",
    ("ADD", "TO"): "+=",
    ("SUBTRACT", "FROM"): "-=",
}
RESERVED_NAMES = set(keyword.kwlist) | set(dir(builtins)) | {"main"}
PERFORM_LOOP_STARTERS = frozenset({"UNTIL", "VARYING", "WITH", "TEST"})


class Value(NamedTuple):
    """A COBOL value or field, translated to Python.

    Attributes:
        code: Python source, such as ``'Hi'``, ``5``, or ``ws_total``.
        is_number: ``True`` for int/float numerics, ``False`` for text.
        is_float: ``True`` when the picture (or literal) is decimal.
    """

    code: str
    is_number: bool
    is_float: bool = False


class VerificationResult(NamedTuple):
    """Outcome of compiling, running, and checking generated Python.

    Attributes:
        passed: ``True`` only when the script is valid, runs cleanly, and
            stdout equals ``expected_output`` exactly.
        stdout: Text printed to standard output (empty if it never ran).
        error: ``None`` on success; otherwise a short syntax, runtime, or
            output-mismatch message.
    """

    passed: bool
    stdout: str
    error: str | None


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
    """Turn a COBOL data or paragraph name into a Python identifier.

    Args:
        cobol_name: A COBOL name such as ``WS-TOTAL`` or ``MAIN-PROC``.

    Returns:
        Lowercase with ``_`` for ``-``. Names that would hide a Python keyword
        or built-in (such as ``print``) get a trailing ``_``.

    Example:
        >>> variable_name("WS-TOTAL")
        'ws_total'
        >>> variable_name("PRINT")
        'print_'
        >>> variable_name("MAIN-PROC")
        'main_proc'
    """
    name = cobol_name.lower().replace("-", "_")
    return f"{name}_" if name in RESERVED_NAMES else name


def picture_is_float(picture: str) -> bool:
    """Return whether a PIC clause describes a decimal (contains ``V``)."""
    return "V" in picture.upper()


def translate_value(text: str, fields: dict[str, Value]) -> Value | None:
    """Translate one COBOL value: a literal, ``ZERO``/``SPACES``, or a field name.

    Args:
        text: The value as written in COBOL.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        The translated value, or ``None`` for anything unsupported (an
        expression, or an undeclared field).

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", is_number=True)}
        >>> translate_value('"Hi"', fields)
        Value(code="'Hi'", is_number=False, is_float=False)
        >>> print(translate_value('"It""s"', fields).code)
        'It"s'
        >>> translate_value("007", fields)
        Value(code='7', is_number=True, is_float=False)
        >>> translate_value("1.5", fields)
        Value(code='1.5', is_number=True, is_float=True)
        >>> translate_value("ws-total", fields)
        Value(code='ws_total', is_number=True, is_float=False)
    """
    text = text.strip()
    upper = text.upper()
    if TEXT_LITERAL.fullmatch(text):
        quote = text[0]
        return Value(repr(text[1:-1].replace(quote * 2, quote)), is_number=False)
    if DECIMAL_NUMBER.fullmatch(text):
        return Value(str(float(text)), is_number=True, is_float=True)
    if WHOLE_NUMBER.fullmatch(text):
        return Value(str(int(text)), is_number=True)
    if upper in {"ZERO", "ZEROS", "ZEROES"}:
        return Value("0", is_number=True)
    if upper in {"SPACE", "SPACES"}:
        return Value("''", is_number=False)
    return fields.get(upper)


def _types_compatible(value: Value, target: Value) -> bool:
    """MOVE/ADD targets: both text, or both numeric (no decimal into whole PIC)."""
    if value.is_number != target.is_number:
        return False
    return not (value.is_float and target.is_number and not target.is_float)


def translate_field(line: str, fields: dict[str, Value]) -> str | None:
    """Translate one WORKING-STORAGE entry and remember the field.

    Group items (no PIC) return an empty string so the caller omits them
    without a review note. Unsupported pictures or type-mismatched VALUEs
    return None (review note).

    Args:
        line: The entry after ``clean_line``, without its final period.
        fields: Declared fields so far. A supported field is added to it.

    Returns:
        A Python assignment, an empty string for a group header, or ``None``.

    Example:
        >>> fields = {}
        >>> translate_field("01 WS-TOTAL PIC 9(4) VALUE 10", fields)
        'ws_total = 10'
        >>> translate_field("01 WS-NAME PIC X(10)", fields)
        "ws_name = ''"
        >>> translate_field("05 HOURS-WORKED PIC 99V99", fields)
        'hours_worked = 0.0'
        >>> translate_field("01 EMPLOYEE", fields)
        ''
        >>> translate_field('01 WS-COUNT PIC 9 VALUE "ten"', fields) is None
        True
        >>> sorted(fields)
        ['HOURS-WORKED', 'WS-NAME', 'WS-TOTAL']
    """
    group = GROUP_ENTRY.fullmatch(line)
    if group is not None:
        return ""

    match = FIELD_ENTRY.fullmatch(line)
    if match is None:
        return None
    _level, cobol_name, picture, initial_text = match.groups()
    is_float = picture_is_float(picture)
    is_number = picture.upper().lstrip("S")[0] == "9"
    initial: Value | None
    if initial_text is None:
        if is_number:
            initial = Value("0.0" if is_float else "0", True, is_float)
        else:
            initial = Value("''", False)
    else:
        initial = translate_value(initial_text, fields)
    if initial is None or initial.is_number != is_number:
        return None
    # Whole-number PIC must not take a decimal VALUE.
    if is_number and not is_float and initial.is_float:
        return None
    variable = variable_name(cobol_name)
    fields[cobol_name.upper()] = Value(variable, is_number, is_float)
    code = initial.code
    if is_float and initial.is_number and not initial.is_float:
        code = "0.0" if initial.code == "0" else str(float(initial.code))
    return f"{variable} = {code}"


def is_paragraph_header(line: str) -> bool:
    """True when the procedure line is a paragraph name (single word)."""
    return bool(FIELD_NAME.fullmatch(line))


def translate_perform(line: str, paragraph_order: list[str]) -> str | None:
    """Translate ``PERFORM name`` or ``PERFORM a THRU b`` into function calls.

    Targets must appear as paragraph headers in this program; otherwise the
    line stays a review note (avoids ``NameError`` on missing functions).
    """
    match = PERFORM_STMT.fullmatch(line.strip())
    if match is None:
        return None
    start = match.group(1).upper()
    if start in PERFORM_LOOP_STARTERS or start.isdigit():
        return None
    end = match.group(2).upper() if match.group(2) else None
    if end is None:
        if start not in paragraph_order:
            return None
        return f"{variable_name(start)}()"
    if start not in paragraph_order or end not in paragraph_order:
        return None
    i, j = paragraph_order.index(start), paragraph_order.index(end)
    if i > j:
        i, j = j, i
    calls = [f"{variable_name(name)}()" for name in paragraph_order[i : j + 1]]
    return "; ".join(calls)


def translate_compute(line: str, fields: dict[str, Value]) -> str | None:
    """Translate a simple ``COMPUTE name = expression``.

    Only ``+ - * /``, parentheses, numbers, and declared field names are
    allowed on the right-hand side.
    """
    match = COMPUTE_STMT.fullmatch(line.strip())
    if match is None:
        return None
    target_name, expression = match.group(1), match.group(2).strip()
    target = fields.get(target_name.upper())
    if target is None or not target.is_number:
        return None
    tokens = COMPUTE_TOKEN.findall(expression)
    if not tokens or COMPUTE_TOKEN.sub("", expression).strip():
        return None
    parts: list[str] = []
    for token in tokens:
        if token in {"+", "-", "*", "/", "(", ")"}:
            parts.append(token)
            continue
        value = translate_value(token, fields)
        if value is None or (value.is_number is False and not TEXT_LITERAL.fullmatch(token)):
            return None
        if not value.is_number:
            return None
        parts.append(value.code)
    return f"{target.code} = {''.join(parts)}"


def translate_multiply_divide(line: str, fields: dict[str, Value]) -> str | None:
    """Translate ``MULTIPLY x BY y`` (``y *= x``) or ``DIVIDE x INTO y`` (``y /= x``)."""
    multiply = MULTIPLY_STMT.fullmatch(line.strip())
    if multiply:
        value = translate_value(multiply.group(1), fields)
        target = fields.get(multiply.group(2).upper())
        if value is None or target is None or not value.is_number or not target.is_number:
            return None
        return f"{target.code} *= {value.code}"
    divide = DIVIDE_STMT.fullmatch(line.strip())
    if divide:
        value = translate_value(divide.group(1), fields)
        target = fields.get(divide.group(2).upper())
        if value is None or target is None or not value.is_number or not target.is_number:
            return None
        return f"{target.code} /= {value.code}"
    return None


def translate_statement(
    line: str,
    fields: dict[str, Value],
    paragraph_order: list[str] | None = None,
) -> str | None:
    """Translate one ``PROCEDURE DIVISION`` statement into one Python statement.

    Args:
        line: The statement after ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.
        paragraph_order: Paragraph names in source order (for ``PERFORM … THRU``).

    Returns:
        One line of Python, or ``None`` if the statement is not supported.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", True)}
        >>> translate_statement("ADD 5 TO WS-TOTAL", fields)
        'ws_total += 5'
        >>> translate_statement("STOP RUN", fields)
        'return'
        >>> translate_statement("PERFORM PRINT-TOTAL", fields, ["PRINT-TOTAL"])
        'print_total()'
        >>> translate_statement(
        ...     "COMPUTE WS-TOTAL = WS-TOTAL * 2",
        ...     {"WS-TOTAL": Value("ws_total", True)},
        ... )
        'ws_total = ws_total*2'
    """
    upper = line.upper()
    if upper == "STOP RUN":
        return "return"
    if upper.startswith("DISPLAY "):
        return translate_display(line[len("DISPLAY ") :], fields)
    if upper.startswith("PERFORM "):
        return translate_perform(line, paragraph_order or [])
    if upper.startswith("COMPUTE "):
        return translate_compute(line, fields)
    multiplied = translate_multiply_divide(line, fields)
    if multiplied is not None:
        return multiplied
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
        return None
    codes = []
    for item in items:
        value = translate_value(item, fields)
        if value is None:
            return None
        codes.append(value.code)
    return f"print({', '.join(codes)}, sep='')"


def translate_assignment(line: str, fields: dict[str, Value]) -> str | None:
    """Translate ``MOVE x TO y``, ``ADD x TO y``, or ``SUBTRACT x FROM y``.

    ``MOVE`` needs a value of the same broad type as its target (text vs
    number). ``ADD`` and ``SUBTRACT`` need numbers on both sides.

    Args:
        line: The statement after ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        A Python assignment such as ``ws_total += 5``, or ``None``.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", True), "WS-NAME": Value("ws_name", False)}
        >>> translate_assignment("SUBTRACT 2 FROM WS-TOTAL", fields)
        'ws_total -= 2'
        >>> translate_assignment('MOVE "GO  TO IT" TO WS-NAME', fields)
        "ws_name = 'GO  TO IT'"
        >>> translate_assignment('MOVE "abc" TO WS-TOTAL', fields) is None
        True
    """
    parts = line.rsplit(maxsplit=2)
    verb_and_value = parts[0].split(maxsplit=1) if len(parts) == 3 else []
    if len(verb_and_value) != 2:
        return None
    (verb, value_text), (_, target_word, target_name) = verb_and_value, parts
    operator = ASSIGNMENT_OPERATORS.get((verb.upper(), target_word.upper()))
    if operator is None or not FIELD_NAME.fullmatch(target_name):
        return None
    value = translate_value(value_text, fields)
    target = fields.get(target_name.upper())
    if value is None or target is None or not _types_compatible(value, target):
        return None
    if operator != "=" and not target.is_number:
        return None
    return f"{target.code} {operator} {value.code}"


def translate_line(
    section: str,
    line: str,
    fields: dict[str, Value],
    paragraph_order: list[str] | None = None,
) -> str | None:
    """Translate one line according to the section it is in.

    Args:
        section: ``storage``, ``procedure``, or ``other``.
        line: After ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.
        paragraph_order: For ``PERFORM … THRU`` expansion.

    Returns:
        Python code, an empty string to omit quietly, or ``None`` for review.

    Example:
        >>> translate_line("storage", "01 N PIC 9 VALUE 1", {})
        'n = 1'
        >>> translate_line("other", "01 LS-DAYS PIC 999", {}) is None
        True
    """
    if section == "storage":
        return translate_field(line, fields)
    if section == "procedure":
        return translate_statement(line, fields, paragraph_order)
    return None


def build_script(
    program_name: str,
    storage: list[str],
    preamble: list[str],
    paragraphs: list[tuple[str, list[str]]],
    field_vars: list[str],
) -> str:
    """Wrap storage, optional preamble, and paragraphs in a runnable ``main()``.

    Paragraphs become nested functions. When any exist, each gets
    ``nonlocal`` for every storage variable so assignments update ``main``'s
    locals. Execution runs the preamble, then calls the first paragraph when
    there was no preamble (normal COBOL style).

    Args:
        program_name: Used in the header comment.
        storage: Field assignments (and storage-section TODO comments).
        preamble: Procedure statements before the first paragraph.
        paragraphs: ``(COBOL_NAME, body_lines)`` in source order.
        field_vars: Python names of storage fields (for ``nonlocal``).

    Returns:
        The full script.

    Example:
        >>> print(build_script("EMPTY", [], [], [], []))
        # Draft conversion of EMPTY. Review TODO lines before use.
        def main():
            pass
        <BLANKLINE>
        <BLANKLINE>
        if __name__ == '__main__':
            main()
        <BLANKLINE>
    """
    body: list[str] = [*storage]
    nonlocal_names = ", ".join(field_vars)

    for cobol_name, lines in paragraphs:
        fn = variable_name(cobol_name)
        body.append(f"def {fn}():")
        chunk: list[str] = []
        if nonlocal_names:
            chunk.append(f"nonlocal {nonlocal_names}")
        usable = [line for line in lines if line != ""]
        chunk.extend(usable if usable else ["pass"])
        body.extend(f"    {line}" for line in chunk)

    if preamble:
        body.extend(preamble)
    elif paragraphs:
        body.append(f"{variable_name(paragraphs[0][0])}()")

    # Top-level statements inside main (not nested def lines or comments).
    top_level = [
        line
        for line in body
        if not line.startswith("#") and not line.startswith("def ") and not line.startswith("    ")
    ]
    if not top_level:
        body.append("pass")

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


def translate_program(source: str) -> PythonDraft:
    """Translate one COBOL program into a Python draft.

    Lines before ``WORKING-STORAGE SECTION`` are skipped. After it, every line
    becomes Python, is omitted (group headers), or becomes a ``# TODO`` with a
    review note.

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
        >>> draft.program_name
        'TAX'
        >>> any('PERFORM PRINT-TOTAL' in note for note in draft.notes)
        True
        >>> 'ws_total += 5' in draft.python
        True
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
    storage: list[str] = []
    preamble: list[str] = []
    paragraphs: list[tuple[str, list[str]]] = []
    current_body: list[str] | None = None
    notes: list[str] = []
    section = ""

    # First pass over procedure lines: collect paragraph order for THRU.
    paragraph_order: list[str] = []
    in_procedure = False
    for _, line in numbered_lines:
        upper = line.upper()
        if upper.startswith("PROCEDURE DIVISION"):
            in_procedure = True
            continue
        if in_procedure and line and is_paragraph_header(line):
            paragraph_order.append(upper)

    for number, line in numbered_lines:
        upper = line.upper()
        if upper == "WORKING-STORAGE SECTION":
            section = "storage"
            continue
        if upper.startswith("PROCEDURE DIVISION"):
            section = "procedure"
            continue
        if not line or not section:
            continue
        if section == "storage" and upper.endswith(" SECTION"):
            section = "other"

        if section == "procedure" and is_paragraph_header(line):
            current_body = []
            paragraphs.append((upper, current_body))
            continue

        translated = translate_line(section, line, fields, paragraph_order)
        if translated is None:
            todo = f"# TODO: COBOL line {number}: {line}"
            notes.append(f"Line {number}: {line}")
            if section == "storage" or section == "other":
                storage.append(todo)
            elif current_body is not None:
                current_body.append(todo)
            else:
                preamble.append(todo)
        elif translated == "":
            continue
        elif section == "storage":
            storage.append(translated)
        elif current_body is not None:
            current_body.append(translated)
        else:
            preamble.append(translated)

    field_vars = [value.code for value in fields.values()]
    program_name = program_id.group(1)
    return PythonDraft(
        program_name=program_name,
        python=build_script(program_name, storage, preamble, paragraphs, field_vars),
        notes=notes,
    )


def run_and_verify_python(python: str, expected_output: str) -> VerificationResult:
    r"""Compile and run generated Python; require stdout to match exactly.

    Steps:

    1. **Syntax** — ``compile`` the script; a ``SyntaxError`` fails the check.
    2. **Logic / runtime** — ``exec`` the script as ``__main__``; any exception
       fails the check (type errors, ``NameError``, etc.).
    3. **Output** — compare captured stdout to ``expected_output`` with an
       exact string match (including newlines).

    Args:
        python: Full generated script (for example ``draft.python``).
        expected_output: Exact text the program must print.

    Returns:
        A ``VerificationResult``. ``passed`` is ``True`` only when all three
        steps succeed.

    Example:
        >>> ok = run_and_verify_python(
        ...     "print('hi')\n",
        ...     "hi\n",
        ... )
        >>> ok.passed, ok.stdout, ok.error
        (True, 'hi\n', None)
        >>> bad = run_and_verify_python("print('hi')\n", "bye\n")
        >>> bad.passed, bad.stdout
        (False, 'hi\n')
        >>> broken = run_and_verify_python("def main(:\n    pass\n", "")
        >>> broken.passed, broken.error is not None
        (False, True)
    """
    try:
        compiled = compile(python, "<generated>", "exec")
    except SyntaxError as error:
        return VerificationResult(
            passed=False,
            stdout="",
            error=f"SyntaxError: {error.msg} (line {error.lineno})",
        )

    stdout_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(compiled, {"__name__": "__main__"})  # noqa: S102
    except Exception as error:  # noqa: BLE001 - report any runtime failure to the caller
        return VerificationResult(
            passed=False,
            stdout=stdout_buffer.getvalue(),
            error=(f"{type(error).__name__}: {error}\n{traceback.format_exc(limit=2).rstrip()}"),
        )

    stdout = stdout_buffer.getvalue()
    if stdout != expected_output:
        return VerificationResult(
            passed=False,
            stdout=stdout,
            error=(f"Output mismatch.\nExpected: {expected_output!r}\nActual:   {stdout!r}"),
        )
    return VerificationResult(passed=True, stdout=stdout, error=None)


def translate_and_verify(source: str, expected_output: str) -> VerificationResult:
    r"""Translate COBOL, then run and verify the generated Python output.

    Args:
        source: Full text of one COBOL program.
        expected_output: Exact stdout expected from the generated script.

    Returns:
        The same ``VerificationResult`` as ``run_and_verify_python``.

    Raises:
        ConversionError: If the COBOL source cannot be translated at all
            (missing ``PROGRAM-ID`` or ``PROCEDURE DIVISION``).

    Example:
        >>> result = translate_and_verify(
        ...     '''PROGRAM-ID. HI.
        ... WORKING-STORAGE SECTION.
        ... PROCEDURE DIVISION.
        ... DISPLAY "ok".
        ... STOP RUN.''',
        ...     "ok\n",
        ... )
        >>> result.passed
        True
    """
    draft = translate_program(source)
    return run_and_verify_python(draft.python, expected_output)
