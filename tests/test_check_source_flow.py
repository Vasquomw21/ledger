# Tests for the source-flow gate: every stamped ledger must have a declared
# discovery/screening route, and included sources must resolve to ledgers.
import check_source_flow as csf


def _ledger(claims_dir, key, *, stamped=True):
    claims_dir.mkdir(parents=True, exist_ok=True)
    stamp = "body_sha256: " + ("a" * 64) if stamped else ""
    text = "\n".join([
        "---",
        'paper: "X"',
        stamp,
        "---",
        "",
        "## Claim 1",
        '> "quote"',
        "**ID:** c",
        "",
    ])
    (claims_dir / f"{key}.md").write_text(text, encoding="utf-8")


def _flow(path, included=("smith_2020",), search=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Source Flow",
        "",
        "## Overview",
        "",
        "**Review-question:** Which sources entered this corpus?",
        "**Inclusion-criteria:** Stamped ledgers relevant to the inquiry.",
        "**Exclusion-criteria:** Irrelevant or inaccessible records.",
        "**Update-procedure:** Update this file when the corpus changes.",
        "**Last-updated:** 2026-06-15",
        "",
    ]
    if search:
        lines += [
            "## Searches",
            "",
            "### Search 1",
            "**Database:** PubMed",
            "**Query:** x",
            "**Date:** 2026-06-15",
            "**Records-found:** 5",
            "**Records-screened:** 2",
            f"**Included:** {', '.join(included)}",
            "",
        ]
    lines += ["## Included sources", ""]
    for key in included:
        lines += [
            f"### {key}",
            f"**Source:** {key}",
            "**Reason:** Addresses Q1.",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def test_empty_project_passes_without_flow(tmp_path):
    assert csf.source_flow_problems(tmp_path / "claims", tmp_path / "content" / "source_flow.md") == []


def test_stamped_ledger_must_be_included(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _ledger(claims, "smith_2020")
    _flow(flow, included=())
    problems = csf.source_flow_problems(claims, flow)
    assert any("smith_2020" in p and "absent" in p for p in problems)


def test_stamped_ledger_requires_overview_protocol(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _ledger(claims, "smith_2020")
    flow.parent.mkdir(parents=True, exist_ok=True)
    flow.write_text("\n".join([
        "# Source Flow",
        "",
        "## Searches",
        "### Search 1",
        "**Database:** PubMed",
        "**Query:** x",
        "**Date:** 2026-06-15",
        "**Records-found:** 1",
        "**Records-screened:** 1",
        "**Included:** smith_2020",
        "",
        "## Included sources",
        "### smith_2020",
        "**Source:** smith_2020",
        "**Reason:** Addresses Q1.",
    ]), encoding="utf-8")
    problems = csf.source_flow_problems(claims, flow)
    assert any("Review-question" in p for p in problems)


def test_complete_flow_passes(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _ledger(claims, "smith_2020")
    _flow(flow)
    assert csf.source_flow_problems(claims, flow) == []


def test_included_source_must_resolve(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _flow(flow, included=("ghost_2099",))
    problems = csf.source_flow_problems(claims, flow)
    assert any("ghost_2099" in p and "resolves to no ledger" in p for p in problems)


def test_search_included_list_must_match_included_entries(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _ledger(claims, "smith_2020")
    _ledger(claims, "jones_2021")
    _flow(flow, included=("smith_2020",))
    text = flow.read_text(encoding="utf-8").replace("**Included:** smith_2020",
                                                     "**Included:** ghost_2099")
    flow.write_text(text, encoding="utf-8")
    problems = csf.source_flow_problems(claims, flow)
    assert any("smith_2020" in p and "absent from all search" in p for p in problems)
    assert any("ghost_2099" in p and "no matching entry" in p for p in problems)


def test_search_counts_must_be_numeric_and_consistent(tmp_path):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    _ledger(claims, "smith_2020")
    _flow(flow)
    text = flow.read_text(encoding="utf-8")
    text = text.replace("**Records-found:** 5", "**Records-found:** five")
    text = text.replace("**Records-screened:** 2", "**Records-screened:** 7")
    flow.write_text(text, encoding="utf-8")
    problems = csf.source_flow_problems(claims, flow)
    assert any("Records-found" in p and "integer" in p for p in problems)


def test_required_fails_warn_passes(tmp_path, monkeypatch):
    claims = tmp_path / "verified_claims"
    flow = tmp_path / "content" / "source_flow.md"
    config = tmp_path / "ledger.config.md"
    config.write_text("source_flow: required\n", encoding="utf-8")
    _ledger(claims, "smith_2020")
    monkeypatch.setattr("sys.argv", [
        "check_source_flow.py", "--claims-dir", str(claims),
        "--flow", str(flow), "--config", str(config),
    ])
    assert csf.main() == 1
    monkeypatch.setattr("sys.argv", [
        "check_source_flow.py", "--claims-dir", str(claims),
        "--flow", str(flow), "--source-flow", "warn",
    ])
    assert csf.main() == 0
