"""Prompt and response shape for a plain-language dependency map.

``build_prompt`` turns parsed programs and their links into text. ``complete``
sends that text to Gemini. ``describe_map`` parses the model's JSON.
"""

import json
from collections.abc import Callable, Sequence

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from legacylift.cobol.dependencies import Dependency, UnresolvedRef, find_dependencies
from legacylift.cobol.parser import ParsedProgram
from legacylift.errors import ProjectStateError

GEMINI_MODEL = "gemini-2.5-flash"


class ProgramDescription(BaseModel):
    """What one COBOL program does."""

    name: str
    summary: str


class DependencyMap(BaseModel):
    """Plain-language map of a project: each program, and the data they share."""

    programs: list[ProgramDescription]
    shared_data: str


def _division_lines(program: ParsedProgram, name: str) -> list[str]:
    """Source lines of one division, or an empty list if that division is absent."""
    for division in program.divisions:
        if division.name == name:
            return [line.text.rstrip() for line in division.lines]
    return []


def build_prompt(
    programs: Sequence[ParsedProgram],
    dependencies: Sequence[Dependency],
    unresolved: Sequence[UnresolvedRef],
    file_names: Sequence[str],
) -> str:
    """Build the Gemini prompt from parsed programs and their links.

    Args:
        programs: Parsed ``.cbl`` and ``.cob`` files.
        dependencies: Resolved COPY, CALL, and PERFORM links.
        unresolved: Names that did not match a project file or paragraph.
        file_names: Every file in the project, including ``.dat`` and ``.cpy``.

    Returns:
        The prompt text. The model is asked for JSON matching ``DependencyMap``.
    """
    sections = [
        "Describe this COBOL project in plain language.",
        "Project files:",
        "\n".join(file_names),
        "Links:",
    ]
    sections.extend(
        f"{item.kind.value} {item.source} -> {item.target} (line {item.line})"
        for item in dependencies
    )
    if unresolved:
        sections.append("Unresolved:")
        sections.extend(
            f"{item.kind.value} {item.source} -> {item.name} (line {item.line})"
            for item in unresolved
        )
    for program in programs:
        fields = [f"{field.level} {field.name} ({field.section})" for field in program.fields]
        paragraphs = [paragraph.name for paragraph in program.paragraphs]
        environment = _division_lines(program, "ENVIRONMENT")
        sections.append(
            "\n".join(
                [
                    f"Program {program.name} PROGRAM-ID {program.program_id}",
                    "Paragraphs: " + ", ".join(paragraphs),
                    "Fields: " + ", ".join(fields),
                    "Environment:",
                    *environment,
                ]
            )
        )
    sections.append(
        'Return only JSON: {"programs": [{"name": "FILE.cbl", "summary": "..."}], '
        '"shared_data": "..."}. '
        "name is the file name. shared_data says which files and copybooks the programs share."
    )
    return "\n\n".join(sections)


def _json_object(raw: str) -> str:
    """Drop a ```json fence if the model wrapped the object."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()


def complete(prompt: str, api_key: str) -> str:
    """Send the prompt to Gemini and return the response text.

    Args:
        prompt: The text from ``build_prompt``.
        api_key: ``LEGACYLIFT_GEMINI_API_KEY``.

    Returns:
        The model's text.

    Raises:
        ProjectStateError: Gemini returned no text.
    """
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    if not response.text:
        raise ProjectStateError("Gemini returned an empty description.")
    return response.text


def describe_map(
    programs: Sequence[ParsedProgram],
    file_names: Sequence[str],
    *,
    api_key: str | None,
    complete_prompt: Callable[[str, str], str] | None = None,
) -> DependencyMap:
    """Turn parsed programs into a plain-language dependency map.

    Args:
        programs: Parsed ``.cbl`` and ``.cob`` files.
        file_names: Every file in the project.
        api_key: Gemini key. Missing or blank skips the model call.
        complete_prompt: Replacement for ``complete``. Tests pass a fake.

    Returns:
        The parsed map.

    Raises:
        ProjectStateError: No API key, or the model text is not a ``DependencyMap``.
    """
    if not api_key:
        raise ProjectStateError("Set LEGACYLIFT_GEMINI_API_KEY before describing a project.")
    dependencies, unresolved = find_dependencies(programs, file_names)
    prompt = build_prompt(programs, dependencies, unresolved, file_names)
    send = complete if complete_prompt is None else complete_prompt
    raw = send(prompt, api_key)
    try:
        return DependencyMap.model_validate_json(_json_object(raw))
    except (ValidationError, json.JSONDecodeError) as error:
        raise ProjectStateError(
            "Gemini returned a description that was not the expected JSON."
        ) from error
