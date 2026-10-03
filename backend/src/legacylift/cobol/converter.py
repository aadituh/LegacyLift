"""Translate a small, explicit subset of COBOL into draft Python.

Supported:

- ``WORKING-STORAGE`` fields at level ``01`` or ``77`` with ``PIC X``, ``XX``,
  ``X(n)`` (text) or ``PIC 9``, ``99``, ``9(n)`` (whole numbers), with an
  optional ``VALUE``. Text literals may use doubled quotes (``"It""s"``).
- ``DISPLAY``, ``MOVE ... TO``, ``ADD ... TO``, ``SUBTRACT ... FROM``, ``STOP RUN``.

Every other line in ``WORKING-STORAGE``, a later data section such as
``LINKAGE``, or the ``PROCEDURE DIVISION`` becomes a ``# TODO`` comment and a
review note. Statements that mix text and numbers, or use decimals, also go to
review, so the generated Python never fails with a type error.

How it works: ``translate_program`` (the entry point, called by
``services.conversion.convert_file``) reads the program one line at a time.
``clean_line`` strips line numbers and comments. ``translate_line`` sends each
line to ``translate_field`` (storage) or ``translate_statement`` (procedure),
which uses ``translate_display`` or ``translate_assignment``; all of them use
``translate_value`` for literals and field names. ``build_script`` wraps the
result in a ``main()`` function. New statement rules go in
``translate_statement``.

After conversion, ``run_and_verify_python`` compiles the draft, runs it, and
checks that stdout matches an expected string exactly (syntax, runtime, and
output).
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
# A field entry: level, name, picture, and an optional VALUE.
FIELD_ENTRY = re.compile(
    r"^(?:01|77)\s+([A-Z][A-Z0-9-]*)\s+PIC\s+(X+|9+)(?:\(\d+\))?(?:\s+VALUE\s+(.+))?$",
    re.IGNORECASE,
)
# A quoted text literal; a doubled quote inside it stands for one quote.
TEXT_LITERAL = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'')
# One DISPLAY item: a text literal, a number, or a name.
DISPLAY_ITEM = re.compile(
    rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?|[A-Z][A-Z0-9-]*", re.IGNORECASE
)
WHOLE_NUMBER = re.compile(r"[-+]?\d+")
FIELD_NAME = re.compile(r"[A-Z][A-Z0-9-]*", re.IGNORECASE)
# MOVE x TO y, ADD x TO y, SUBTRACT x FROM y: (verb, word before the target) -> operator.
ASSIGNMENT_OPERATORS = {("MOVE", "TO"): "=", ("ADD", "TO"): "+=", ("SUBTRACT", "FROM"): "-="}
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
        >>> print(translate_value('"It""s"', fields).code)
        'It"s'
        >>> translate_value("007", fields)
        Value(code='7', is_number=True)
        >>> translate_value("ws-total", fields)
        Value(code='ws_total', is_number=True)
        >>> translate_value("1.5", fields) is None
        True
    """
    text = text.strip()
    upper = text.upper()
    if TEXT_LITERAL.fullmatch(text):
        quote = text[0]
        return Value(repr(text[1:-1].replace(quote * 2, quote)), is_number=False)
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
    is_number = picture[0] == "9"
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
        >>> translate_assignment('MOVE "GO  TO IT" TO WS-NAME', fields)
        "ws_name = 'GO  TO IT'"
        >>> translate_assignment('MOVE "abc" TO WS-TOTAL', fields) is None
        True
    """
    # Split on whitespace rather than one regex, so the time stays linear in the
    # line length: "MOVE 5 TO X" -> ["MOVE 5", "TO", "X"] -> "MOVE", "5".
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
    if value is None or target is None or value.is_number != target.is_number:
        return None
    if operator != "=" and not target.is_number:
        return None  # ADD and SUBTRACT need numbers
    return f"{target.code} {operator} {value.code}"


def translate_line(section: str, line: str, fields: dict[str, Value]) -> str | None:
    """Translate one line according to the section it is in.

    Args:
        section: ``"storage"`` (``WORKING-STORAGE``), ``"procedure"``, or
            ``"other"`` (a later data section such as ``LINKAGE``).
        line: The line after ``clean_line``, without its final period.
        fields: Declared fields, by uppercase COBOL name.

    Returns:
        One line of Python, or ``None`` if the line goes to review. Lines in
        ``"other"`` always go to review.

    Example:
        >>> translate_line("storage", "01 N PIC 9 VALUE 1", {})
        'n = 1'
        >>> translate_line("other", "01 LS-DAYS PIC 999", {}) is None
        True
    """
    if section == "storage":
        return translate_field(line, fields)
    if section == "procedure":
        return translate_statement(line, fields)
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
    section = ""  # becomes "storage", maybe "other", then "procedure"
    for number, line in numbered_lines:
        upper = line.upper()
        if upper == "WORKING-STORAGE SECTION":
            section = "storage"
        elif upper.startswith("PROCEDURE DIVISION"):
            section = "procedure"
        elif line and section:
            if section == "storage" and upper.endswith(" SECTION"):
                section = "other"  # LINKAGE and the like: parameters, not variables
            translated = translate_line(section, line, fields)
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
            # Running generated drafts is the point of this check.
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
