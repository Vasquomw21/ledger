# Tests for the citation coverage gate. Fixtures are built in tmp_path; no
# fixture touches the git-ignored corpus, so the suite runs in CI.
import sys

import pytest

import check_citations as cc


# --- extract_citations: which styles are caught, which are correctly ignored ---

def test_catches_supported_styles():
    text = ("As Smith et al. 2020 showed, and per Smith & Jones (2019); "
            "see also (Brown 2018) and Green (2017).")
    found = cc.extract_citations(text)
    assert ("smith", "2020", None) in found
    assert ("smith", "2019", None) in found
    assert ("brown", "2018", None) in found
    assert ("green", "2017", None) in found


def test_two_author_does_not_emit_second_surname():
    # "Smith & Jones 2020" is one cite (smith 2020), never a spurious jones 2020.
    found = cc.extract_citations("per Smith & Jones 2020 the result holds")
    assert ("smith", "2020", None) in found
    assert ("jones", "2020", None) not in found


def test_three_author_cite_credits_the_first_author():
    # A ledger is keyed by FIRST author, so a spelled-out list must resolve to it.
    # The "A & B" pattern used to match the TAIL pair here ("Hassidim & Lloyd 2009"),
    # crediting the middle author: it demanded a hassidim_2009 ledger that convention
    # says can never exist, and never checked the real harrow_2009 ledger at all.
    found = cc.extract_citations("(Harrow, Hassidim & Lloyd 2009) advertises a solve")
    assert ("harrow", "2009", None) in found
    assert ("hassidim", "2009", None) not in found
    assert ("lloyd", "2009", None) not in found


def test_three_author_cite_with_and_credits_the_first_author():
    # Spelled "and" rather than "&": the single-author pattern used to take the LAST.
    found = cc.extract_citations("Harrow, Hassidim and Lloyd (2009) proved it")
    assert ("harrow", "2009", None) in found
    assert ("lloyd", "2009", None) not in found


@pytest.mark.parametrize("text", [
    "Harrow, Hassidim, and Lloyd (2009) proved it",     # Oxford comma + "and"
    "Harrow, Hassidim, & Lloyd (2009) proved it",       # Oxford comma + "&"
    "Harrow, Hassidim and Lloyd (2009) proved it",      # no Oxford comma
    "(Harrow, Hassidim & Lloyd 2009) proved it",
])
def test_author_list_credits_the_first_author_whatever_the_conjunction(text):
    # An unsupported punctuation variant does not fail safe: the cite falls through
    # to a narrower pattern that matches the TAIL. The Oxford forms used to credit
    # Lloyd — the LAST author — so the real harrow_2009 ledger went unchecked.
    found = cc.extract_citations(text)
    assert found == {("harrow", "2009", None)}, text


@pytest.mark.parametrize("text,expected", [
    ("Smith and Jones (2020) showed x", ("smith", "2020", None)),
    ("Smith & Jones (2020) showed x", ("smith", "2020", None)),
    ("Alpha, Beta, Gamma, and Delta (2011) reported", ("alpha", "2011", None)),
    ("Alpha, Beta, Gamma, & Delta (2011) reported", ("alpha", "2011", None)),
])
def test_spelled_conjunction_is_supported_like_the_ampersand(text, expected):
    # "Smith and Jones (2020)" used to credit JONES: the two-author pattern took
    # only "&", so the single-author pattern matched "Jones (2020)".
    assert cc.extract_citations(text) == {expected}, text


def test_long_author_list_credits_the_first_author():
    found = cc.extract_citations("Alpha, Beta, Gamma & Delta (2011) reported")
    assert ("alpha", "2011", None) in found
    assert all(a not in {"beta", "gamma", "delta"} for a, _y, _c in found)


def test_three_author_cite_with_year_comma_and_report_name():
    # The lhc_safety prose shape: a report name, then a parenthesised author list.
    found = cc.extract_citations("LA-602 (Konopinski, Marvin & Teller, 1946) asked")
    assert ("konopinski", "1946", None) in found
    assert ("marvin", "1946", None) not in found


def test_three_author_cite_keeps_its_claim_ref():
    found = cc.extract_citations("(Harrow, Hassidim & Lloyd 2009 #hhl-speedup) holds")
    assert ("harrow", "2009", "hhl-speedup") in found


def test_three_author_cite_emits_exactly_one_citation():
    # Not just "the first author is present" — the list is ONE cite, not three.
    assert len(cc.extract_citations("(Harrow, Hassidim & Lloyd 2009)")) == 1


def test_extract_captures_claim_ref_across_forms():
    cases = {
        "(Smith et al. 2020 #c1) holds": ("smith", "2020", "c1"),
        "per Smith & Jones (2019 #rec3)": ("smith", "2019", "rec3"),
        "(Brown 2018 #eff) shows": ("brown", "2018", "eff"),
        "Green (2017 #c2) found": ("green", "2017", "c2"),
    }
    for text, expected in cases.items():
        assert expected in cc.extract_citations(text), text


def test_bare_cite_has_none_claim():
    assert ("smith", "2020", None) in cc.extract_citations("(Smith 2020) holds")


# --- the zero-gated-files guard: green having checked nothing ---

CONFIGURED = {"project_state": "configured",
              "gated_paths": "content/concept_notes/, content/literature_reviews/"}


def test_configured_project_whose_gating_matches_no_prose_blocks(tmp_path):
    # The exact shape all five shipped cases were in: gated_paths named two directories
    # that were empty placeholders while the authored synthesis sat elsewhere, so
    # coverage reported "ok — 0 gated file(s) checked" having verified nothing.
    prose = [tmp_path / "inquiry.md", tmp_path / "finding.md"]
    problem = cc.unscanned_prose_problem(CONFIGURED, prose, [])
    assert problem is not None
    assert "matches none of its 2 authored prose file(s)" in problem


def test_bookkeeping_alone_is_not_unscanned_prose(tmp_path):
    # A freshly configured project holds a log and a crosswalk and no prose yet. It has
    # nothing to gate, so it must not be told its gating is wrong — otherwise `init`
    # produces a project that immediately fails `check`.
    machinery = [tmp_path / "content" / n for n in
                 ("log.md", "crosswalk.md", "source_register.md", "source_flow.md")]
    machinery.append(tmp_path / "content" / "_ledger" / "skin_rules.md")
    machinery.append(tmp_path / "content" / "_ledger" / "semantic_health.md")
    assert cc.unscanned_prose_problem(CONFIGURED, machinery, []) is None


def test_prose_beside_bookkeeping_still_blocks(tmp_path):
    # The machinery filter must not swallow the finding: one authored file is enough.
    files = [tmp_path / "content" / "log.md",
             tmp_path / "content" / "_ledger" / "skin_rules.md",
             tmp_path / "content" / "inquiry.md"]
    problem = cc.unscanned_prose_problem(CONFIGURED, files, [])
    assert problem is not None
    assert "1 authored prose file(s)" in problem
    assert "inquiry.md" in problem


@pytest.mark.parametrize("rel,machinery", [
    ("content/log.md", True),
    ("content/crosswalk.md", True),
    ("content/source_register.md", True),
    ("content/source_flow.md", True),
    ("content/_ledger/skin_rules.md", True),
    ("content/_ledger/semantic_health.md", True),
    ("content/inquiry.md", False),
    ("content/finding.md", False),
    ("content/baseline_comparison.md", False),
    ("content/assessments/calibration.md", False),
    ("content/concept_notes/a.md", False),
    ("content/literature_reviews/r.md", False),
])
def test_machinery_classification(tmp_path, rel, machinery):
    assert cc.is_machinery(tmp_path / rel) is machinery, rel


def test_pristine_project_scanning_nothing_is_fine(tmp_path):
    # The kit's own root: content/ ships empty by design, so zero gated files is right.
    config = dict(CONFIGURED, project_state="pristine")
    assert cc.unscanned_prose_problem(config, [tmp_path / "inquiry.md"], []) is None


def test_unfilled_project_state_scanning_nothing_is_fine(tmp_path):
    assert cc.unscanned_prose_problem({"gated_paths": "content/x/"},
                                      [tmp_path / "inquiry.md"], []) is None


def test_a_project_with_no_prose_at_all_is_fine():
    assert cc.unscanned_prose_problem(CONFIGURED, [], []) is None


def test_a_project_that_scans_something_is_fine(tmp_path):
    prose = [tmp_path / "inquiry.md", tmp_path / "log.md"]
    assert cc.unscanned_prose_problem(CONFIGURED, prose, [prose[0]]) is None


def test_gating_nothing_can_be_declared_explicitly(tmp_path):
    # `gated_paths: none` is a declaration; an accident is what this guard is for.
    config = {"project_state": "configured", "gated_paths": "none"}
    assert cc.gated_prefixes(config) == []
    assert cc.unscanned_prose_problem(config, [tmp_path / "inquiry.md"], []) is None


def test_gated_paths_none_is_not_a_literal_prefix():
    # Guard against 'none' silently becoming a path substring that matches nothing.
    assert cc.gated_prefixes({"gated_paths": "none"}) == []
    assert not cc.is_gated("/x/content/none/a.md", cc.gated_prefixes({"gated_paths": "none"}))


def test_gated_paths_tolerates_a_trailing_comment():
    assert cc.gated_prefixes({"gated_paths": "content/x/  # a note"}) == ["content/x/"]


# --- citation aliases: an accurate surname over an abbreviated ledger key ---

def _claims(tmp_path, *keys):
    d = tmp_path / "verified_claims"
    d.mkdir(parents=True, exist_ok=True)
    for k in keys:
        (d / f"{k}.md").write_text("# ledger\n", encoding="utf-8")
    return d


def test_alias_resolves_a_cite_whose_key_abbreviates_the_surname(tmp_path):
    # Drouin-Chartier et al. (2020) against a ledger keyed drouin_2020: the resolver
    # misses, and the cheap fix — clipping the surname in the prose — lets an internal
    # identifier dictate the bibliography.
    claims = _claims(tmp_path, "drouin_2020")
    aliases = cc.citation_aliases({"citation_aliases": "drouin-chartier_2020 -> drouin_2020"})
    assert cc.ledger_path_for(claims, "drouin-chartier", "2020") is None
    assert cc.ledger_path_for(claims, "drouin-chartier", "2020", aliases).name == "drouin_2020.md"


def test_alias_does_not_disturb_the_canonical_key(tmp_path):
    claims = _claims(tmp_path, "drouin_2020")
    aliases = cc.citation_aliases({"citation_aliases": "drouin-chartier_2020 -> drouin_2020"})
    assert cc.ledger_path_for(claims, "drouin", "2020", aliases).name == "drouin_2020.md"


def test_aliases_parse_several_pairs():
    aliases = cc.citation_aliases(
        {"citation_aliases": "drouin-chartier_2020 -> drouin_2020, konopinski_1946 -> la602_1946"})
    assert aliases == {"drouin-chartier_2020": "drouin_2020",
                       "konopinski_1946": "la602_1946"}


def test_absent_or_placeholder_aliases_are_empty():
    assert cc.citation_aliases({}) == {}
    assert cc.citation_aliases({"citation_aliases": "<cited -> ledger>"}) == {}


def test_alias_shadowing_a_real_ledger_blocks(tmp_path):
    # An alias over a key that already resolves would silently redirect good cites.
    claims = _claims(tmp_path, "drouin_2020", "chen_2021")
    problems = cc.alias_problems({"citation_aliases": "chen_2021 -> drouin_2020"}, claims)
    assert any("must not shadow" in p for p in problems)


def test_alias_to_a_nonexistent_ledger_blocks(tmp_path):
    claims = _claims(tmp_path, "drouin_2020")
    problems = cc.alias_problems({"citation_aliases": "x_2020 -> ghost_1999"}, claims)
    assert any("no ledger named 'ghost_1999'" in p for p in problems)


def test_duplicate_alias_blocks(tmp_path):
    # The dict would keep the last silently; the ambiguity is the finding.
    claims = _claims(tmp_path, "drouin_2020", "chen_2021")
    problems = cc.alias_problems(
        {"citation_aliases": "x_2020 -> drouin_2020, x_2020 -> chen_2021"}, claims)
    assert any("aliased more than once" in p for p in problems)


def test_no_aliases_declared_is_never_a_problem(tmp_path):
    assert cc.alias_problems({}, _claims(tmp_path, "drouin_2020")) == []


def test_alias_does_not_chain(tmp_path):
    # a -> b -> c must not resolve a to c: an alias points at a real ledger only, so
    # no chain (and no cycle) can form.
    claims = _claims(tmp_path, "real_2020")
    aliases = cc.citation_aliases({"citation_aliases": "a_2020 -> b_2020, b_2020 -> real_2020"})
    assert cc.ledger_path_for(claims, "a", "2020", aliases) is None
    assert cc.ledger_path_for(claims, "b", "2020", aliases).name == "real_2020.md"


def test_spelled_and_does_not_turn_year_range_into_citation():
    # Why the conjunction pattern demands whitespace around "and" and a capitalised
    # surname either side: a year range is the form closest to a two-author cite.
    assert cc.extract_citations("between 2018 and 2020") == set()
    assert cc.extract_citations("The work ran between 2018 and 2020 at the lab.") == set()


def test_ignores_bare_year_running_text():
    # No parenthesis touching the year → not a single-author citation.
    text = "Since 2020 the field changed, and by 2019 it was clear, see Figure 2020."
    assert cc.extract_citations(text) == set()


def test_stopwords_and_non_year_numbers():
    text = "see Section (Table 2020) and (Model 4096) and (Figure 2018)"
    found = cc.extract_citations(text)
    # 4096 is not a 19xx/20xx year; Table/Figure are stopwords.
    assert found == set()


# --- gating ---

def test_gated_prefixes_default_when_placeholder():
    assert cc.gated_prefixes({"gated_paths": "<placeholder>"}) == cc.DEFAULT_GATED
    assert cc.gated_prefixes({}) == cc.DEFAULT_GATED


def test_gated_prefixes_parsed():
    prefixes = cc.gated_prefixes({"gated_paths": "content/notes/, content/reviews/"})
    assert prefixes == ["content/notes/", "content/reviews/"]


def test_is_gated_excludes_verified_claims():
    assert cc.is_gated("content/concept_notes/x.md", cc.DEFAULT_GATED)
    assert not cc.is_gated("literature/verified_claims/smith_2020.md", cc.DEFAULT_GATED)
    assert not cc.is_gated("content/_ledger/skin_rules.md", cc.DEFAULT_GATED)


# --- numeric detection ---

def test_numeric_markers_detected():
    assert cc.find_numeric_markers("as shown previously [42] and also [7, 9]")
    assert cc.find_numeric_markers("the method.⁵⁴ was applied")
    assert cc.find_numeric_markers("as shown previously⁴² in the work")


def test_maths_superscripts_not_flagged():
    # Exponents on a single variable / Greek letter / closing paren are NOT
    # citation markers (quantum-dogfood false positives).
    assert not cc.find_numeric_markers("scales as κ² in the regime")
    assert not cc.find_numeric_markers("the bound is O(log N)³ overall")
    assert not cc.find_numeric_markers("complexity N² in the worst case")


# --- ledger / paper presence against a tmp corpus ---

LEDGER_TWO_CLAIMS = (
    "# Verified Claims — Smith et al. (2020)\n\n"
    "## Claim 1: efficiency\n\n> \"a verbatim quote about efficiency from the paper\"\n\n"
    "**ID:** efficiency\n**Location:** Results\n\n"
    "## Claim 2: scaling\n\n> \"a verbatim quote about scaling from the paper\"\n\n"
    "**Location:** Discussion\n"
)


def _tmp_corpus(tmp_path, with_paper=False, with_ledger=False, ledger_body="x" * 600):
    (tmp_path / "verified_claims").mkdir()
    if with_paper:
        (tmp_path / "smith_2020.html").write_text("x" * 600, encoding="utf-8")
    if with_ledger:
        (tmp_path / "verified_claims" / "smith_2020.md").write_text(
            ledger_body, encoding="utf-8")
    return tmp_path


def test_check_text_missing_ledger(tmp_path):
    lit = _tmp_corpus(tmp_path, with_paper=True, with_ledger=False)
    mp, ml, cp = cc.check_text("per Smith et al. 2020", "x.md", lit, check_papers=True)
    assert mp == [] and ml == ["x.md: smith 2020"] and cp == []


def test_check_text_missing_paper(tmp_path):
    lit = _tmp_corpus(tmp_path, with_paper=False, with_ledger=True)
    mp, ml, cp = cc.check_text("per Smith et al. 2020", "x.md", lit, check_papers=True)
    assert mp == ["x.md: smith 2020"] and ml == [] and cp == []


def test_check_text_no_corpus_skips_paper(tmp_path):
    # check_papers=False (the --no-corpus / CI path): paper absent is fine,
    # a missing ledger still fails.
    lit = _tmp_corpus(tmp_path, with_paper=False, with_ledger=True)
    mp, ml, cp = cc.check_text("per Smith et al. 2020", "x.md", lit, check_papers=False)
    assert mp == [] and ml == [] and cp == []


def test_check_text_fully_covered(tmp_path):
    lit = _tmp_corpus(tmp_path, with_paper=True, with_ledger=True)
    mp, ml, cp = cc.check_text("per Smith et al. 2020", "x.md", lit, check_papers=True)
    assert mp == [] and ml == [] and cp == []


# --- claim-ID granularity (Layer 2b) ---

def test_ledger_claim_ids_ordinal_and_alias(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    ids = cc.ledger_claim_ids(lit / "verified_claims" / "smith_2020.md")
    assert {"c1", "c2", "efficiency"} <= ids


def test_valid_claim_ref_passes(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    for ref in ("#c1", "#c2", "#efficiency"):
        _, _, cp = cc.check_text(f"per (Smith et al. 2020 {ref})", "x.md", lit,
                                 check_papers=False, claims="optional")
        assert cp == [], ref


def test_bogus_claim_ref_fails(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    _, _, cp = cc.check_text("per (Smith et al. 2020 #c9)", "x.md", lit,
                             check_papers=False, claims="optional")
    assert len(cp) == 1 and "c9" in cp[0]


def test_bare_cite_optional_passes_required_fails(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    _, _, cp_opt = cc.check_text("per Smith et al. 2020", "x.md", lit,
                                 check_papers=False, claims="optional")
    assert cp_opt == []
    _, _, cp_req = cc.check_text("per Smith et al. 2020", "x.md", lit,
                                 check_papers=False, claims="required")
    assert len(cp_req) == 1 and "needs a #claim ref" in cp_req[0]


# --- ordinal vs slug refs: bare ordinals rejected in strict mode ---

def test_ledger_claim_id_sets_splits_ordinals_and_slugs(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    ordinals, slugs = cc.ledger_claim_id_sets(lit / "verified_claims" / "smith_2020.md")
    assert ordinals == {"c1", "c2"} and slugs == {"efficiency"}


def test_ordinal_ref_ok_optional_blocked_when_forbidden(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    # optional posture leaves ordinals alone (back-compat).
    _, _, cp = cc.check_text("per (Smith et al. 2020 #c1)", "x.md", lit,
                             check_papers=False, claims="optional")
    assert cp == []
    # strict (forbid) rejects the bare ordinal with a slug-nudge.
    _, _, cp2 = cc.check_text("per (Smith et al. 2020 #c1)", "x.md", lit,
                              check_papers=False, claims="required",
                              forbid_ordinal_refs=True)
    assert len(cp2) == 1 and "ordinal" in cp2[0]


def test_slug_ref_allowed_when_ordinals_forbidden(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    _, _, cp = cc.check_text("per (Smith et al. 2020 #efficiency)", "x.md", lit,
                             check_papers=False, claims="required",
                             forbid_ordinal_refs=True)
    assert cp == []


def test_slug_literally_named_c1_is_allowed(tmp_path):
    # An explicit **ID:** c1 is a stable slug, not the positional ordinal — it
    # survives reorder, so it passes even when bare ordinals are forbidden.
    body = ("## Claim 1: a\n\n> \"a verbatim quote about the first claim here\"\n\n"
            "**ID:** c1\n**Location:** Results\n")
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=body)
    _, _, cp = cc.check_text("per (Smith et al. 2020 #c1)", "x.md", lit,
                             check_papers=False, claims="required",
                             forbid_ordinal_refs=True)
    assert cp == []


def test_required_config_forbids_ordinal_end_to_end(tmp_path, monkeypatch):
    # claim_ids: required turns on the ordinal ban via config (no flag); the
    # explicit slug passes, and --allow-ordinal-refs overrides the ban.
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    cfg = tmp_path / "ledger.config.md"
    cfg.write_text("gated_paths: content/concept_notes/\nclaim_ids: required\n",
                   encoding="utf-8")
    argv = _gated_stdin_argv(lit, cfg)
    assert _run_main_stdin(monkeypatch, "per (Smith et al. 2020 #c2)", argv) == 1
    assert _run_main_stdin(monkeypatch, "per (Smith et al. 2020 #efficiency)", argv) == 0
    assert _run_main_stdin(monkeypatch, "per (Smith et al. 2020 #c2)",
                           argv + ["--allow-ordinal-refs"]) == 0


def test_claims_off_ignores_refs(tmp_path):
    lit = _tmp_corpus(tmp_path, with_ledger=True, ledger_body=LEDGER_TWO_CLAIMS)
    _, _, cp = cc.check_text("per (Smith et al. 2020 #c9)", "x.md", lit,
                             check_papers=False, claims="off")
    assert cp == []


def test_claim_mode_default_and_parse():
    assert cc.claim_mode({}) == "optional"
    assert cc.claim_mode({"claim_ids": "required  # comment"}) == "required"
    assert cc.claim_mode({"claim_ids": "off"}) == "off"
    assert cc.claim_mode({"claim_ids": "<placeholder>"}) == "optional"


def test_short_surname_does_not_overmatch(tmp_path):
    # "Li 2020" must NOT be treated as covered by an unrelated "lin_2020" file.
    lit = _tmp_corpus(tmp_path, with_paper=False, with_ledger=False)
    (lit / "verified_claims" / "lin_2020.md").write_text("x" * 600, encoding="utf-8")
    assert not cc.ledger_on_disk(lit / "verified_claims", "li", "2020")
    # The exact surname still matches.
    (lit / "verified_claims" / "li_2020.md").write_text("x" * 600, encoding="utf-8")
    assert cc.ledger_on_disk(lit / "verified_claims", "li", "2020")


def test_year_not_substring_overmatch(tmp_path):
    lit = _tmp_corpus(tmp_path, with_paper=False, with_ledger=False)
    (lit / "verified_claims" / "smith_20200.md").write_text("x" * 600, encoding="utf-8")
    assert not cc.ledger_on_disk(lit / "verified_claims", "smith", "2020")


def test_register_usable(tmp_path):
    _tmp_corpus(tmp_path)
    header = "key\tc2\tc3\tc4\tc5\tc6\tc7\tc8\tstatus\n"
    (tmp_path / "REGISTER.tsv").write_text(
        header + "smith_2020\t\t\t\t\t\t\t\tverified\n", encoding="utf-8")
    assert cc.register_usable(tmp_path / "REGISTER.tsv", "smith", "2020")
    assert not cc.register_usable(tmp_path / "REGISTER.tsv", "smith", "2019")


# --- numeric_citations posture (config key, parallel to claim_ids) ---

def test_numeric_mode_default_and_parse():
    assert cc.numeric_mode({}) == "warn"
    assert cc.numeric_mode({"numeric_citations": "block  # comment"}) == "block"
    assert cc.numeric_mode({"numeric_citations": "ignore"}) == "ignore"
    assert cc.numeric_mode({"numeric_citations": "<placeholder>"}) == "warn"


def _run_main_stdin(monkeypatch, text, argv):
    """Run check_citations.main() in --stdin mode; return its exit code."""
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    monkeypatch.setattr(sys, "argv", ["check_citations.py", *argv])
    return cc.main()


def _gated_stdin_argv(lit, cfg):
    return ["--stdin", "--path", "content/concept_notes/x.md", "--no-corpus",
            "--literature-dir", str(lit), "--config", str(cfg)]


def test_numeric_config_block_fires_end_to_end(tmp_path, monkeypatch):
    # A project that sets numeric_citations: block fails the gate on a [42]
    # marker with no --numeric flag — all three gates honour the config posture.
    lit = _tmp_corpus(tmp_path)
    cfg = tmp_path / "ledger.config.md"
    cfg.write_text("gated_paths: content/concept_notes/\nnumeric_citations: block\n",
                   encoding="utf-8")
    argv = _gated_stdin_argv(lit, cfg)
    assert _run_main_stdin(monkeypatch, "as shown [42]", argv) == 1
    # An explicit --numeric flag overrides the config block.
    assert _run_main_stdin(monkeypatch, "as shown [42]", argv + ["--numeric", "warn"]) == 0


def test_numeric_default_warn_does_not_fail(tmp_path, monkeypatch):
    # No numeric_citations: key → warn (default): a [42] marker is reported but
    # does not fail the gate.
    lit = _tmp_corpus(tmp_path)
    cfg = tmp_path / "ledger.config.md"
    cfg.write_text("gated_paths: content/concept_notes/\n", encoding="utf-8")
    assert _run_main_stdin(monkeypatch, "as shown [42]", _gated_stdin_argv(lit, cfg)) == 0


# --- claim_header_issues: positional #cN footgun detector ---

def test_claim_header_issues_contiguous_ok(tmp_path):
    p = tmp_path / "smith_2020.md"
    p.write_text("## Claim 1: a\n\n## Claim 2: b\n", encoding="utf-8")
    assert cc.claim_header_issues(p) is None


def test_claim_header_issues_noncontiguous_flagged(tmp_path):
    p = tmp_path / "smith_2020.md"
    p.write_text("## Claim 1: a\n\n## Claim 3: b\n", encoding="utf-8")
    msg = cc.claim_header_issues(p)
    assert msg and "re-point" in msg


def test_claim_header_issues_unnumbered_ignored(tmp_path):
    # Claims addressed only by **ID:** carry no ## Claim N number — not flagged.
    p = tmp_path / "smith_2020.md"
    p.write_text("## Claim: a\n\n## Claim: b\n", encoding="utf-8")
    assert cc.claim_header_issues(p) is None
