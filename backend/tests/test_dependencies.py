"""COPY/CALL dependency discovery against project file names."""

from pathlib import Path

from legacylift.cobol.dependencies import DependencyKind, find_dependencies
from legacylift.cobol.parser import parse_program

DATA = Path(__file__).parents[1] / "src" / "legacylift" / "data"


def _parse(*names: str):
    return [parse_program(name, (DATA / name).read_text(encoding="utf-8")) for name in names]


def test_bank_sample_copy_and_call_links() -> None:
    programs = _parse("BANKMAIN.cbl", "TXNPOST.cbl", "INTCALC.cbl")
    catalog = [
        "BANKMAIN.cbl",
        "TXNPOST.cbl",
        "INTCALC.cbl",
        "ACCTDEF.cpy",
        "TXNDEF.cpy",
        "accounts.dat",
    ]
    deps, unresolved = find_dependencies(programs, catalog)

    assert unresolved == []
    by_source: dict[str, list[tuple[str, str, int]]] = {}
    for dep in deps:
        by_source.setdefault(dep.source, []).append(
            (dep.kind.value, dep.target, dep.line)
        )

    assert by_source["BANKMAIN.cbl"] == [
        ("copy", "ACCTDEF.cpy", 41),
        ("copy", "TXNDEF.cpy", 44),
        ("call", "TXNPOST.cbl", 116),
        ("call", "INTCALC.cbl", 156),
    ]
    assert by_source["TXNPOST.cbl"] == [
        ("copy", "ACCTDEF.cpy", 17),
        ("copy", "TXNDEF.cpy", 19),
    ]
    assert by_source["INTCALC.cbl"] == [
        ("copy", "ACCTDEF.cpy", 15),
    ]


def test_matching_ignores_case_and_extension() -> None:
    programs = _parse("BANKMAIN.cbl")
    catalog = ["bankmain.CBL", "acctdef.CPY", "txndef.cpy", "txnpost.cbl", "intcalc.COB"]
    deps, unresolved = find_dependencies(programs, catalog)
    assert unresolved == []
    targets = {(d.kind, d.target.casefold()) for d in deps}
    assert (DependencyKind.COPY, "acctdef.cpy") in targets
    assert (DependencyKind.COPY, "txndef.cpy") in targets
    assert (DependencyKind.CALL, "txnpost.cbl") in targets
    assert (DependencyKind.CALL, "intcalc.cob") in targets


def test_missing_copybook_is_unresolved() -> None:
    programs = _parse("BANKMAIN.cbl")
    # ACCTDEF and callees present; TXNDEF missing
    catalog = ["BANKMAIN.cbl", "ACCTDEF.cpy", "TXNPOST.cbl", "INTCALC.cbl"]
    deps, unresolved = find_dependencies(programs, catalog)

    assert [("copy", "ACCTDEF.cpy"), ("call", "TXNPOST.cbl"), ("call", "INTCALC.cbl")] == [
        (d.kind.value, d.target) for d in deps
    ]
    assert len(unresolved) == 1
    assert unresolved[0].source == "BANKMAIN.cbl"
    assert unresolved[0].name == "TXNDEF"
    assert unresolved[0].kind == DependencyKind.COPY
    assert unresolved[0].line == 44


def test_analyze_endpoint_returns_dependencies(client) -> None:
    created = client.post("/api/projects", json={"name": "Bank"}).json()
    base = f"/api/projects/{created['id']}"
    files = [
        (name, (DATA / name).read_text(encoding="utf-8"))
        for name in (
            "BANKMAIN.cbl",
            "TXNPOST.cbl",
            "INTCALC.cbl",
            "ACCTDEF.cpy",
            "TXNDEF.cpy",
        )
    ]
    upload = client.post(
        f"{base}/files",
        files=[("files", file) for file in files],
    )
    assert upload.status_code == 200

    result = client.post(f"{base}/analyze").json()
    assert result["status"] == "analyzed"
    assert result["program_count"] == 3
    assert result["copybook_count"] == 2

    links = {(d["source"], d["kind"], d["target"]) for d in result["dependencies"]}
    assert ("BANKMAIN.cbl", "copy", "ACCTDEF.cpy") in links
    assert ("BANKMAIN.cbl", "copy", "TXNDEF.cpy") in links
    assert ("BANKMAIN.cbl", "call", "TXNPOST.cbl") in links
    assert ("BANKMAIN.cbl", "call", "INTCALC.cbl") in links
    assert ("TXNPOST.cbl", "copy", "ACCTDEF.cpy") in links
    assert ("INTCALC.cbl", "copy", "ACCTDEF.cpy") in links
    assert result["unresolved"] == []

    run = client.get(f"{base}/runs/{result['run_id']}").json()
    assert run["dependencies"] == result["dependencies"]
