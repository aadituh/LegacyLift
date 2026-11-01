"""The runner: compiles and runs uploaded COBOL, and runs generated Python, in its own container.

``sandbox`` runs one program per call in a temporary folder with a time limit and
an output limit. ``server`` serves it over HTTP to the API. Both use only the
standard library, so the runner image (``backend/runner.Dockerfile``) needs no
packages besides GnuCOBOL.
"""
