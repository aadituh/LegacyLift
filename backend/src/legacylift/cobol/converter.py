"""Translate a practical subset of COBOL into draft Python that runs.

Supported (WORKING-STORAGE, LINKAGE, and PROCEDURE DIVISION)
------------------------------------------------------------
**Data items**

- Elementary fields at levels ``01``–``49`` and ``77`` with:
  - text: ``PIC X``, ``XX``, ``X(n)``
  - whole numbers: ``PIC 9``, ``99``, ``9(n)``, optional leading ``S``
  - decimals: ``PIC …V…`` (e.g. ``99V99``, ``S9(10)V99``) via ``Decimal``
    and ``cobol_number`` (issue #21)
- Optional ``VALUE`` (literals, ``ZERO``/``ZEROS``, ``SPACE``/``SPACES``).
- Text literals may use doubled quotes (``"It""s"``).
- Group items become ``dict`` values; elementary children are dict keys.
- ``OCCURS n TIMES`` becomes a list of ``n`` record dicts; COBOL's 1-based
  subscripts ``NAME(I)`` become ``name[i - 1]``.
- Level ``88`` conditions become parent-field comparisons; ``SET cond TO TRUE``
  assigns the condition's ``VALUE`` to the parent.
- ``COPY name`` expands when copybook text is supplied to ``translate_program``.

**Procedure**

- ``DISPLAY`` items (literals and declared fields) using ``display_number`` /
  stored ``cobol_text`` so padding matches GnuCOBOL
- ``MOVE … TO …``, ``ADD … TO …``, ``SUBTRACT … FROM …``
- ``MULTIPLY … BY …``, ``DIVIDE … INTO …`` (no ``GIVING``)
- ``COMPUTE [ROUNDED] name =`` expression with ``+ - * /``, numbers, fields
- Paragraph headers (``NAME.``) become nested functions inside ``main()``
- ``PERFORM name`` / ``PERFORM a THRU b`` call those functions
- ``STOP RUN`` → ``return`` (exits the current paragraph or ``main``)

Unsupported lines become ``# TODO`` comments and review notes so the draft
still runs (file I/O, edited PICs, ``COMPUTE ROUNDED``, etc.).

Generated scripts import ``cobol_number``, ``cobol_text``, and
``display_number`` from ``legacylift.cobol.runtime``.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import keyword
import re
import traceback
from dataclasses import dataclass, field
from typing import NamedTuple

from legacylift.cobol.runtime import analyze_numeric_picture, analyze_text_length
from legacylift.errors import ConversionError
from legacylift.models import PythonDraft

PROGRAM_ID = re.compile(r"\bPROGRAM-ID\s*\.\s*([A-Z][A-Z0-9-]*)", re.IGNORECASE)
PROCEDURE_DIVISION = re.compile(
    r"\bPROCEDURE\s+DIVISION(?:\s+USING\s+(.+))?",
    re.IGNORECASE,
)
COPY_STMT = re.compile(r"^COPY\s+([A-Z][A-Z0-9-]*)\s*$", re.IGNORECASE)

# Elementary: level, name, PIC, optional VALUE. Trailing SIGN … is ignored.
FIELD_ENTRY = re.compile(
    r"^(0[1-9]|[1-4]\d|77)\s+([A-Z][A-Z0-9-]*)\s+"
    r"PIC(?:TURE)?\s+(S?9+(?:\(\d+\))?(?:V9+(?:\(\d+\))?)?|X+(?:\(\d+\))?)"
    r"(?:\s+VALUE(?:\s+IS)?\s+(.+?))?"
    r"(?:\s+SIGN\b.*)?$",
    re.IGNORECASE,
)
# Group or OCCURS group: level + name, optional OCCURS, no (supported) PIC.
GROUP_ENTRY = re.compile(
    r"^(0[1-9]|[1-4]\d)\s+([A-Z][A-Z0-9-]*)"
    r"(?:\s+OCCURS\s+(\d+)\s+TIMES)?$",
    re.IGNORECASE,
)
LEVEL88_ENTRY = re.compile(
    r"^88\s+([A-Z][A-Z0-9-]*)\s+VALUE(?:\s+IS)?\s+(.+)$",
    re.IGNORECASE,
)
# OCCURS on the same line as PIC (rare in our samples).
FIELD_OCCURS_ENTRY = re.compile(
    r"^(0[1-9]|[1-4]\d)\s+([A-Z][A-Z0-9-]*)\s+"
    r"OCCURS\s+(\d+)\s+TIMES\s+"
    r"PIC(?:TURE)?\s+(S?9+(?:\(\d+\))?(?:V9+(?:\(\d+\))?)?|X+(?:\(\d+\))?)"
    r"(?:\s+VALUE(?:\s+IS)?\s+(.+?))?$",
    re.IGNORECASE,
)

TEXT_LITERAL = re.compile(r'"(?:[^"]|"")*"|\'(?:[^\']|\'\')*\'')
# Subscripted or plain name in DISPLAY / expressions.
NAME_OR_SUB = re.compile(
    rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?"
    rf"|[A-Z][A-Z0-9-]*(?:\s*\(\s*[A-Z0-9+-]+\s*\))?",
    re.IGNORECASE,
)
DISPLAY_ITEM = NAME_OR_SUB
WHOLE_NUMBER = re.compile(r"[-+]?\d+")
DECIMAL_NUMBER = re.compile(r"[-+]?\d+\.\d+")
FIELD_NAME = re.compile(r"[A-Z][A-Z0-9-]*", re.IGNORECASE)
SUBSCRIPT_REF = re.compile(
    r"^([A-Z][A-Z0-9-]*)\s*\(\s*([A-Z][A-Z0-9-]*|[-+]?\d+)\s*\)$",
    re.IGNORECASE,
)
COMPUTE_STMT = re.compile(
    r"^COMPUTE\s+([A-Z][A-Z0-9-]*)\s+(?:(ROUNDED)\s+)?=\s*(.+)$",
    re.IGNORECASE,
)
COMPUTE_TOKEN = re.compile(
    rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?"
    rf"|[A-Z][A-Z0-9-]*(?:\s*\(\s*[A-Z0-9+-]+\s*\))?|[()+*/\-]",
    re.IGNORECASE,
)
PERFORM_STMT = re.compile(
    r"^PERFORM\s+([A-Z][A-Z0-9-]*)"
    r"(?:\s+(?:THRU|THROUGH)\s+([A-Z][A-Z0-9-]*))?$",
    re.IGNORECASE,
)
PERFORM_UNTIL = re.compile(r"^PERFORM\s+UNTIL\s+(.+)$", re.IGNORECASE)
PERFORM_VARYING = re.compile(
    r"^PERFORM\s+VARYING\s+([A-Z][A-Z0-9-]*)\s+FROM\s+(\S+)\s+BY\s+(\S+)\s+UNTIL\s+(.+)$",
    re.IGNORECASE,
)
MULTIPLY_STMT = re.compile(
    r"^MULTIPLY\s+(.+?)\s+BY\s+([A-Z][A-Z0-9-]*(?:\s*\(\s*[A-Z0-9+-]+\s*\))?)$",
    re.IGNORECASE,
)
DIVIDE_STMT = re.compile(
    r"^DIVIDE\s+(.+?)\s+INTO\s+([A-Z][A-Z0-9-]*(?:\s*\(\s*[A-Z0-9+-]+\s*\))?)$",
    re.IGNORECASE,
)
CALL_STMT = re.compile(
    r"""^CALL\s+(?:"([^"]+)"|'([^']+)')\s+USING\s+(.+)$""",
    re.IGNORECASE,
)
SET_TRUE = re.compile(
    r"^SET\s+([A-Z][A-Z0-9-]*)\s+TO\s+TRUE$",
    re.IGNORECASE,
)
IF_HEAD = re.compile(r"^IF\s+(.+)$", re.IGNORECASE)
EVALUATE_HEAD = re.compile(r"^EVALUATE\s+(.+)$", re.IGNORECASE)
WHEN_HEAD = re.compile(r"^WHEN\s+(.+)$", re.IGNORECASE)

ASSIGNMENT_OPERATORS = {
    ("MOVE", "TO"): "=",
    ("ADD", "TO"): "+=",
    ("SUBTRACT", "FROM"): "-=",
}
RESERVED_NAMES = set(keyword.kwlist) | set(dir(builtins)) | {"main"}
PERFORM_LOOP_STARTERS = frozenset({"UNTIL", "VARYING", "WITH", "TEST"})
# Scope terminators and clauses that must not become paragraph functions.
NOT_PARAGRAPH_NAMES = frozenset(
    {
        "ELSE",
        "WHEN",
        "OTHER",
        "END-IF",
        "END-PERFORM",
        "END-EVALUATE",
        "END-READ",
        "END-CALL",
        "END-COMPUTE",
        "END-SEARCH",
        "AT",
        "NOT",
        "ALSO",
        "THROUGH",
        "THRU",
        "UNTIL",
        "VARYING",
        "WITH",
        "TEST",
        "TRUE",
        "FALSE",
    }
)

# Procedure lines that start a new statement (not a CALL/PERFORM continuation).
_STMT_STARTERS = re.compile(
    r"^(?:"
    r"DISPLAY|MOVE|ADD|SUBTRACT|MULTIPLY|DIVIDE|COMPUTE|PERFORM|IF|ELSE|END-IF|"
    r"EVALUATE|WHEN|END-EVALUATE|CALL|SET|STOP|GOBACK|EXIT|OPEN|CLOSE|READ|WRITE|"
    r"ACCEPT|REWRITE|DELETE|START|END-PERFORM|END-READ|END-IF|END-EVALUATE|"
    r"END-CALL|AT\s+END|NOT\s+AT\s+END|CONTINUE|NEXT\s+SENTENCE"
    r")\b",
    re.IGNORECASE,
)
_LEVEL_START = re.compile(r"^(0[1-9]|[1-4]\d|66|77|88)\s+", re.IGNORECASE)


class Value(NamedTuple):
    """A COBOL value or field, translated to Python.

    Attributes:
        code: Python source, such as ``'Hi'``, ``5``, or ``ws_total``.
        is_number: ``True`` for numerics, ``False`` for text.
        is_float: ``True`` when the picture has ``V`` (decimal places).
        integers: ``9`` digits left of ``V`` (0 for text).
        decimals: ``9`` digits right of ``V``.
        signed: ``True`` for ``S9…`` pictures.
        length: ``PIC X(n)`` length (0 for numbers).
    """

    code: str
    is_number: bool
    is_float: bool = False
    integers: int = 0
    decimals: int = 0
    signed: bool = False
    length: int = 0


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


@dataclass
class ConditionInfo:
    """Level-88 condition: parent field code and the VALUE that makes it true."""

    parent_code: str
    value: Value


@dataclass
class OccursChild:
    """One elementary field inside an OCCURS record dict."""

    key: str
    is_number: bool
    is_float: bool
    default_code: str


@dataclass
class FieldModel:
    """Resolved names for translation.

    Attributes:
        fields: COBOL name → access ``Value`` (scalars, groups, or whole tables).
        conditions: Level-88 name → parent comparison info.
        occurs_children: Elementary name under OCCURS → (table_code, dict_key, types).
        group_children: Elementary name under a non-OCCURS group → (group_code, key, types).
        init_lines: Python assignments for WORKING-STORAGE.
        linkage_params: Ordered LINKAGE / USING parameter COBOL names.
        scalar_vars: Python names that need ``nonlocal`` in nested paragraphs.
    """

    fields: dict[str, Value] = field(default_factory=dict)
    conditions: dict[str, ConditionInfo] = field(default_factory=dict)
    occurs_children: dict[str, tuple[str, str, bool, bool]] = field(default_factory=dict)
    group_children: dict[str, tuple[str, str, bool, bool]] = field(default_factory=dict)
    init_lines: list[str] = field(default_factory=list)
    linkage_params: list[str] = field(default_factory=list)
    scalar_vars: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)


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
        if raw_line[6] == "-" or raw_line[6] == " ":
            raw_line = raw_line[7:]
    # Keep leading spaces so Area A (paragraph names) vs Area B stays visible.
    line = raw_line.rstrip()
    stripped = line.lstrip()
    return "" if stripped.startswith("*>") else line


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


def _store_number(expr: str, target: Value, *, rounded: bool = False) -> str:
    """Emit ``name = cobol_number(expr, …)`` for a numeric target field."""
    rounded_arg = ", rounded=True" if rounded else ""
    return (
        f"{target.code} = cobol_number({expr}, integers={target.integers}, "
        f"decimals={target.decimals}, signed={target.signed}{rounded_arg})"
    )


def _store_text(expr: str, target: Value) -> str:
    """Emit ``name = cobol_text(expr, length)`` for a text target field."""
    return f"{target.code} = cobol_text({expr}, {target.length})"


def _display_expr(value: Value) -> str:
    """Python expression that prints a field with COBOL DISPLAY formatting."""
    if value.is_number:
        return (
            f"display_number({value.code}, integers={value.integers}, "
            f"decimals={value.decimals}, signed={value.signed})"
        )
    return value.code


def translate_value(text: str, fields: dict[str, Value]) -> Value | None:
    """Translate one COBOL value: a literal, ``ZERO``/``SPACES``, or a field name.

    Args:
        text: The value as written in COBOL.
        model: Declared fields and conditions.

    Returns:
        The translated value, or ``None`` for anything unsupported.

    Example:
        >>> fields = {"WS-TOTAL": Value("ws_total", is_number=True)}
        >>> translate_value('"Hi"', fields).code
        "'Hi'"
        >>> print(translate_value('"It""s"', fields).code)
        'It"s'
        >>> translate_value("007", fields).code
        '7'
        >>> translate_value("1.5", fields).is_float
        True
        >>> translate_value("ws-total", fields).code
        'ws_total'
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
    if upper in {"TRUE"}:
        return Value("True", is_number=False)
    if upper in {"FALSE"}:
        return Value("False", is_number=False)
    return resolve_name(text, model)


def resolve_name(text: str, model: FieldModel) -> Value | None:
    """Resolve a field name or ``NAME(INDEX)`` subscript to a Python ``Value``."""
    text = text.strip()
    sub = SUBSCRIPT_REF.fullmatch(text)
    if sub:
        return resolve_subscript(sub.group(1).upper(), sub.group(2).strip(), model)
    upper = text.upper()
    if upper in model.conditions:
        cond = model.conditions[upper]
        return Value(f"({cond.parent_code} == {cond.value.code})", False)
    if upper in model.fields:
        return model.fields[upper]
    if upper in model.group_children:
        group_code, key, is_number, is_float = model.group_children[upper]
        return Value(f'{group_code}["{key}"]', is_number, is_float)
    if upper in model.occurs_children:
        # Unsubscripted OCCURS child is ambiguous; leave unsupported.
        return None
    return None


def resolve_subscript(name: str, index_text: str, model: FieldModel) -> Value | None:
    """Resolve ``TABLE(I)`` or ``CHILD(I)`` with COBOL 1-based indexing."""
    if WHOLE_NUMBER.fullmatch(index_text):
        index_expr = str(int(index_text) - 1)
    else:
        index_val = translate_value(index_text, model)
        if index_val is None:
            return None
        index_expr = f"({index_val.code}) - 1"

    upper = name.upper()
    occurs_tables = {n for n, _ in _occurs_table_names(model)}

    if upper in model.occurs_children:
        table_code, key, is_number, is_float = model.occurs_children[upper]
        return Value(f'{table_code}[{index_expr}]["{key}"]', is_number, is_float)

    if upper in model.fields:
        table = model.fields[upper]
        if upper in occurs_tables:
            return Value(f"{table.code}[{index_expr}]", False)
        # Elementary OCCURS list element.
        return Value(f"{table.code}[{index_expr}]", table.is_number, table.is_float)

    return None


def _occurs_table_names(model: FieldModel) -> list[tuple[str, str]]:
    """COBOL names that are OCCURS tables (list variables)."""
    names: list[tuple[str, str]] = []
    seen: set[str] = set()
    for table_code, _key, _n, _f in model.occurs_children.values():
        if table_code not in seen:
            seen.add(table_code)
            for cobol, value in model.fields.items():
                if value.code == table_code:
                    names.append((cobol, table_code))
                    break
    return names


def _types_compatible(value: Value, target: Value) -> bool:
    """MOVE/ADD targets: both text, or both numeric (no decimal into whole PIC)."""
    if value.is_number != target.is_number:
        return False
    return not (value.is_float and target.is_number and not target.is_float)


def expand_copybooks(source: str, copybooks: dict[str, str] | None) -> str:
    """Replace ``COPY name.`` lines with copybook text when available.

    Args:
        source: Full COBOL program text.
        copybooks: Map of copybook name (with or without ``.cpy``) → text.
            Matching is case-insensitive on the stem.

    Returns:
        Source with resolved COPY lines expanded; unresolved COPY lines kept.
    """
    if not copybooks:
        return source

    index: dict[str, str] = {}
    for name, text in copybooks.items():
        stem = name.rsplit(".", 1)[0].upper()
        index[stem] = text
        index[name.upper()] = text

    out_lines: list[str] = []
    for raw in source.splitlines():
        cleaned = clean_line(raw).removesuffix(".").strip()
        match = COPY_STMT.fullmatch(cleaned)
        if match is None:
            out_lines.append(raw)
            continue
        book = match.group(1).upper()
        book_text = index.get(book)
        if book_text is None:
            out_lines.append(raw)
            continue
        out_lines.extend(book_text.splitlines())
    return "\n".join(out_lines)

    Example:
        >>> fields = {}
        >>> translate_field("01 WS-TOTAL PIC 9(4) VALUE 10", fields)
        'ws_total = cobol_number(10, integers=4, decimals=0, signed=False)'
        >>> translate_field("01 WS-NAME PIC X(10)", fields)
        "ws_name = cobol_text('', 10)"
        >>> translate_field("05 HOURS-WORKED PIC 99V99", fields)
        'hours_worked = cobol_number(0, integers=2, decimals=2, signed=False)'
        >>> translate_field("01 EMPLOYEE", fields)
        ''
        >>> translate_field('01 WS-COUNT PIC 9 VALUE "ten"', fields) is None
        True
        >>> sorted(fields)
        ['HOURS-WORKED', 'WS-NAME', 'WS-TOTAL']
    """
    if not numbered:
        return []
    result: list[tuple[int, str]] = [numbered[0]]
    for number, line in numbered[1:]:
        if not line:
            result.append((number, line))
            continue
        prev_num, prev = result[-1]
        if not prev:
            result.append((number, line))
            continue

    match = FIELD_ENTRY.fullmatch(line)
    if match is None:
        return None
    _level, cobol_name, picture, initial_text = match.groups()
    text_len = analyze_text_length(picture)
    numeric = analyze_numeric_picture(picture)
    is_float = picture_is_float(picture)
    is_number = numeric is not None
    initial: Value | None
    if initial_text is None:
        initial = Value("0" if is_number else "''", is_number, is_float)
    else:
        initial = translate_value(initial_text, fields)
    if initial is None or initial.is_number != is_number:
        return None
    if is_number and not is_float and initial.is_float:
        return None

    variable = variable_name(cobol_name)
    if is_number and numeric is not None:
        fields[cobol_name.upper()] = Value(
            variable,
            True,
            is_float,
            integers=numeric.integers,
            decimals=numeric.decimals,
            signed=numeric.signed,
        )
        return _store_number(initial.code, fields[cobol_name.upper()])
    length = text_len or 1
    fields[cobol_name.upper()] = Value(variable, False, length=length)
    return _store_text(initial.code, fields[cobol_name.upper()])


def is_paragraph_header(line: str) -> bool:
    """True when the procedure line is a paragraph name in Area A.

    After ``clean_line``, Area A starts at column 0 (no leading spaces). Area B
    statements are indented, so ``END-PERFORM`` / ``USING`` continuations are
    not treated as headers.
    """
    if not line or line[0] in " \t":
        return False
    return bool(FIELD_NAME.fullmatch(line.strip()))


@dataclass
class _PendingGroup:
    level: int
    cobol_name: str
    py_name: str
    occurs: int | None
    children: list[OccursChild] = field(default_factory=list)
    section: str = "storage"  # storage | linkage


def build_field_model(
    numbered: list[tuple[int, str]],
    *,
    accept_linkage: bool = False,
) -> tuple[FieldModel, list[str]]:
    """Parse WORKING-STORAGE and LINKAGE into a ``FieldModel``.

    Args:
        numbered: Cleaned source lines with original numbers.
        accept_linkage: When True (PROCEDURE DIVISION USING), parse LINKAGE
            into parameters. When False, LINKAGE lines become review notes.

    Returns:
        The model and the ordered USING/linkage parameter COBOL names found.
    """
    model = FieldModel()
    section = ""
    stack: list[_PendingGroup] = []
    last_elementary_parent: tuple[str, str] | None = None  # (cobol, code) for 88
    linkage_order: list[str] = []

    def close_groups_deeper_or_equal(level: int) -> None:
        nonlocal last_elementary_parent
        while stack and stack[-1].level >= level:
            pending = stack.pop()
            _emit_group(pending, model, linkage_order)
            last_elementary_parent = None

    for number, line in numbered:
        upper = line.upper()
        if upper == "WORKING-STORAGE SECTION":
            close_groups_deeper_or_equal(0)
            section = "storage"
            continue
        if upper == "LINKAGE SECTION":
            close_groups_deeper_or_equal(0)
            if accept_linkage:
                section = "linkage"
            else:
                section = "other"
                model.notes.append(f"Line {number}: {line}")
                model.init_lines.append(f"# TODO: COBOL line {number}: {line}")
            continue
        if upper.endswith(" SECTION") and section in {"storage", "linkage"}:
            close_groups_deeper_or_equal(0)
            section = "other"
            continue
        if upper.startswith("PROCEDURE DIVISION"):
            close_groups_deeper_or_equal(0)
            break
        if not line or section not in {"storage", "linkage", "other"}:
            continue
        if section == "other":
            todo = f"# TODO: COBOL line {number}: {line}"
            model.notes.append(f"Line {number}: {line}")
            model.todos.append(todo)
            model.init_lines.append(todo)
            continue

        # COPY left unresolved.
        if COPY_STMT.fullmatch(line):
            todo = f"# TODO: COBOL line {number}: {line}"
            model.notes.append(f"Line {number}: {line}")
            model.todos.append(todo)
            if section == "storage":
                model.init_lines.append(todo)
            continue

        lvl88 = LEVEL88_ENTRY.fullmatch(line)
        if lvl88:
            cond_name = lvl88.group(1).upper()
            value = translate_value(lvl88.group(2).strip(), model)
            if value is None or last_elementary_parent is None:
                todo = f"# TODO: COBOL line {number}: {line}"
                model.notes.append(f"Line {number}: {line}")
                model.todos.append(todo)
                if section == "storage":
                    model.init_lines.append(todo)
                continue
            _parent_cobol, parent_code = last_elementary_parent
            model.conditions[cond_name] = ConditionInfo(parent_code, value)
            continue

        occurs_elem = FIELD_OCCURS_ENTRY.fullmatch(line)
        if occurs_elem:
            level_s, cobol_name, occurs_s, picture, initial_text = occurs_elem.groups()
            if cobol_name.upper() == "FILLER":
                continue
            level = int(level_s)
            close_groups_deeper_or_equal(level)
            is_float = picture_is_float(picture)
            is_number = picture.upper().lstrip("S")[0] == "9"
            initial = _initial_from_text(initial_text, is_number, is_float, model)
            if initial is None:
                todo = f"# TODO: COBOL line {number}: {line}"
                model.notes.append(f"Line {number}: {line}")
                if section == "storage":
                    model.init_lines.append(todo)
                continue
            py = variable_name(cobol_name)
            n = int(occurs_s)
            if section == "storage":
                model.init_lines.append(f"{py} = [{initial.code} for _ in range({n})]")
                model.scalar_vars.append(py)
            model.fields[cobol_name.upper()] = Value(py, is_number, is_float)
            last_elementary_parent = (cobol_name.upper(), f"{py}[0]")
            continue

        elem = FIELD_ENTRY.fullmatch(line)
        if elem:
            level_s, cobol_name, picture, initial_text = elem.groups()
            if cobol_name.upper() == "FILLER":
                continue
            level = int(level_s)
            close_groups_deeper_or_equal(level)
            is_float = picture_is_float(picture)
            is_number = picture.upper().lstrip("S")[0] == "9"
            initial = _initial_from_text(initial_text, is_number, is_float, model)
            if initial is None:
                todo = f"# TODO: COBOL line {number}: {line}"
                model.notes.append(f"Line {number}: {line}")
                if section == "storage":
                    model.init_lines.append(todo)
                continue

            key = variable_name(cobol_name)
            # Nested under an OCCURS or group?
            if stack and stack[-1].occurs is not None:
                stack[-1].children.append(OccursChild(key, is_number, is_float, initial.code))
                table_py = stack[-1].py_name
                model.occurs_children[cobol_name.upper()] = (
                    table_py,
                    key,
                    is_number,
                    is_float,
                )
                last_elementary_parent = (
                    cobol_name.upper(),
                    f'{table_py}[0]["{key}"]',
                )
            elif stack:
                # Non-OCCURS group child.
                stack[-1].children.append(OccursChild(key, is_number, is_float, initial.code))
                group_py = stack[-1].py_name
                model.group_children[cobol_name.upper()] = (
                    group_py,
                    key,
                    is_number,
                    is_float,
                )
                last_elementary_parent = (
                    cobol_name.upper(),
                    f'{group_py}["{key}"]',
                )
            else:
                # Top-level elementary.
                if section == "storage":
                    model.init_lines.append(f"{key} = {initial.code}")
                    model.scalar_vars.append(key)
                elif section == "linkage":
                    linkage_order.append(cobol_name.upper())
                model.fields[cobol_name.upper()] = Value(key, is_number, is_float)
                last_elementary_parent = (cobol_name.upper(), key)
            continue

        group = GROUP_ENTRY.fullmatch(line)
        if group:
            level_s, cobol_name, occurs_s = group.groups()
            level = int(level_s)
            close_groups_deeper_or_equal(level)
            occurs = int(occurs_s) if occurs_s else None
            py = variable_name(cobol_name)
            stack.append(
                _PendingGroup(
                    level=level,
                    cobol_name=cobol_name.upper(),
                    py_name=py,
                    occurs=occurs,
                    section=section,
                )
            )
            last_elementary_parent = None
            continue

        # FILLER or unsupported storage line.
        filler = re.match(
            r"^(0[1-9]|[1-4]\d)\s+FILLER\b",
            line,
            re.IGNORECASE,
        )
        if filler:
            # Ignore FILLER under groups; no review note.
            continue

        todo = f"# TODO: COBOL line {number}: {line}"
        model.notes.append(f"Line {number}: {line}")
        if section == "storage":
            model.init_lines.append(todo)
        # linkage unsupported lines noted but not emitted as locals

    close_groups_deeper_or_equal(0)
    model.linkage_params = linkage_order
    return model, linkage_order


def _emit_group(
    pending: _PendingGroup,
    model: FieldModel,
    linkage_order: list[str],
) -> None:
    """Emit init / register a finished group or OCCURS table."""
    name = pending.cobol_name
    py = pending.py_name
    if pending.occurs is not None:
        record = _record_default_dict(pending.children)
        if pending.section == "storage":
            model.init_lines.append(f"{py} = [{record} for _ in range({pending.occurs})]")
            model.scalar_vars.append(py)
        model.fields[name] = Value(py, False)
        return

    if not pending.children:
        # Empty group header (e.g. wrapper around OCCURS child already emitted).
        return

    record = _record_default_dict(pending.children)
    if pending.section == "storage":
        model.init_lines.append(f"{py} = {record}")
        model.scalar_vars.append(py)
    elif pending.section == "linkage":
        linkage_order.append(name)
    model.fields[name] = Value(py, False)
    # Children already registered in group_children during parse.


def translate_condition(text: str, model: FieldModel) -> str | None:
    """Translate a COBOL condition to a Python expression."""
    text = text.strip()
    if not text:
        return None
    upper = text.upper()
    if upper == "TRUE":
        return "True"
    if upper == "FALSE":
        return "False"

    # Level-88 alone.
    if upper in model.conditions:
        cond = model.conditions[upper]
        return f"({cond.parent_code} == {cond.value.code})"

    # Tokenize into values, operators, AND/OR/NOT, parentheses.
    token_re = re.compile(
        rf"{TEXT_LITERAL.pattern}|[-+]?\d+(?:\.\d+)?"
        rf"|[A-Z][A-Z0-9-]*(?:\s*\(\s*[A-Z0-9+-]+\s*\))?"
        rf"|>=|<=|<>|!=|[()<>=]|AND|OR|NOT",
        re.IGNORECASE,
    )
    tokens = token_re.findall(text)
    if not tokens or token_re.sub("", text).strip():
        return None

    parts: list[str] = []
    for token in tokens:
        tu = token.upper()
        if tu == "AND":
            parts.append("and")
        elif tu == "OR":
            parts.append("or")
        elif tu == "NOT":
            parts.append("not")
        elif tu in {"=", "=="}:
            parts.append("==")
        elif tu == "<>":
            parts.append("!=")
        elif tu in {">", "<", ">=", "<=", "(", ")"}:
            parts.append(tu)
        else:
            value = translate_value(token, model)
            if value is None:
                return None
            # Level-88 resolve_name returns a comparison already parenthesized;
            # bare condition names are handled above. Field refs use .code.
            if token.upper() in model.conditions:
                parts.append(value.code)
            else:
                parts.append(value.code)
    return " ".join(parts)


def translate_perform(line: str, paragraph_order: list[str]) -> str | None:
    """Translate ``PERFORM name`` or ``PERFORM a THRU b`` into function calls."""
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
    """Translate ``COMPUTE [ROUNDED] name = expression`` via ``cobol_number``.

    Only ``+ - * /``, parentheses, numbers, and declared field names are
    allowed on the right-hand side.
    """
    match = COMPUTE_STMT.fullmatch(line.strip())
    if match is None:
        return None
    target_name, rounded_word, expression = match.group(1), match.group(2), match.group(3)
    expression = expression.strip()
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
        value = translate_value(token, model)
        if value is None or not value.is_number:
            return None
        parts.append(value.code)
    return _store_number("".join(parts), target, rounded=bool(rounded_word))


def translate_multiply_divide(line: str, fields: dict[str, Value]) -> str | None:
    """Translate ``MULTIPLY x BY y`` or ``DIVIDE x INTO y`` through ``cobol_number``."""
    multiply = MULTIPLY_STMT.fullmatch(line.strip())
    if multiply:
        value = translate_value(multiply.group(1), model)
        target = resolve_name(multiply.group(2), model)
        if value is None or target is None or not value.is_number or not target.is_number:
            return None
        return _store_number(f"{target.code} * {value.code}", target)
    divide = DIVIDE_STMT.fullmatch(line.strip())
    if divide:
        value = translate_value(divide.group(1), model)
        target = resolve_name(divide.group(2), model)
        if value is None or target is None or not value.is_number or not target.is_number:
            return None
        return _store_number(f"{target.code} / {value.code}", target)
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
        >>> fields = {"WS-TOTAL": Value("ws_total", True, integers=4)}
        >>> translate_statement("ADD 5 TO WS-TOTAL", fields)
        'ws_total = cobol_number(ws_total + 5, integers=4, decimals=0, signed=False)'
        >>> translate_statement("STOP RUN", fields)
        'return'
        >>> translate_statement("PERFORM PRINT-TOTAL", fields, ["PRINT-TOTAL"])
        'print_total()'
        >>> translate_statement(
        ...     "COMPUTE WS-TOTAL = WS-TOTAL * 2",
        ...     {"WS-TOTAL": Value("ws_total", True, integers=4)},
        ... )
        'ws_total = cobol_number(ws_total*2, integers=4, decimals=0, signed=False)'
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
        >>> fields = {"WS-TOTAL": Value("ws_total", True, integers=4)}
        >>> translate_display('"Total: " WS-TOTAL', fields)
        "print('Total: ', display_number(ws_total, integers=4, decimals=0, signed=False), sep='')"
        >>> translate_display("WS-TOTAL + 1", fields) is None
        True
    """
    items_text = items_text.strip()
    items = DISPLAY_ITEM.findall(items_text)
    if not items or DISPLAY_ITEM.sub("", items_text).strip():
        return None
    codes = []
    for item in items:
        value = translate_value(item, model)
        if value is None:
            return None
        # Literals print as-is; fields use DISPLAY formatting helpers.
        if FIELD_NAME.fullmatch(item) and item.upper() in fields:
            codes.append(_display_expr(fields[item.upper()]))
        else:
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
        >>> fields = {
        ...     "WS-TOTAL": Value("ws_total", True, integers=4),
        ...     "WS-NAME": Value("ws_name", False, length=10),
        ... }
        >>> translate_assignment("SUBTRACT 2 FROM WS-TOTAL", fields)
        'ws_total = cobol_number(ws_total - 2, integers=4, decimals=0, signed=False)'
        >>> translate_assignment('MOVE "GO  TO IT" TO WS-NAME', fields)
        "ws_name = cobol_text('GO  TO IT', 10)"
        >>> translate_assignment('MOVE "abc" TO WS-TOTAL', fields) is None
        True
    """
    parts = line.rsplit(maxsplit=2)
    verb_and_value = parts[0].split(maxsplit=1) if len(parts) == 3 else []
    if len(verb_and_value) != 2:
        return None
    (verb, value_text), (_, target_word, target_name) = verb_and_value, parts
    operator = ASSIGNMENT_OPERATORS.get((verb.upper(), target_word.upper()))
    if operator is None:
        return None
    # Target may be subscripted: NAME(I)
    target = resolve_name(target_name, model)
    if target is None and SUBSCRIPT_REF.fullmatch(target_name):
        target = resolve_name(target_name, model)
    # rsplit may have split NAME ( I ) badly — try full line parse for subscripts.
    if target is None:
        assign_sub = re.match(
            r"^(MOVE|ADD|SUBTRACT)\s+(.+?)\s+(TO|FROM)\s+"
            r"([A-Z][A-Z0-9-]*\s*\(\s*[A-Z0-9+-]+\s*\))$",
            line,
            re.IGNORECASE,
        )
        if assign_sub:
            verb = assign_sub.group(1)
            value_text = assign_sub.group(2)
            target_word = assign_sub.group(3)
            target_name = assign_sub.group(4)
            operator = ASSIGNMENT_OPERATORS.get((verb.upper(), target_word.upper()))
            if operator is None:
                return None
            target = resolve_name(target_name, model)
    if operator is None or target is None:
        return None
    value = translate_value(value_text, model)
    if value is None or not _types_compatible(value, target):
        return None
    if operator != "=" and not target.is_number:
        return None
    if not target.is_number:
        return _store_text(value.code, target)
    if operator == "=":
        return _store_number(value.code, target)
    if operator == "+=":
        return _store_number(f"{target.code} + {value.code}", target)
    return _store_number(f"{target.code} - {value.code}", target)


def translate_set(line: str, model: FieldModel) -> str | None:
    """Translate ``SET condition TO TRUE``."""
    match = SET_TRUE.fullmatch(line.strip())
    if match is None:
        return None
    name = match.group(1).upper()
    cond = model.conditions.get(name)
    if cond is None:
        return None
    return f"{cond.parent_code} = {cond.value.code}"


def translate_call(
    line: str,
    model: FieldModel,
    call_targets: list[str] | None = None,
) -> str | None:
    """Translate ``CALL "PROG" USING a b c`` into a Python call with return assign.

    Dict/group arguments are passed through (mutated in place). The last
    elementary (scalar) USING argument is assigned from the function's return
    value, matching sample-bank callees that set a result code or interest.
    """
    match = CALL_STMT.fullmatch(line.strip())
    if match is None:
        return None
    prog = match.group(1) or match.group(2)
    if prog is None:
        return None
    fn = variable_name(prog)
    if call_targets is not None and fn not in call_targets:
        call_targets.append(fn)
    using_text = match.group(3).strip()
    # Split USING args on whitespace, keeping NAME(I) together.
    arg_tokens = NAME_OR_SUB.findall(using_text)
    if not arg_tokens or NAME_OR_SUB.sub("", using_text).strip():
        return None
    args: list[str] = []
    last_scalar: str | None = None
    for token in arg_tokens:
        value = resolve_name(token, model)
        if value is None:
            # Allow passing whole group/table element.
            value = translate_value(token, model)
        if value is None:
            return None
        args.append(value.code)
        # Track last scalar-looking arg (not a dict/list subscript of record).
        if value.is_number or (
            value.code
            and not value.code.endswith("]")
            and "[" not in value.code
            and not value.code.startswith("{")
        ):
            # Heuristic: if it's a registered elementary field, it's scalar.
            upper = token.upper()
            plain = upper.split("(")[0].strip()
            if plain in model.fields and plain not in model.group_children:
                field_val = model.fields[plain]
                # OCCURS table name is a list — not a scalar out param.
                if plain in {n for n, _ in _occurs_table_names(model)}:
                    pass
                elif not field_val.is_number and field_val.code == value.code:
                    # Could be a group dict — groups have is_number False.
                    # Groups are in fields with is_number False; elementary text too.
                    # Distinguish: group names are keys that own group_children values.
                    is_group = any(
                        g == field_val.code for g, _k, _n, _f in model.group_children.values()
                    )
                    if not is_group:
                        last_scalar = value.code
                elif field_val.is_number:
                    last_scalar = value.code
            elif SUBSCRIPT_REF.fullmatch(token):
                # Element of occurs is a dict — not scalar.
                pass
            elif plain in model.group_children or plain in model.occurs_children:
                last_scalar = value.code

    call = f"{fn}({', '.join(args)})"
    if last_scalar is not None:
        return f"{last_scalar} = {call}"
    return call


def translate_simple_statement(
    line: str,
    model: FieldModel,
    paragraph_order: list[str],
    call_targets: list[str] | None = None,
) -> str | None:
    """Translate one non-block PROCEDURE statement to one Python statement."""
    upper = line.upper()
    if upper in {"STOP RUN", "GOBACK", "EXIT PROGRAM"}:
        return "return"
    if upper == "EXIT":
        return "return"
    if upper.startswith("DISPLAY "):
        return translate_display(line[len("DISPLAY ") :], model)
    if upper.startswith("SET "):
        return translate_set(line, model)
    if upper.startswith("CALL "):
        return translate_call(line, model, call_targets)
    if upper.startswith("PERFORM "):
        # Loops handled by block translator.
        if PERFORM_UNTIL.fullmatch(line) or PERFORM_VARYING.fullmatch(line):
            return None
        if line.upper().startswith("PERFORM UNTIL") or line.upper().startswith("PERFORM VARYING"):
            return None
        return translate_perform(line, paragraph_order)
    if upper.startswith("COMPUTE "):
        return translate_compute(line, model)
    multiplied = translate_multiply_divide(line, model)
    if multiplied is not None:
        return multiplied
    return translate_assignment(line, model)


    Example:
        >>> translate_line("storage", "01 N PIC 9 VALUE 1", {})
        'n = cobol_number(1, integers=1, decimals=0, signed=False)'
        >>> translate_line("other", "01 LS-DAYS PIC 999", {}) is None
        True
    """
    preamble: list[str] = []
    paragraphs: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    notes: list[str] = []
    call_targets: list[str] = []

    def emit_target() -> list[str]:
        nonlocal current
        if current is not None:
            return current
        return preamble

    def note_todo(number: int, line: str) -> None:
        todo = f"# TODO: COBOL line {number}: {line}"
        notes.append(f"Line {number}: {line}")
        emit_target().append(todo)

    i = 0
    n = len(lines)

    def peek_upper(j: int) -> str:
        return lines[j][1].upper() if 0 <= j < n else ""

    def _hits_marker(upper: str, end_markers: set[str]) -> bool:
        if upper in end_markers:
            return True
        # WHEN "OK" / WHEN OTHER share the WHEN marker.
        return bool("WHEN" in end_markers and (upper == "WHEN" or upper.startswith("WHEN ")))

    def translate_block_body(start: int, end_markers: set[str]) -> tuple[list[str], int]:
        """Translate statements until a line whose upper form is in end_markers."""
        body: list[str] = []
        j = start
        while j < n:
            number, line = lines[j]
            if not line:
                j += 1
                continue
            upper = line.upper()
            if _hits_marker(upper, end_markers):
                return body, j
            # Nested structures.
            if upper.startswith("IF "):
                chunk, j = translate_if(j)
                body.extend(chunk)
                continue
            if upper.startswith("EVALUATE "):
                chunk, j = translate_evaluate(j)
                body.extend(chunk)
                continue
            if upper.startswith("PERFORM UNTIL "):
                chunk, j = translate_perform_until(j)
                body.extend(chunk)
                continue
            if upper.startswith("PERFORM VARYING "):
                chunk, j = translate_perform_varying(j)
                body.extend(chunk)
                continue
            if is_paragraph_header(line):
                return body, j
            translated = translate_simple_statement(line, model, paragraph_order, call_targets)
            if translated is None:
                body.append(f"# TODO: COBOL line {number}: {line}")
                notes.append(f"Line {number}: {line}")
            else:
                body.append(translated)
            j += 1
        return body, j

    def translate_if(start: int) -> tuple[list[str], int]:
        number, line = lines[start]
        match = IF_HEAD.fullmatch(line)
        if match is None:
            note_todo(number, line)
            return [f"# TODO: COBOL line {number}: {line}"], start + 1
        cond = translate_condition(match.group(1), model)
        if cond is None:
            # Keep structure with if False so converted body lines do not run.
            body, j = translate_block_body(start + 1, {"END-IF", "ELSE"})
            out = [
                f"# TODO: COBOL line {number}: {line}",
                "if False:",
                *_indent_block(body),
            ]
            notes.append(f"Line {number}: {line}")
            if j < n and peek_upper(j) == "ELSE":
                else_body, j = translate_block_body(j + 1, {"END-IF"})
                out.append("else:")
                out.extend(_indent_block(else_body))
            if j < n and peek_upper(j) == "END-IF":
                j += 1
            return out, j

        then_body, j = translate_block_body(start + 1, {"END-IF", "ELSE"})
        out = [f"if {cond}:", *_indent_block(then_body)]
        if j < n and peek_upper(j) == "ELSE":
            else_body, j = translate_block_body(j + 1, {"END-IF"})
            out.append("else:")
            out.extend(_indent_block(else_body))
        if j < n and peek_upper(j) == "END-IF":
            j += 1
        return out, j

    def translate_evaluate(start: int) -> tuple[list[str], int]:
        number, line = lines[start]
        match = EVALUATE_HEAD.fullmatch(line)
        if match is None:
            notes.append(f"Line {number}: {line}")
            return [f"# TODO: COBOL line {number}: {line}"], start + 1
        subject = match.group(1).strip()
        subject_upper = subject.upper()
        is_true = subject_upper == "TRUE"
        subject_expr: str | None = "True" if is_true else translate_condition(subject, model)
        if subject_expr is None and not is_true:
            # Try as value/field for EVALUATE WS-RESULT style.
            val = translate_value(subject, model)
            subject_expr = val.code if val else None
        if subject_expr is None:
            notes.append(f"Line {number}: {line}")
            body, j = translate_block_body(start + 1, {"END-EVALUATE"})
            if j < n and peek_upper(j) == "END-EVALUATE":
                j += 1
            return [f"# TODO: COBOL line {number}: {line}", *body], j

        j = start + 1
        out: list[str] = []
        branch_index = 0
        while j < n:
            number_w, when_line = lines[j]
            wu = when_line.upper()
            if wu == "END-EVALUATE":
                j += 1
                break
            if not wu.startswith("WHEN "):
                notes.append(f"Line {number_w}: {when_line}")
                out.append(f"# TODO: COBOL line {number_w}: {when_line}")
                j += 1
                continue
            when_match = WHEN_HEAD.fullmatch(when_line)
            assert when_match is not None
            when_text = when_match.group(1).strip()
            when_body, j = translate_block_body(j + 1, {"WHEN", "END-EVALUATE"})
            if when_text.upper() == "OTHER":
                if branch_index:
                    out.append("else:")
                else:
                    out.append("if True:")
                out.extend(_indent_block(when_body))
                branch_index += 1
                continue

            if is_true:
                cond = translate_condition(when_text, model)
            else:
                when_val = translate_value(when_text, model)
                cond = None if when_val is None else f"({subject_expr} == {when_val.code})"

            if cond is None:
                notes.append(f"Line {number_w}: {when_line}")
                out.append(f"# TODO: COBOL line {number_w}: {when_line}")
                out.extend(when_body)
                continue

            if branch_index == 0:
                out.append(f"if {cond}:")
            else:
                out.append(f"elif {cond}:")
            out.extend(_indent_block(when_body))
            branch_index += 1

        if not out:
            out = ["pass"]
        return out, j

    def translate_perform_until(start: int) -> tuple[list[str], int]:
        number, line = lines[start]
        match = PERFORM_UNTIL.fullmatch(line)
        if match is None:
            notes.append(f"Line {number}: {line}")
            return [f"# TODO: COBOL line {number}: {line}"], start + 1
        cond = translate_condition(match.group(1), model)
        body, j = translate_block_body(start + 1, {"END-PERFORM"})
        if j < n and peek_upper(j) == "END-PERFORM":
            j += 1
        if cond is None:
            notes.append(f"Line {number}: {line}")
            return [f"# TODO: COBOL line {number}: {line}", *body], j
        return [f"while not ({cond}):", *_indent_block(body)], j

    def translate_perform_varying(start: int) -> tuple[list[str], int]:
        number, line = lines[start]
        match = PERFORM_VARYING.fullmatch(line)
        if match is None:
            notes.append(f"Line {number}: {line}")
            return [f"# TODO: COBOL line {number}: {line}"], start + 1
        var_name, from_text, by_text, until_text = match.groups()
        var = resolve_name(var_name, model)
        from_v = translate_value(from_text, model)
        by_v = translate_value(by_text, model)
        cond = translate_condition(until_text, model)
        body, j = translate_block_body(start + 1, {"END-PERFORM"})
        if j < n and peek_upper(j) == "END-PERFORM":
            j += 1
        if None in (var, from_v, by_v, cond):
            notes.append(f"Line {number}: {line}")
            return [f"# TODO: COBOL line {number}: {line}", *body], j
        assert var is not None and from_v is not None and by_v is not None and cond is not None
        inner = [*body, f"{var.code} += {by_v.code}"]
        return [
            f"{var.code} = {from_v.code}",
            f"while not ({cond}):",
            *_indent_block(inner),
        ], j

    while i < n:
        number, line = lines[i]
        if not line:
            i += 1
            continue
        upper = line.upper()
        if upper.startswith("PROCEDURE DIVISION"):
            i += 1
            continue
        if is_paragraph_header(line):
            current = []
            paragraphs.append((upper, current))
            i += 1
            continue
        if upper.startswith("IF "):
            chunk, i = translate_if(i)
            emit_target().extend(chunk)
            continue
        if upper.startswith("EVALUATE "):
            chunk, i = translate_evaluate(i)
            emit_target().extend(chunk)
            continue
        if upper.startswith("PERFORM UNTIL "):
            chunk, i = translate_perform_until(i)
            emit_target().extend(chunk)
            continue
        if upper.startswith("PERFORM VARYING "):
            chunk, i = translate_perform_varying(i)
            emit_target().extend(chunk)
            continue

        translated = translate_simple_statement(line, model, paragraph_order, call_targets)
        if translated is None:
            note_todo(number, line)
        else:
            emit_target().append(translated)
        i += 1

    return preamble, paragraphs, notes, call_targets


def is_paragraph_header(line: str) -> bool:
    """True when the procedure line is a paragraph name (single word)."""
    if not FIELD_NAME.fullmatch(line):
        return False
    upper = line.upper()
    return not (upper in NOT_PARAGRAPH_NAMES or upper.startswith("END-"))


def build_script(
    program_name: str,
    storage: list[str],
    preamble: list[str],
    paragraphs: list[tuple[str, list[str]]],
    field_vars: list[str],
    *,
    using_params: list[str] | None = None,
    return_name: str | None = None,
    call_targets: list[str] | None = None,
) -> str:
    """Wrap storage, optional preamble, and paragraphs in runnable Python.

    Standalone programs get ``main()``. Programs with ``PROCEDURE DIVISION USING``
    get a module-level function named after the PROGRAM-ID that takes the
    linkage parameters and returns ``return_name`` when set.

    Args:
        program_name: Used in the header comment and callee function name.
        storage: Field assignments (and storage-section TODO comments).
        preamble: Procedure statements before the first paragraph.
        paragraphs: ``(COBOL_NAME, body_lines)`` in source order.
        field_vars: Python names of storage fields (for ``nonlocal``).
        using_params: Python parameter names for a callee program.
        return_name: Python name to ``return`` from a callee (last elementary).
        call_targets: Callee function names to stub so a single-file draft runs
            before the converted callee is loaded into the same namespace.

    Returns:
        The full script.

    Example:
        >>> print(build_script("EMPTY", [], [], [], []))
        # Draft conversion of EMPTY. Review TODO lines before use.
        from legacylift.cobol.runtime import cobol_number, cobol_text, display_number
        <BLANKLINE>
        def main():
            pass
        <BLANKLINE>
        <BLANKLINE>
        if __name__ == '__main__':
            main()
        <BLANKLINE>
    """
    is_callee = bool(using_params)
    fn_name = variable_name(program_name) if is_callee else "main"
    params = ", ".join(using_params or [])

    stubs: list[str] = []
    if not is_callee and call_targets:
        for target in call_targets:
            stubs.append(f"def {target}(*_args):")
            stubs.append('    """Stub until the converted callee is loaded."""')
            stubs.append("    return _args[-1] if _args else None")
            stubs.append("")

    body: list[str] = [*storage]
    ", ".join(field_vars)

    for cobol_name, para_lines in paragraphs:
        nested = variable_name(cobol_name)
        body.append(f"def {nested}():")
        chunk: list[str] = []
        # Nested functions need nonlocal for storage; linkage params are enclosing
        # locals too when this is a callee — include them.
        extra = list(field_vars)
        if is_callee:
            for p in using_params or []:
                if p not in extra:
                    extra.append(p)
        nl = ", ".join(extra)
        if nl:
            chunk.append(f"nonlocal {nl}")
        usable = [line for line in para_lines if line != ""]
        chunk.extend(usable if usable else ["pass"])
        body.extend(f"    {line}" for line in chunk)

    if preamble:
        body.extend(preamble)
    elif paragraphs:
        body.append(f"{variable_name(paragraphs[0][0])}()")

    if is_callee and return_name:
        # GOBACK/STOP at top level must return the OUT elementary; nested paragraph
        # returns only exit the nested def, so also append a final return.
        body = [f"return {return_name}" if line == "return" else line for line in body]
        top = [
            line
            for line in body
            if not line.startswith("#")
            and not line.startswith("def ")
            and not line.startswith("    ")
        ]
        if not top or not top[-1].startswith("return"):
            body.append(f"return {return_name}")

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
            "from legacylift.cobol.runtime import cobol_number, cobol_text, display_number",
            "",
            "def main():",
            *(f"    {line}" for line in body),
            "",
            "",
            "if __name__ == '__main__':",
            "    main()",
            "",
        ]
    )


def translate_program(
    source: str,
    copybooks: dict[str, str] | None = None,
) -> PythonDraft:
    """Translate one COBOL program into a Python draft.

    Args:
        source: The full text of one ``.cbl`` or ``.cob`` file.
        copybooks: Optional map of copybook file name / stem → text. When
            provided, ``COPY name`` is expanded before translation.

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
        >>> 'cobol_number(ws_total + 5' in draft.python
        True
    """
    source = expand_copybooks(source, copybooks)
    numbered_lines = [
        (number, clean_line(raw_line).removesuffix(".").rstrip())
        for number, raw_line in enumerate(source.splitlines(), start=1)
    ]
    all_code = "\n".join(line.strip() for _, line in numbered_lines if line.strip())
    program_id = PROGRAM_ID.search(all_code)
    proc_match = PROCEDURE_DIVISION.search(all_code)
    if program_id is None or proc_match is None:
        raise ConversionError("File needs PROGRAM-ID and PROCEDURE DIVISION.")

    using_raw = proc_match.group(1)
    using_cobol: list[str] = []
    if using_raw:
        using_cobol = [m.group(0).upper() for m in FIELD_NAME.finditer(using_raw)]

    model, linkage_from_section = build_field_model(
        numbered_lines, accept_linkage=bool(using_cobol)
    )
    # Prefer PROCEDURE DIVISION USING order; fall back to linkage section order.
    using_names = using_cobol or linkage_from_section

    # Register linkage params as fields (dict or scalar) for name resolution.
    for cobol in using_names:
        py = variable_name(cobol)
        if cobol not in model.fields:
            model.fields[cobol] = Value(py, False)

    paragraph_order: list[str] = []
    in_procedure = False
    for _, line in numbered_lines:
        upper = line.strip().upper()
        if upper.startswith("PROCEDURE DIVISION"):
            in_procedure = True
            continue
        if in_procedure and line.strip() and is_paragraph_header(line):
            paragraph_order.append(upper)

    for number, line in numbered_lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper == "WORKING-STORAGE SECTION":
            section = "storage"
            continue
        if upper.startswith("PROCEDURE DIVISION"):
            section = "procedure"
            continue
        if not stripped or not section:
            continue
        if not in_procedure:
            continue
        if line and is_paragraph_header(line):
            paragraph_order.append(upper)
        proc_lines.append((number, line))

        translated = translate_line(section, stripped, fields, paragraph_order)
        if translated is None:
            todo = f"# TODO: COBOL line {number}: {stripped}"
            notes.append(f"Line {number}: {stripped}")
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

    program_name = program_id.group(1)
    using_params_py = [variable_name(n) for n in using_names] if using_names else None

    return_name: str | None = None
    if using_names:
        # Last elementary USING item (not a group that owns children).
        for cobol in reversed(using_names):
            is_group = any(
                model.fields.get(cobol, Value("", False)).code == g
                for g, _k, _n, _f in model.group_children.values()
            )
            if is_group:
                continue
            if cobol in model.fields:
                return_name = model.fields[cobol].code
                break
            return_name = variable_name(cobol)
            break

    python = build_script(
        program_name,
        model.init_lines,
        preamble,
        paragraphs,
        model.scalar_vars,
        using_params=using_params_py,
        return_name=return_name,
        call_targets=call_targets,
    )
    return PythonDraft(program_name=program_name, python=python, notes=notes)


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
