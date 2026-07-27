# Tests for the read-only judge dashboard.
import json

import judge_dashboard as jd


def _project(tmp_path):
    (tmp_path / "ledger.config.md").write_text("source_flow: warn\n", encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    (claims / "a_2020.md").write_text(
        "\n".join([
            "---",
            'paper: "A"',
            'doi: "10.1/a"',
            "body_sha256: " + ("a" * 64),
            'verified_verdict: "pass"',
            "---",
            "",
            "## Claim 1",
            '> "premise"',
            "**ID:** p",
            "**Addresses:** q1",
            "**Supports:** b_2021:c (grounded by #p)",
            '**Assess-rhetorical:** "premise" — overstates the evidence (grounded by #p) [rec: a-rhet]',
            "",
        ]),
        encoding="utf-8",
    )
    (claims / "b_2021.md").write_text(
        "\n".join([
            "---",
            'paper: "B"',
            "body_sha256: " + ("b" * 64),
            "---",
            "",
            "## Claim 1",
            '> "conclusion"',
            "**ID:** c",
            "",
        ]),
        encoding="utf-8",
    )
    content = tmp_path / "content"
    content.mkdir()
    (content / "source_flow.md").write_text("# Source Flow\n", encoding="utf-8")
    (content / "inquiry.md").write_text(
        "\n".join([
            "---",
            "authored_by: ai",
            "generated_by: claude",
            "generated_date: 20260712",
            "reviewed_by:",
            "status: draft",
            "---",
            "",
            "# Inquiry — Does the premise hold?",
            "",
            "## Q1 — Does p support c?",
            "",
            "**id:** q1",
            "",
        ]),
        encoding="utf-8",
    )
    records = content / "assessments" / "_records"
    records.mkdir(parents=True)
    (records / "a-rhet.assess.json").write_text(json.dumps({
        "id": "a-rhet", "kind": "rhetorical", "subject": "a_2020:p",
        "span": "premise", "grounding": ["a_2020:p"], "disputes": [], "reviews": [],
        "assessor": "tester@example.com", "assessed_date": "20260712",
    }), encoding="utf-8")
    return tmp_path


def test_dashboard_model_surfaces_backlog(tmp_path):
    proj = _project(tmp_path)
    model = jd.dashboard_model(proj)
    assert model["counts"]["unassessed_edges"] == 1
    assert model["counts"]["source_flow_gaps"] >= 1
    assert model["counts"]["records"] == 1


def test_render_html_has_tabbed_shell_and_hero(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert "Ledger Judge Dashboard" in html          # <title> preserved
    assert 'class="case-q"' in html                  # the hero case question
    assert "Does the premise hold?" in html          # pulled from inquiry.md
    for panel in ("board", "quotes", "sources", "assessments", "docs", "metrics"):
        assert f'data-panel="{panel}"' in html
    assert 'id="theme-toggle"' in html               # light/dark toggle
    assert "Awaiting judgement" in html              # metrics tab backlog (the human's queue)


def test_graphview_payload_carries_quotes_and_edges(tmp_path):
    pv = jd.graphview_payload(_project(tmp_path))
    assert {n["id"] for n in pv["nodes"]} == {"a_2020:p", "b_2021:c"}
    quotes = {n["id"]: n["quote"] for n in pv["nodes"]}
    assert quotes["a_2020:p"] == "premise"
    assert quotes["b_2021:c"] == "conclusion"
    assert len(pv["edges"]) == 1
    e = pv["edges"][0]
    assert (e["source"], e["target"], e["type"]) == ("a_2020:p", "b_2021:c", "supports")
    assert e["assessed"] is False           # no edge record covers it → unassessed
    assert e["grounding"] == "p"            # the dropped-then-restored edge fields
    assert "rec" in e and e["target_resolved"] is True
    assert e["edge_record_id"] is None      # unassessed → no covering record id
    # the awaiting frontier surfaces this edge with a runnable, prefilled assess command
    assert len(pv["awaiting"]) == 1
    a = pv["awaiting"][0]
    assert (a["source"], a["target"], a["type"]) == ("a_2020:p", "b_2021:c", "supports")
    assert a["grounding_quote"] == "premise"
    for frag in ("--kind edge", "--subject b_2021:c", "--grounding a_2020:p", "--span premise"):
        assert frag in a["command"]


def test_command_helpers_shape_and_shell_escape():
    import shlex
    assert jd._suggest_edge_id("worobey_2022:market", "andersen_2020:no-lab",
                               "supports") == "worobey-supports-no-lab-apt"
    # a span with a single quote and double quotes must survive a shell parse intact
    cmd = jd.assess_command("k:t", "k:s", "id1", "it's a \"quote\"")
    assert cmd.startswith("python3 tools/assess_record.py --write --kind edge")
    parts = shlex.split(cmd)
    assert parts[parts.index("--span") + 1] == 'it\'s a "quote"'
    # contest is empty without a record to dispute, and names it when present
    assert jd.contest_command("k:t", "k:s", "", "q") == ""
    assert "--kind faithfulness --disputes rec9" in jd.contest_command("k:t", "k:s", "rec9", "q")


def test_awaiting_frontier_renders_command_in_html(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert "Awaiting human judgement" in html                              # the enriched section
    assert "--subject b_2021:c --grounding a_2020:p" in html               # prefilled command shipped


def test_payload_surfaces_assessments_and_annotations(tmp_path):
    pv = jd.graphview_payload(_project(tmp_path))
    node = next(n for n in pv["nodes"] if n["id"] == "a_2020:p")
    # the sealed record is attached to its subject claim
    assert any(r["id"] == "a-rhet" and r["kind"] == "rhetorical" for r in node["records"])
    # the in-band rhetorical comment is parsed and attached
    rhet = [a for a in node["annotations"] if a["type"] == "rhetorical"]
    assert rhet and rhet[0]["span"] == "premise"
    assert "overstates" in rhet[0]["note"]
    assert rhet[0]["rec"] == "a-rhet"
    # cross-cutting structures the tabs render off
    assert "a-rhet" in pv["records_index"]
    assert any(s["key"] == "a_2020" and s["verified_verdict"] == "pass" for s in pv["sources"])
    assert pv["case"]["title"] == "Does the premise hold?"


def test_claim_annotations_parser():
    body = "\n".join([
        "## Claim 2",
        '> "quote"',
        '**Assess-rhetorical:** "irrefutably" — asserts too much (grounded by #x) [rec: r1]',
        "**Status:** contested",
        "**Correlated-with:** other:slug (grounded by #x) [shared premise: same data]",
    ])
    anns = jd.claim_annotations(body)
    by_type = {a["type"]: a for a in anns}
    assert by_type["rhetorical"]["span"] == "irrefutably"
    assert by_type["rhetorical"]["note"] == "asserts too much"
    assert by_type["rhetorical"]["rec"] == "r1"
    assert by_type["status"]["note"] == "contested"
    assert by_type["correlated"]["note"] == "shared premise: same data"


def test_render_html_embeds_graph_and_exhibit(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert 'id="ledger-data"' in html      # the embedded client-side model
    assert 'id="graph"' in html            # the interactive SVG surface
    assert "highlightQuote" in html        # the annotated-exhibit renderer shipped
    assert "premise" in html               # a verbatim quote travels into the page


def test_docs_tab_surfaces_documents_and_provenance(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert 'data-panel="docs"' in html            # the Docs tab panel exists
    assert "Development documents" in html         # the tab intro
    assert "content/inquiry.md" in html            # the inquiry is surfaced by name
    assert "Does the premise hold?" in html        # its rendered body travels in
    assert "AI-drafted" in html                    # provenance badge from authored_by: ai
    assert '<span class="badge muted">draft</span>' in html  # the status badge
    assert "ledger.config.md" in html              # the gate-posture config is surfaced too


def test_metrics_gap_lines_linkify_real_refs():
    node_ids = {"andersen_2020:no-lab-scenario", "pekar_2022:x"}
    ledger_first = {"andersen_2020": "andersen_2020:no-lab-scenario",
                    "pekar_2022": "pekar_2022:x", "worobey_2022": "worobey_2022:y"}
    text = ("pekar_2022 and worobey_2022 both support andersen_2020:no-lab-scenario "
            "(possible double-count)")
    out = jd._linkify_refs(text, node_ids, ledger_first)
    # the key:slug claim id becomes a jump-link to itself
    assert '<a class="jump" data-goto="andersen_2020:no-lab-scenario">andersen_2020:no-lab-scenario</a>' in out
    # bare ledger keys become jump-links to that source's first claim
    assert '<a class="jump" data-goto="pekar_2022:x">pekar_2022</a>' in out
    assert '<a class="jump" data-goto="worobey_2022:y">worobey_2022</a>' in out
    # the ledger key inside a key:slug must NOT be split into a nested link
    assert ">andersen_2020</a>:no-lab-scenario" not in out
    # an unresolvable line stays plain text
    assert jd._linkify_refs("nothing to link here", set(), {}) == "nothing to link here"


def test_dashboard_ships_cross_tab_jump_wiring(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert "__ledgerGoto" in html            # Board exposes selection for jump-links
    assert "data-goto" in html               # delegated handler target attribute
    assert "a.jump" in html                  # jump-link styling shipped


def test_metric_tiles_deep_link(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert "metric-link" in html                        # tiles are clickable
    assert 'data-scroll="#sec-double-count"' in html    # a tile jumps to its section
    assert 'id="sec-double-count"' in html              # and that section anchor exists
    # a cross-tab tile carries a data-tab (Assessments has records in the fixture)
    assert html.count('data-tab="assessments"') >= 2    # the nav button + ≥1 tile


def test_self_contained_no_cdn(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert "<script src=" not in html          # no external scripts
    assert '<link rel="stylesheet"' not in html  # no external styles
    assert "cdn." not in html and "fonts.googleapis" not in html


def test_main_writes_out(tmp_path, monkeypatch):
    proj = _project(tmp_path)
    out = tmp_path / "dashboard.html"
    monkeypatch.setattr("sys.argv", [
        "judge_dashboard.py", "--repo-root", str(proj), "--out", str(out),
    ])
    assert jd.main() == 0
    assert "Ledger Judge Dashboard" in out.read_text(encoding="utf-8")


def test_main_rejects_nonexistent_project(tmp_path, monkeypatch):
    # A bare dir would render a plausible empty dashboard and exit 0 (false success).
    monkeypatch.setattr("sys.argv", [
        "judge_dashboard.py", "--repo-root", str(tmp_path / "nope"),
        "--out", str(tmp_path / "o.html"),
    ])
    assert jd.main() == 2
