# Research prototype

This directory holds earlier COBOL conversion experiments, sample files, notebooks, and demo scripts. It is separate from the active FastAPI and React demo. The web app uses `backend/src/legacylift/converter.py`, not this directory's `src/pipeline.py`.

| Path | Contents |
| --- | --- |
| `data/` | Small research inputs and a reference Python file |
| `notebooks/` | Exploration and refactoring demonstrations |
| `src/` | Experimental parser, translator, clustering, refactorer, and pipeline |
| `run_demo.py`, `run_refactoring_demo.py` | Standalone research scripts |
| `requirements.txt` | Dependencies for these experiments |

To try the research scripts, use an isolated Python environment and install `requirements.txt`. Those dependencies are deliberately separate from the small web demo's `backend/pyproject.toml`. Generated prototype files belong in `output/`, which Git ignores.
