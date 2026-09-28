"""
Rule-based COBOL statement → Python statement translator.

Used by ``OOPRefactorer`` to emit functionally equivalent method bodies for
common procedural COBOL (ADD, SUBTRACT, COMPUTE, MOVE, DISPLAY, PERFORM, IF).
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence


def clean_identifier(name: str) -> str:
    """Convert a COBOL name (ACCOUNT-BALANCE) to a Python identifier."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unknown"


def map_pic_to_type(pic: str) -> str:
    pic = (pic or "").upper()
    if any(token in pic for token in ("S9", "V9", "9V", "V99")):
        return "Decimal"
    if "9" in pic:
        return "int"
    if "X" in pic:
        return "str"
    return "Any"


def default_value_for_pic(pic: str) -> str:
    py_type = map_pic_to_type(pic)
    if py_type == "Decimal":
        return "Decimal('0.00')"
    if py_type == "int":
        return "0"
    if py_type == "str":
        return "''"
    return "None"


class CobolTranslator:
    """Translate COBOL paragraph bodies into indented Python statements."""

    def __init__(self, field_names: Sequence[str]):
        self.field_map: Dict[str, str] = {
            name.upper(): clean_identifier(name) for name in field_names
        }
        # Longest names first so ACCOUNT-BALANCE beats ACCOUNT / BALANCE
        self._field_pattern = self._build_field_pattern()

    def _build_field_pattern(self) -> re.Pattern[str] | None:
        if not self.field_map:
            return None
        names = sorted(self.field_map.keys(), key=len, reverse=True)
        return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")

    def attr(self, cobol_name: str) -> str:
        key = cobol_name.upper().strip()
        py_name = self.field_map.get(key, clean_identifier(key))
        return f"self.{py_name}"

    def _replace_fields(self, expression: str) -> str:
        if not self._field_pattern:
            return expression

        def repl(match: re.Match[str]) -> str:
            return self.attr(match.group(1))

        return self._field_pattern.sub(repl, expression)

    def _translate_display(self, statement: str) -> str:
        # DISPLAY "text" VAR "more" VAR2.
        parts = re.findall(
            r'"([^"]*)"|\'([^\']*)\'|([A-Z0-9][A-Z0-9-]*)',
            statement,
            re.IGNORECASE,
        )
        chunks: List[str] = []
        for double, single, ident in parts:
            if double or single:
                text = double or single
                chunks.append(repr(text))
            elif ident and ident.upper() not in {"DISPLAY"}:
                if ident.upper() in self.field_map:
                    chunks.append(f"{{{self.attr(ident)}}}")
                else:
                    chunks.append(repr(ident))
        if not chunks:
            return 'print("")'
        # Mix literals and f-string field inserts
        if any(c.startswith("{") for c in chunks):
            pieces = []
            for c in chunks:
                if c.startswith("{") and c.endswith("}"):
                    pieces.append(c)
                else:
                    # strip quotes from repr for embedding in f-string
                    pieces.append(c[1:-1] if c.startswith(("'", '"')) else c)
            return 'print(f"' + "".join(pieces) + '")'
        return "print(" + " + ".join(chunks) + ")"

    def _translate_compute(self, statement: str) -> List[str]:
        # COMPUTE TOTAL-PAY = HOURS-WORKED * HOURLY-RATE
        # COMPUTE WS-INTEREST ROUNDED = A * B / C
        match = re.search(
            r"COMPUTE\s+([A-Z0-9-]+)\s+(?:ROUNDED\s+)?=\s*(.+)$",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported COMPUTE: {statement}"]
        target = self.attr(match.group(1))
        expr = self._replace_fields(match.group(2).rstrip("."))
        expr = expr.replace("/", " / ").replace("*", " * ")
        return [f"{target} = {expr}"]

    def _translate_add(self, statement: str) -> List[str]:
        # ADD A TO B  |  ADD A B TO C  |  ADD 1 TO COUNTER
        match = re.search(
            r"ADD\s+(.+?)\s+TO\s+([A-Z0-9-]+)",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported ADD: {statement}"]
        sources = match.group(1).strip()
        target = self.attr(match.group(2))
        source_tokens = re.split(r"\s+", sources)
        lines = []
        for token in source_tokens:
            if re.fullmatch(r"[A-Z0-9-]+", token, re.IGNORECASE):
                if token.upper() in self.field_map or "-" in token:
                    lines.append(f"{target} += {self.attr(token)}")
                elif re.fullmatch(r"\d+(\.\d+)?", token):
                    lines.append(f"{target} += {token}")
                else:
                    lines.append(f"{target} += {self.attr(token)}")
            else:
                lines.append(f"{target} += {token}")
        return lines or [f"# TODO: unsupported ADD: {statement}"]

    def _translate_subtract(self, statement: str) -> List[str]:
        match = re.search(
            r"SUBTRACT\s+(.+?)\s+FROM\s+([A-Z0-9-]+)",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported SUBTRACT: {statement}"]
        source = match.group(1).strip()
        target = self.attr(match.group(2))
        if re.fullmatch(r"\d+(\.\d+)?", source):
            rhs = source
        else:
            rhs = self.attr(source.split()[0])
        return [f"{target} -= {rhs}"]

    def _translate_move(self, statement: str) -> List[str]:
        match = re.search(
            r"MOVE\s+(.+?)\s+TO\s+([A-Z0-9-]+)",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported MOVE: {statement}"]
        source_raw = match.group(1).strip().rstrip(".")
        target = self.attr(match.group(2))
        if source_raw.upper() in {"ZERO", "ZEROS", "ZEROES"}:
            source = "0"
        elif source_raw.upper() in {"SPACE", "SPACES"}:
            source = "''"
        elif source_raw.startswith(("'", '"')):
            source = source_raw
        elif re.fullmatch(r"\d+(\.\d+)?", source_raw):
            source = source_raw
        else:
            source = self.attr(source_raw)
        return [f"{target} = {source}"]

    def _translate_perform(self, statement: str) -> List[str]:
        match = re.search(
            r"PERFORM\s+([A-Z0-9-]+)",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported PERFORM: {statement}"]
        method = clean_identifier(match.group(1))
        return [f"self.{method}()"]

    def _translate_condition(self, condition: str) -> str:
        cond = condition.strip()
        cond = self._replace_fields(cond)
        cond = (
            cond.replace(" AND ", " and ")
            .replace(" OR ", " or ")
            .replace(" NOT ", " not ")
            .replace(" ZERO", " 0")
            .replace(" ZEROS", " 0")
            .replace(" ZEROES", " 0")
        )
        # Normalize COBOL relational operators to Python
        cond = re.sub(r"\s+>=\s+", " >= ", cond)
        cond = re.sub(r"\s+<=\s+", " <= ", cond)
        cond = re.sub(r"\s+<>\s+", " != ", cond)
        cond = re.sub(r"\s+>\s+", " > ", cond)
        cond = re.sub(r"\s+<\s+", " < ", cond)
        cond = re.sub(r"(?<![<>=!])=(?!=)", " == ", cond)
        return cond

    def _translate_if(self, statement: str) -> List[str]:
        match = re.match(
            r"IF\s+(.+?)\s+(?:THEN\s+)?(.+)$",
            statement,
            re.IGNORECASE,
        )
        if not match:
            return [f"# TODO: unsupported IF: {statement}"]
        condition = self._translate_condition(match.group(1))
        then_part = match.group(2).strip()
        # Avoid recursively treating nested IF poorly — translate remaining as statements
        then_lines = self.translate_statement(then_part)
        if not then_lines:
            then_lines = ["pass"]
        lines = [f"if {condition}:"]
        for line in then_lines:
            lines.append("    " + line)
        return lines

    def translate_statement(self, statement: str) -> List[str]:
        stmt = statement.strip().rstrip(".")
        if not stmt:
            return []
        upper = stmt.upper()
        if upper.startswith("DISPLAY"):
            return [self._translate_display(stmt)]
        if upper.startswith("COMPUTE"):
            return self._translate_compute(stmt)
        if upper.startswith("ADD"):
            return self._translate_add(stmt)
        if upper.startswith("SUBTRACT"):
            return self._translate_subtract(stmt)
        if upper.startswith("MOVE"):
            return self._translate_move(stmt)
        if upper.startswith("PERFORM"):
            return self._translate_perform(stmt)
        if upper.startswith("IF "):
            return self._translate_if(stmt)
        if upper in {"STOP RUN", "GOBACK", "EXIT", "EXIT PROGRAM"}:
            return ["return"]
        if upper.startswith(("CALL ", "OPEN ", "CLOSE ", "READ ", "WRITE ", "ACCEPT ")):
            return [f"# TODO: {stmt}"]
        return [f"# TODO: translate statement: {stmt}"]

    def _split_statements(self, body: str) -> List[str]:
        """Split a paragraph body into individual COBOL statements."""
        # Collapse END-IF / multi-line IF into flatter units
        text = re.sub(r"\s+", " ", body.replace("\n", " ")).strip()
        text = re.sub(r"\bEND-IF\b", "", text, flags=re.IGNORECASE)
        # Split on periods that terminate statements, but keep PERFORM X. style
        chunks = re.split(r"\.\s*", text)
        return [c.strip() for c in chunks if c.strip()]

    def translate_paragraph(self, body: str, indent: str = "        ") -> List[str]:
        """Return indented Python lines for a COBOL paragraph body."""
        lines: List[str] = []
        for statement in self._split_statements(body):
            for py in self.translate_statement(statement):
                lines.append(indent + py)
        if not lines:
            lines.append(indent + "pass")
        return lines
