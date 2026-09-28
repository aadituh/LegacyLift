"""
End-to-end COBOL modernization pipeline for the web shell and console.

Mirrors notebooks/01–03:
  1. Parse COBOL (preprocessing)
  2. Detect patterns (unsupervised clustering)
  3. Generate functionally oriented OOP Python
  4. Return structured results for ``index.html`` and server logs
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.cobol_parser import parse_cobol, parse_cobol_source
from src.models import cluster_procedural_patterns
from src.refactorer import OOPRefactorer
from src.translator import clean_identifier

logger = logging.getLogger("legacylift.pipeline")

CobolInput = Union[str, Path]


def _configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def analyze_source(source: str, filename: str = "input.cbl") -> Dict[str, Any]:
    """
    Notebook-style analysis of COBOL text.

    Returns program metadata, attributes, methods, paragraphs, and cluster IDs.
    """
    _configure_logging()
    logger.info("Analyzing COBOL input (%s), %d chars", filename, len(source))
    parsed = parse_cobol_source(source)
    paragraphs = parsed.get("raw_paragraphs") or []
    texts = [body if body.strip() else name for name, body in paragraphs]
    if len(texts) >= 2:
        clusters = cluster_procedural_patterns(
            texts, n_clusters=min(4, len(texts))
        )
    else:
        clusters = [0] * len(texts)

    cluster_map = [
        {"paragraph": name, "cluster": int(clusters[i]) if i < len(clusters) else 0}
        for i, (name, _) in enumerate(paragraphs)
    ]
    result = {
        "filename": filename,
        "program_name": parsed.get("program_name"),
        "attributes": parsed.get("potential_attributes"),
        "methods": parsed.get("potential_methods"),
        "paragraphs": [
            {"name": name, "body": body} for name, body in paragraphs
        ],
        "clusters": cluster_map,
    }
    logger.info(
        "Parsed program=%s attributes=%d methods=%d",
        result["program_name"],
        len(result["attributes"] or []),
        len(result["methods"] or []),
    )
    return result


def analyze_file(path: CobolInput) -> Dict[str, Any]:
    """Analyze a COBOL file from disk."""
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    return analyze_source(source, filename=file_path.name)


def convert_source(
    source: str,
    filename: str = "input.cbl",
    *,
    use_ml_clustering: bool = True,
) -> Dict[str, Any]:
    """
    Convert COBOL source to Python and build console-facing log lines.

    Returns
    -------
    dict
        filename, analysis, python, console_log
    """
    _configure_logging()
    logger.info("Converting COBOL -> Python (%s)", filename)
    analysis = analyze_source(source, filename=filename)
    refactorer = OOPRefactorer(use_ml_clustering=use_ml_clustering)
    python_code = refactorer.refactor_source(source)

    console_lines = [
        "ML-Driven Legacy Code Modernization",
        f"Input: {filename}",
        f"Program: {analysis.get('program_name')}",
        f"Attributes: {[a['name'] for a in (analysis.get('attributes') or [])]}",
        f"Methods: {analysis.get('methods')}",
        "--- Generated Python ---",
        python_code,
    ]
    console_log = "\n".join(console_lines)
    # Mirror notebook / CLI output on the server console
    print(console_log)
    logger.info(
        "Conversion complete (%s): %d bytes of Python",
        filename,
        len(python_code),
    )
    return {
        "filename": filename,
        "analysis": analysis,
        "python": python_code,
        "console_log": console_log,
        "entry_class": _guess_entry_class(analysis.get("program_name") or "UNKNOWN"),
    }


def convert_file(path: CobolInput, **kwargs: Any) -> Dict[str, Any]:
    """Convert a COBOL file from disk."""
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    return convert_source(source, filename=file_path.name, **kwargs)


def _guess_entry_class(program_name: str) -> str:
    return clean_identifier(program_name).title().replace("_", "") + "Class"
