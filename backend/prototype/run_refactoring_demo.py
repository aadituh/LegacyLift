#!/usr/bin/env python3
"""
Full Pipeline Demonstration — Python script frontend for
``notebooks/03_refactoring_demo.ipynb``.

Pipeline (identical to the notebook):
  1. Parse COBOL (preprocessing)
  2. Detect patterns (unsupervised ML via embeddings + clustering)
  3. Generate OOP Python skeleton (rule-based + ML-augmented)
  4. Compare with manual reference implementation
  5. Print qualitative evaluation summary

Dependencies
------------
Same stack as the prototype notebooks (see ``requirements.txt``):

  - pandas, numpy, scikit-learn
  - sentence-transformers  (CodeEmbedder / OOPRefactorer)
  - matplotlib, seaborn, jupyter  (notebook ecosystem; not required to run this script)

Local modules (unchanged):
  - ``src.cobol_parser.parse_cobol``
  - ``src.refactorer.OOPRefactorer``
  - ``src.models.CodeEmbedder``

Usage
-----
From the ``backend/prototype`` directory::

    python run_refactoring_demo.py

Or with an explicit COBOL input path::

    python run_refactoring_demo.py --cobol data/simple_account.cbl

This script resolves paths relative to the prototype root so it works
whether you launch it from ``prototype/`` or from another working directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Windows consoles often default to cp1252; generated code contains Unicode
# (e.g. "→") that Jupyter prints fine. Reconfigure stdout for parity.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Path setup — mirror notebook Cell 1 (`sys.path.append('..')` when run from
# notebooks/), but resolve against this file so imports stay stable.
# ---------------------------------------------------------------------------
PROTOTYPE_ROOT = Path(__file__).resolve().parent
if str(PROTOTYPE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE_ROOT))

from src.cobol_parser import parse_cobol  # noqa: E402
from src.refactorer import OOPRefactorer  # noqa: E402
from src.models import CodeEmbedder  # noqa: E402  # imported for parity with the notebook

# Default data paths (same files the notebook uses via ``../data/...``)
DEFAULT_COBOL = PROTOTYPE_ROOT / "data" / "simple_account.cbl"
DEFAULT_REFERENCE = PROTOTYPE_ROOT / "data" / "reference_account.py"

# Inline reference used by notebook Cell 5 when the reference file is absent
INLINE_REFERENCE = '''from decimal import Decimal

class AccountClass:
    def __init__(self, account_number: int = 0, owner: str = ''):
        self.number = account_number
        self.balance = Decimal('0.00')
        self.owner = owner
        self.amount = Decimal('0.00')

    def deposit(self):
        self.balance += self.amount
        print(f"Deposit processed for account {self.number}")

    def withdraw(self):
        self.balance -= self.amount
        print(f"Withdrawal processed for account {self.number}")

    def generate_report(self):
        print(f"Account Balance Report: {self.balance}")

    def run(self):
        print('=== Reference Implementation Running ===')
        self.amount = Decimal('150.00')
        self.deposit()
        self.amount = Decimal('75.50')
        self.withdraw()
        self.generate_report()
'''

EVALUATION_TEXT = """
Evaluation:
- Business logic preserved: Yes (deposit, withdrawal, report)
- Modularity improved: Flat procedures → Encapsulated class methods
- Readability: Significantly higher in Python
- Complexity reduction: Measured by fewer global variables and clearer structure
"""


def setup() -> None:
    """
    Notebook Cell 1: Setup.

    Imports are performed at module load (above). This prints the same
    banner the notebook prints after importing ``parse_cobol``,
    ``OOPRefactorer``, and ``CodeEmbedder``.
    """
    # Touch CodeEmbedder so the import is "used" and matches notebook intent
    # (the refactorer constructs its own embedder during ``refactor()``).
    _ = CodeEmbedder
    print("ML-Driven Legacy Code Modernization Demo")


def load_cobol_input(cobol_path: Path, truncate_at: int = 800) -> str:
    """
    Notebook Cell 2: Input COBOL.

    Reads the COBOL source and prints a truncated preview, matching the
    notebook's ``cobol_code[:800] + "\\n... (truncated)"`` display.

    Parameters
    ----------
    cobol_path:
        Path to a ``.cbl`` (or similar) COBOL source file.
    truncate_at:
        Number of characters to show in the console preview.

    Returns
    -------
    str
        Full COBOL source text.
    """
    with open(cobol_path, "r", encoding="utf-8", errors="ignore") as f:
        cobol_code = f.read()

    print("=== Original COBOL Code ===")
    print(cobol_code[:truncate_at] + "\n... (truncated)")
    return cobol_code


def parse_and_detect_patterns(cobol_path: Path) -> dict:
    """
    Notebook Cell 3: Parsing + Pattern Detection.

    Calls ``parse_cobol`` and prints extracted attributes and methods
    exactly as the notebook does.

    Parameters
    ----------
    cobol_path:
        Path passed through to ``src.cobol_parser.parse_cobol``.

    Returns
    -------
    dict
        Parsed structure with keys ``program_name``,
        ``potential_attributes``, ``potential_methods``, ``raw_paragraphs``.
    """
    parsed = parse_cobol(str(cobol_path))
    print(
        "Extracted Attributes:",
        [item["name"] for item in parsed["potential_attributes"]],
    )
    print("Extracted Methods:", parsed["potential_methods"])
    return parsed


def generate_oop_code(cobol_path: Path) -> str:
    """
    Notebook Cell 4: Generate Refactored OOP Code.

    Instantiates ``OOPRefactorer`` (which loads ``CodeEmbedder`` /
    sentence-transformers) and runs the full ML-augmented refactor path.

    Parameters
    ----------
    cobol_path:
        COBOL file path for ``OOPRefactorer.refactor``.

    Returns
    -------
    str
        Generated Python OOP source as a single string.
    """
    refactorer = OOPRefactorer()
    python_code = refactorer.refactor(str(cobol_path))

    print("=== Generated Python OOP Code ===")
    print(python_code)
    return python_code


def compare_with_reference(reference_path: Optional[Path] = None) -> None:
    """
    Notebook Cell 5: Comparison with Manual Reference (safe version).

    Tries to open ``reference_account.py`` (notebook path). On
    ``FileNotFoundError``, prints the same inline reference string the
    notebook uses.

    Parameters
    ----------
    reference_path:
        Optional override for the reference Python file. Defaults to the
        notebook's ``reference_account.py`` path under ``data/``.
    """
    print("=== Manual Reference Python OOP (Ground Truth) ===")

    path = reference_path or DEFAULT_REFERENCE

    try:
        with open(path, "r", encoding="utf-8") as f:
            print(f.read())
    except FileNotFoundError:
        print("Reference file not found. Using inline reference version instead.\n")
        print(INLINE_REFERENCE)


def print_evaluation() -> None:
    """
    Notebook Cell 6: Qualitative Evaluation.

    Prints the same evaluation blurb as the notebook.
    """
    print(EVALUATION_TEXT)


def run_full_pipeline(cobol_path: Path, reference_path: Optional[Path] = None) -> str:
    """
    Execute the complete demonstration pipeline in notebook order.

    Parameters
    ----------
    cobol_path:
        Input COBOL program.
    reference_path:
        Optional ground-truth Python OOP file for the comparison step.

    Returns
    -------
    str
        The generated OOP Python source from ``OOPRefactorer.refactor``.
    """
    setup()
    load_cobol_input(cobol_path)
    parse_and_detect_patterns(cobol_path)
    python_code = generate_oop_code(cobol_path)
    compare_with_reference(reference_path)
    print_evaluation()
    return python_code


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI matching the notebook defaults while allowing overrides."""
    parser = argparse.ArgumentParser(
        description=(
            "Script frontend for notebooks/03_refactoring_demo.ipynb — "
            "parse COBOL, cluster procedural patterns, generate OOP Python, "
            "and compare with a manual reference."
        )
    )
    parser.add_argument(
        "--cobol",
        type=Path,
        default=DEFAULT_COBOL,
        help=f"Path to COBOL source (default: {DEFAULT_COBOL})",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help=(
            "Optional path to reference OOP Python. "
            f"Defaults to {DEFAULT_REFERENCE}; on missing file, uses the "
            "notebook's inline reference fallback."
        ),
    )
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional path to write the generated Python OOP code (UTF-8).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Entry point.

    Returns
    -------
    int
        Process exit code (0 on success, 1 on missing COBOL input).
    """
    args = build_arg_parser().parse_args(argv)
    cobol_path = args.cobol.resolve()

    if not cobol_path.is_file():
        print(f"Error: COBOL file not found: {cobol_path}", file=sys.stderr)
        return 1

    python_code = run_full_pipeline(cobol_path, args.reference)

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(python_code, encoding="utf-8")
        print(f"\nSaved generated code to: {args.save}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
