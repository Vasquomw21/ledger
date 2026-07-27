# Tests for the coverage gate (corpus-free). A cited claim with no role
# in the argument graph is flagged; a claim situated by an edge, an **Addresses:**,
# or an assessment passes; bare cites and the off posture are not checked.
import assess_record as ar
import check_coverage as cc

PREFIXES = ["content/concept_notes/"]


def _ledger(claims_dir, key, claims, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", ""]
    for i, (slug, quote) in enumerate(claims, start=1):
        lines += [f"## Claim {i}: summary", "", f'> "{quote}"', "",
                  f"**ID:** {slug}", "**Location:** Section 1"]
        if i == 1:
            lines += list(extra)
        lines.append("")
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _note(content_dir, text):
    d = content_dir / "concept_notes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "note.md").write_text(text, encoding="utf-8")


def _dirs(tmp_path):
    return (tmp_path / "verified_claims", tmp_path / "content",
            tmp_path / "assessments")


def test_unsituated_cited_claim_flagged(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    _note(content, "The site is not engineered (Andersen 2020 #fcs).")
    problems = cc.coverage_problems(claims, content, PREFIXES, assess)
    assert any("#fcs" in p and "no graph role" in p for p in problems)


def test_situated_via_edge_passes(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    _ledger(claims, "segreto_2021", [("eng", "the site implies engineering")],
            extra=["**Rebuts:** andersen_2020:fcs (grounded by #eng)"])
    _note(content, "The site is not engineered (Andersen 2020 #fcs).")
    assert cc.coverage_problems(claims, content, PREFIXES, assess) == []


def test_situated_via_addresses_passes(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")],
            extra=["**Addresses:** fcs-engineering"])
    _note(content, "The site is not engineered (Andersen 2020 #fcs).")
    assert cc.coverage_problems(claims, content, PREFIXES, assess) == []


def test_situated_via_assessment_passes(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    record = ar.build_record("crux-of", "r1", "andersen_2020:fcs",
                             ["andersen_2020:fcs"], "", "20260613", claims_dir=claims)
    ar.write_record(record, assess_dir=assess)
    _note(content, "The site is not engineered (Andersen 2020 #fcs).")
    assert cc.coverage_problems(claims, content, PREFIXES, assess) == []


def test_bare_cite_not_checked(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    _note(content, "Per the proximal-origin analysis (Andersen 2020).")  # no #ref
    assert cc.coverage_problems(claims, content, PREFIXES, assess) == []


def test_off_skips(tmp_path, monkeypatch, capsys):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    _note(content, "(Andersen 2020 #fcs)")
    rc = _run_main(monkeypatch, claims, content, assess, "off")
    assert rc == 0
    assert "off" in capsys.readouterr().out


def test_required_fails_optional_warns(tmp_path, monkeypatch):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "the furin site is not expected")])
    _note(content, "The site is not engineered (Andersen 2020 #fcs).")
    assert _run_main(monkeypatch, claims, content, assess, "required") == 1
    assert _run_main(monkeypatch, claims, content, assess, "warn") == 0


def test_empty_passes(tmp_path, monkeypatch):
    claims, content, assess = _dirs(tmp_path)
    claims.mkdir()
    content.mkdir()
    assert _run_main(monkeypatch, claims, content, assess, "required") == 0


def test_citation_aliases_survive_an_earlier_resolved_cite(tmp_path):
    # Two unrelated 'alias' concepts met in this loop: the CITE -> ledger map (passed in,
    # project-wide) and the addresses of ONE claim (recomputed per cite). The second used
    # to overwrite the first, so every aliased cite AFTER the first resolved one hit a set
    # with no .get(). Order matters: extract_citations returns a set, so the ordinary cite
    # is not reliably first — this pins the fix, not the iteration order.
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "andersen_2020", [("fcs", "a quote about the site")])
    _ledger(claims, "drouin_2020", [("no-association", "a quote about eggs")])
    _note(content, "The site is not engineered (Andersen 2020 #fcs). "
                   "Eggs are fine (Drouin-Chartier et al. 2020 #no-association).")
    problems = cc.coverage_problems(claims, content, PREFIXES, assess,
                                    {"drouin-chartier_2020": "drouin_2020"})
    # Neither claim is situated, so BOTH must be reported. Before the fix this raised
    # AttributeError, or silently dropped the aliased cite.
    assert len(problems) == 2, problems
    assert any("drouin-chartier 2020 #no-association" in p for p in problems), problems


def test_an_aliased_cite_resolves_for_coverage(tmp_path):
    claims, content, assess = _dirs(tmp_path)
    _ledger(claims, "drouin_2020", [("no-association", "a quote about eggs")])
    _note(content, "Eggs are fine (Drouin-Chartier et al. 2020 #no-association).")
    # Without the citation-alias map the cite does not resolve, and coverage skips it —
    # resolving is check_citations' job, so the skip is correct there.
    assert cc.coverage_problems(claims, content, PREFIXES, assess) == []
    # With it, the unsituated claim is caught.
    problems = cc.coverage_problems(claims, content, PREFIXES, assess,
                                    {"drouin-chartier_2020": "drouin_2020"})
    assert len(problems) == 1, problems


def _run_main(monkeypatch, claims, content, assess, mode):
    argv = ["check_coverage.py", "--claims-dir", str(claims),
            "--content-dir", str(content), "--assess-dir", str(assess),
            "--coverage", mode]
    monkeypatch.setattr("sys.argv", argv)
    return cc.main()
