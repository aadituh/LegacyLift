"""Ask Gemini whether generated Python preserves a COBOL program.

``build_prompt`` puts the COBOL, the Python, and the converter's review notes
in one request. ``request_gemini_review`` posts that prompt and returns
matches and concerns with the line numbers they refer to. The route and the
tests call these functions; tests replace ``request_gemini_review``.

The model is Gemini 2.5 Flash: it follows a JSON schema and is fast enough
for a per-program review. The API key is passed in a header and is not written
into the prompt or the response.
"""

import json
import urllib.error
import urllib.request
from typing import cast

from pydantic import BaseModel, ValidationError

from legacylift.errors import AIReviewError
from legacylift.models import LineFinding

GEMINI_MODEL = "gemini-3.5-flash-lite"
_GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


def _finding_schema() -> dict[str, object]:
    """JSON schema for one match or concern. Gemini uses these type names."""
    return {
        "type": "OBJECT",
        "properties": {
            "cobol_lines": {"type": "ARRAY", "items": {"type": "INTEGER"}},
            "python_lines": {"type": "ARRAY", "items": {"type": "INTEGER"}},
            "detail": {"type": "STRING"},
        },
        "required": ["cobol_lines", "python_lines", "detail"],
    }


# Field names match LineFinding. Inlined twice: Gemini's schema does not use $ref.
_RESPONSE_SCHEMA: dict[str, object] = {
    "type": "OBJECT",
    "properties": {
        "matches": {"type": "ARRAY", "items": _finding_schema()},
        "concerns": {"type": "ARRAY", "items": _finding_schema()},
    },
    "required": ["matches", "concerns"],
}


class ProgramFindings(BaseModel):
    """Matches and concerns for one program, before file names are attached."""

    matches: list[LineFinding]
    concerns: list[LineFinding]


def build_prompt(cobol: str, python_source: str, notes: list[str]) -> str:
    """Build the review prompt from the COBOL, the Python, and the review notes.

    Args:
        cobol: The original program.
        python_source: The generated Python draft.
        notes: ``"Line N: ..."`` notes for lines the converter could not prove.

    Returns:
        The prompt sent to Gemini. Line numbers in it are 1-based.

    Example:
        >>> "COBOL" in build_prompt("DISPLAY 1.", "print(1)", ["Line 1: DISPLAY 1"])
        True
    """
    note_block = "\n".join(f"- {note}" for note in notes) if notes else "(none)"
    return (
        "Compare this COBOL program with the Python draft a rule-based converter produced.\n"
        "The review notes are lines those rules could not prove. Check those lines first, "
        "then flag any other place the Python may not preserve COBOL behavior.\n"
        "A match is behavior you can justify from both sources. "
        "A concern is unproven, missing, or possibly different behavior.\n"
        "cobol_lines and python_lines are 1-based line numbers from the numbered sources. "
        "Use an empty list when a side has no corresponding line. "
        "detail is one sentence. Do not invent line numbers that are not shown.\n\n"
        f"COBOL:\n{_numbered(cobol)}\n\n"
        f"Python:\n{_numbered(python_source)}\n\n"
        f"Review notes:\n{note_block}\n"
    )


def request_gemini_review(prompt: str, *, api_key: str, timeout: float) -> ProgramFindings:
    """Send ``prompt`` to Gemini and parse the JSON review.

    Args:
        prompt: Text from ``build_prompt``.
        api_key: Gemini API key. Sent as a header, not in the URL.
        timeout: Seconds to wait for the response.

    Returns:
        The matches and concerns Gemini reported.

    Raises:
        AIReviewError: The request failed, timed out, or was not the expected JSON.
    """
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": _RESPONSE_SCHEMA,
        },
    }
    request = urllib.request.Request(
        _GEMINI_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
    except TimeoutError as error:
        raise AIReviewError("The AI review timed out.") from error
    except urllib.error.HTTPError as error:
        raise AIReviewError("Gemini rejected the AI review request.") from error
    except urllib.error.URLError as error:
        raise AIReviewError("The AI review could not reach Gemini.") from error
    return _parse_model_response(raw)


def _numbered(source: str) -> str:
    """Prefix each line with its 1-based line number."""
    return "\n".join(f"{number}|{line}" for number, line in enumerate(source.splitlines(), start=1))


def _parse_model_response(raw: str) -> ProgramFindings:
    """Read Gemini's HTTP body and validate the review JSON."""
    try:
        payload = cast(object, json.loads(raw))
    except json.JSONDecodeError as error:
        raise AIReviewError("Gemini returned a review that was not the expected JSON.") from error
    return _parse_findings(_review_text(payload))


def _review_text(payload: object) -> str:
    """Return the text part of the first Gemini candidate."""
    if not isinstance(payload, dict):
        raise AIReviewError("Gemini returned a review that was not the expected JSON.")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise AIReviewError("Gemini returned a review that was not the expected JSON.")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise AIReviewError("Gemini returned a review that was not the expected JSON.")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], dict):
        raise AIReviewError("Gemini returned a review that was not the expected JSON.")
    text = parts[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise AIReviewError("Gemini returned a review that was not the expected JSON.")
    return text


def _parse_findings(text: str) -> ProgramFindings:
    """Validate the JSON object Gemini was asked to return."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return ProgramFindings.model_validate(cast(object, json.loads(cleaned)))
    except (json.JSONDecodeError, ValidationError) as error:
        raise AIReviewError("Gemini returned a review that was not the expected JSON.") from error
