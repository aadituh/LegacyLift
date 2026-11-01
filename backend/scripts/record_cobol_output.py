"""Record what GnuCOBOL prints for the sample programs, for the tests to compare against.

Run it where ``cobc`` is installed, such as the runner image. From the repository root:

    docker compose run --rm --no-deps -v ./backend:/backend runner \
        python /backend/scripts/record_cobol_output.py

Writes ``tests/data/recorded/FEESCHED.out``, ``MONTHEND.out``, and, for each folder in
``tests/data/recorded/bank/``, ``BANKMAIN.out`` from that folder's ``accounts.dat``
and ``transactions.dat`` (the ``sample`` folder uses the files in
``src/legacylift/data/``).
"""

import sys
from pathlib import Path

from legacylift.runner.sandbox import run_cobol

BACKEND = Path(__file__).resolve().parents[1]
SAMPLE = BACKEND / "src" / "legacylift" / "data"
RECORDED = BACKEND / "tests" / "data" / "recorded"


def read(folder: Path, *names: str) -> dict[str, str]:
    """Read files from a folder as ``{name: text}``."""
    return {name: (folder / name).read_text(encoding="utf-8") for name in names}


def record(
    out: Path, *programs: str, copybooks: tuple[str, ...] = (), data: Path | None = None
) -> None:
    """Run ``programs`` (the first is the main one) and save exactly what it prints.

    Raises:
        SystemExit: The program did not compile or run cleanly.
    """
    data_files = read(data, "accounts.dat", "transactions.dat") if data else {}
    result = run_cobol(
        read(SAMPLE, *programs),
        main=programs[0],
        copybooks=read(SAMPLE, *copybooks),
        data_files=data_files,
    )
    if not result.ok:
        sys.exit(f"{out.name}: {result.stage} failed\n{result.stderr}")
    out.write_text(result.stdout, encoding="utf-8", newline="\n")  # keeps trailing spaces
    print(f"recorded {out.relative_to(BACKEND)}")


def main() -> None:
    """Record every program and bank case."""
    record(RECORDED / "FEESCHED.out", "FEESCHED.cbl")
    record(RECORDED / "MONTHEND.out", "MONTHEND.cbl", copybooks=("FEERATES.cpy",))
    for case in sorted(path for path in (RECORDED / "bank").iterdir() if path.is_dir()):
        record(
            case / "BANKMAIN.out",
            "BANKMAIN.cbl",
            "TXNPOST.cbl",
            "INTCALC.cbl",
            copybooks=("ACCTDEF.cpy", "TXNDEF.cpy"),
            data=SAMPLE if case.name == "sample" else case,
        )


if __name__ == "__main__":
    main()
