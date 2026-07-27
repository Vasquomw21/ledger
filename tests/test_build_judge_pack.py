# Tests for the judge-bundle generator.
from pathlib import Path

import build_judge_pack as bjp


def _project(tmp_path):
    (tmp_path / "ledger.config.md").write_text(
        "\n".join([
            "project_name: testcase",
            "project_root: /secret/abs/path",   # must be scrubbed — never rendered
            "provenance: required",
            "structure_layer: required",
            "source_flow: warn",
        ]), encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    (claims / "a_2020.md").write_text("\n".join([
        "---", 'paper: "A et al. (2020)"', 'doi: "10.1/a"',
        "verified_verdict: pass", "body_sha256: " + ("a" * 64), "---", "",
        "## Claim 1", '> "premise"', "**ID:** p", "**Location:** Abstract",
        "**Supports:** b_2021:c (grounded by #p)", "",
    ]), encoding="utf-8")
    (claims / "b_2021.md").write_text("\n".join([
        "---", 'paper: "B et al. (2021)"', "verified_verdict: pass",
        "body_sha256: " + ("b" * 64), "---", "",
        "## Claim 1", '> "conclusion"', "**ID:** c", "",
    ]), encoding="utf-8")
    content = tmp_path / "content"
    (content / "assessments" / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    (content / "source_register.md").write_text(
        "## Sources\n### A\n**Source:** a_2020\n**Position:** pro — the pro side.\n",
        encoding="utf-8")
    (content / "source_flow.md").write_text("# Source Flow\n", encoding="utf-8")
    (content / "assessments" / "_records" / "r1.json").write_text(
        '{"id":"r1","kind":"edge","subject":"a_2020:p","grounding":["a_2020:p"],'
        '"disputes":[],"assessor":"tester@example.com","assessed_date":"20260101"}',
        encoding="utf-8")
    return tmp_path


def test_bundle_structure(tmp_path):
    out = tmp_path / "pack"
    written = bjp.build_pack(_project(tmp_path), out)
    for rel in ("index.html", "assets/ledger.css", "ledgers/a_2020.html",
                "ledgers/b_2021.html", "assessments.html", "graph.json"):
        assert (out / rel).is_file(), rel
        assert rel in written
    # no finding.md in the fixture → no finding.html
    assert not (out / "finding.html").is_file()


def test_index_links_resolve(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    for rel in ("ledgers/a_2020.html", "ledgers/b_2021.html"):
        assert f'href="{rel}"' in idx
    assert 'id="inputs"' in idx and 'class="infographic"' in idx and 'id="ledger-data"' in idx


def test_ledger_page_has_quote_and_crosslink(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    page = (out / "ledgers" / "a_2020.html").read_text(encoding="utf-8")
    assert "premise" in page                      # the verbatim quote
    assert "A et al. (2020)" in page              # provenance
    assert 'href="b_2021.html"' in page           # edge linkified to the target ledger


def test_assessor_surfaced(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    assert "tester@example.com" in (out / "assessments.html").read_text(encoding="utf-8")


def test_hitl_map_renders_touchpoints_and_command(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="hitl"' in idx                             # the collaboration section
    assert "index.html#hitl" in idx                       # nav + processes pointer link
    assert "Where a human judges" in idx                  # Band 1 (touchpoints by layer)
    assert "Presentation vs production" in idx            # Band 3 (production boundary)
    # Band 2 is populated in this fixture: the one unassessed edge gets a prefilled command
    assert "--kind edge" in idx
    assert "--subject b_2021:c --grounding a_2020:p" in idx


def test_processes_shows_five_integrity_layers(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    # the five integrity layers by name, in the Processes section (per DEMO.md §5)
    for layer in ("Fidelity", "Completeness", "Coherence", "Validity", "Clarity"):
        assert layer in idx, layer
    assert "five-layer integrity stack" in idx
    assert "the frontier" in idx                       # Validity, the judged layer
    # the strength badges reuse the trust/badge vocabulary
    assert "Guarantee" in idx and "Structural" in idx and "Judged" in idx


def test_theme_toggle_and_dark_tokens(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    # the toggle button + the early head script + the end-of-body handler, all keyed
    # to the pack-scoped storage key
    assert 'id="theme-toggle"' in idx
    assert idx.count("ledger-pack-theme") == 2          # head restore + toggle handler
    assert 'setAttribute("data-theme"' in idx
    # a sub-page (prefix "../") carries the same wiring
    sub = (out / "ledgers" / "a_2020.html").read_text(encoding="utf-8")
    assert 'id="theme-toggle"' in sub and "ledger-pack-theme" in sub
    css = (out / "assets" / "ledger.css").read_text(encoding="utf-8")
    assert '[data-theme="dark"]' in css
    # the theme-aware badge must be re-asserted AFTER GRAPH_CSS's light-hard-coded one,
    # so dark mode wins — the LAST .badge.ok rule is the color-mix version
    assert css.rindex(".badge.ok { background: color-mix") > css.rindex(".badge.ok { background: #")


def test_no_absolute_path_leak(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    for p in out.rglob("*"):
        if p.is_file():
            assert "/secret/abs/path" not in p.read_text(encoding="utf-8", errors="ignore"), p


def test_hitl_intake_commands_use_real_paths(tmp_path):
    """The L1 command names intake tools under literature/ (not tools/), each on disk."""
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    idx = (out / "index.html").read_text(encoding="utf-8")
    repo_root = Path(bjp.__file__).resolve().parents[1]
    for tool in ("literature/check.sh", "literature/fetch_paper.sh",
                 "literature/extract_text.py", "literature/verify_quotes.py"):
        assert tool in idx, f"HITL band should reference {tool}"
        assert (repo_root / tool).is_file(), f"{tool} must exist on disk"
    assert "tools/check.sh" not in idx and "tools/verify_quotes.py" not in idx


def test_main_rejects_nonexistent_project(tmp_path, monkeypatch):
    # Packing a bare dir would emit a plausible-looking empty bundle and exit 0.
    monkeypatch.setattr("sys.argv", ["build_judge_pack.py",
                                     str(tmp_path / "nope"), "--out", str(tmp_path / "o")])
    assert bjp.main() == 2
