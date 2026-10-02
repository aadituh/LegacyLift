# Research prototype

Early COBOL-to-Python experiments: a regex parser and KMeans clustering that group COBOL paragraphs into Python classes. The design deck's Driver, Implementation, and Output slides show this code.

It is **not** part of the running API. The API's converter is [`src/legacylift/cobol/converter.py`](../src/legacylift/cobol/converter.py), and nothing here is imported by it.

| Path | Contents |
| --- | --- |
| `data/` | Sample COBOL (`BANKMAIN`, `INTCALC`, `ACCTDEF`, and others) and a reference Python file |
| `notebooks/` | Data exploration, pattern detection, and refactoring demos |
| `src/` | Parser, translator, refactorer, and pipeline |
| `run_demo.py`, `run_refactoring_demo.py` | Standalone demo scripts |
| `requirements.txt` | Dependencies for this folder only |

To run it, create a separate virtual environment and install `requirements.txt`; do not add these packages to `backend/pyproject.toml`. Scripts write to `output/`, which Git ignores.
