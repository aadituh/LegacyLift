"""COPY/CALL/PERFORM dependency discovery against project files and paragraphs."""

from pathlib import Path

from legacylift.cobol.dependencies import DependencyKind, find_dependencies
from legacylift.cobol.parser import parse_program

DATA = Path(__file__).parents[1] / "src" / "legacylift" / "data"


def _parse(*names: str):
    return [parse_program(name, (DATA / name).read_text(encoding="utf-8")) for name in names]


def _by_kind(deps, kind: DependencyKind):
    return [d for d in deps if d.kind == kind]


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

    assert [u for u in unresolved if u.kind != DependencyKind.PERFORM] == []
    file_deps = [d for d in deps if d.kind != DependencyKind.PERFORM]
    by_source: dict[str, list[tuple[str, str, int]]] = {}
    for dep in file_deps:
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


def test_bankmain_perform_links() -> None:
    programs = _parse("BANKMAIN.cbl")
    deps, unresolved = find_dependencies(programs, ["BANKMAIN.cbl"])
    performs = [
        (d.source, d.target, d.line) for d in _by_kind(deps, DependencyKind.PERFORM)
    ]
    assert performs == [
        ("BANKMAIN.cbl:MAIN-LOGIC", "LOAD-ACCOUNTS", 74),
        ("BANKMAIN.cbl:MAIN-LOGIC", "POST-TRANSACTIONS", 75),
        ("BANKMAIN.cbl:MAIN-LOGIC", "PRINT-STATEMENT", 76),
        ("BANKMAIN.cbl:POST-TRANSACTIONS", "POST-ONE-TRANSACTION", 102),
        ("BANKMAIN.cbl:POST-ONE-TRANSACTION", "FIND-ACCOUNT", 112),
    ]
    assert [u for u in unresolved if u.kind == DependencyKind.PERFORM] == []


def test_perform_thru_expands_paragraph_range() -> None:
    text = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. P.\n"
        "       PROCEDURE DIVISION.\n"
        "       START-PARA.\n"
        "           PERFORM ALPHA THRU GAMMA.\n"
        "           STOP RUN.\n"
        "       ALPHA.\n"
        "           DISPLAY \"A\".\n"
        "       BETA.\n"
        "           DISPLAY \"B\".\n"
        "       GAMMA.\n"
        "           DISPLAY \"C\".\n"
    )
    programs = [parse_program("P.cbl", text)]
    deps, unresolved = find_dependencies(programs, ["P.cbl"])
    performs = [
        (d.source, d.target, d.line) for d in _by_kind(deps, DependencyKind.PERFORM)
    ]
    assert performs == [
        ("P.cbl:START-PARA", "ALPHA", 5),
        ("P.cbl:START-PARA", "BETA", 5),
        ("P.cbl:START-PARA", "GAMMA", 5),
    ]
    assert unresolved == []


def test_missing_perform_target_is_unresolved() -> None:
    text = (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. P.\n"
        "       PROCEDURE DIVISION.\n"
        "       MAIN.\n"
        "           PERFORM MISSING-PARA.\n"
        "           STOP RUN.\n"
    )
    programs = [parse_program("P.cbl", text)]
    deps, unresolved = find_dependencies(programs, ["P.cbl"])
    assert _by_kind(deps, DependencyKind.PERFORM) == []
    assert len(unresolved) == 1
    assert unresolved[0].kind == DependencyKind.PERFORM
    assert unresolved[0].name == "MISSING-PARA"
    assert unresolved[0].source == "P.cbl:MAIN"
    assert unresolved[0].line == 5


def test_matching_ignores_case_and_extension() -> None:
    programs = _parse("BANKMAIN.cbl")
    catalog = ["bankmain.CBL", "acctdef.CPY", "txndef.cpy", "txnpost.cbl", "intcalc.COB"]
    deps, unresolved = find_dependencies(programs, catalog)
    assert [u for u in unresolved if u.kind != DependencyKind.PERFORM] == []
    targets = {(d.kind, d.target.casefold()) for d in deps if d.kind != DependencyKind.PERFORM}
    assert (DependencyKind.COPY, "acctdef.cpy") in targets
    assert (DependencyKind.COPY, "txndef.cpy") in targets
    assert (DependencyKind.CALL, "txnpost.cbl") in targets
    assert (DependencyKind.CALL, "intcalc.cob") in targets


def test_missing_copybook_is_unresolved() -> None:
    programs = _parse("BANKMAIN.cbl")
    # ACCTDEF and callees present; TXNDEF missing
    catalog = ["BANKMAIN.cbl", "ACCTDEF.cpy", "TXNPOST.cbl", "INTCALC.cbl"]
    deps, unresolved = find_dependencies(programs, catalog)

    file_deps = [d for d in deps if d.kind != DependencyKind.PERFORM]
    assert [
        (d.kind.value, d.target) for d in file_deps
    ] == [("copy", "ACCTDEF.cpy"), ("call", "TXNPOST.cbl"), ("call", "INTCALC.cbl")]
    copy_unresolved = [u for u in unresolved if u.kind == DependencyKind.COPY]
    assert len(copy_unresolved) == 1
    assert copy_unresolved[0].source == "BANKMAIN.cbl"
    assert copy_unresolved[0].name == "TXNDEF"
    assert copy_unresolved[0].line == 44


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
    assert ("BANKMAIN.cbl:MAIN-LOGIC", "perform", "LOAD-ACCOUNTS") in links
    assert ("BANKMAIN.cbl:POST-ONE-TRANSACTION", "perform", "FIND-ACCOUNT") in links
    assert result["unresolved"] == []

    run = client.get(f"{base}/runs/{result['run_id']}").json()
    assert run["dependencies"] == result["dependencies"]
