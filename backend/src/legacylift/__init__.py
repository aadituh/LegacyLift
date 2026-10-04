"""LegacyLift backend: a FastAPI service that stores COBOL projects and converts COBOL to Python.

A request goes ``main`` (app setup) -> ``routers`` (HTTP) -> ``services`` (rules)
-> ``storage`` (saving) or ``cobol.converter`` (translation). Start with ``main.py``.
"""
