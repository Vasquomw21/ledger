# The two surfaces render the three trust layers from ONE shared model, in one DOM order,
# with one vocabulary. These pin the spec's acceptance additions: order is trust -> derived
# -> judgements -> interpretation; a declared cause never reads as mechanically established;
# a sealed record never reads as correct; each empty layer has its own honest state; the
# boundaries survive with JavaScript disabled; and every pack action opens a trace ANCHOR,
# never the page top.
import assess_record as ar
import build_judge_pack as bjp
import judge_dashboard as jd

FINDING = ('---\nauthor: R. Curator\ndate: "20260615"\n---\n\n'
           "# Finding\n\nThe authored lesson, stated first.\n\n## Detail\nMore.\n")


def _ledger(claims_dir, key, slug, quote, *, extra=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", "",
             "## Claim 1: summary", "", f'> "{quote}"', "",
             f"**ID:** {slug}", "**Location:** Section 1", *extra, ""]
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _full_project(tmp_path, *, finding=FINDING):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledger.config.md").write_text(
        "project_name: layercase\ngated_paths: content/finding.md\n", encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    content = tmp_path / "content"
    assess = content / "assessments"
    (assess / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    # sealed WHI pair (typed), declared-only null pair (typed), unrelated rhetorical flag
    _ledger(claims, "chen_2021", "whi", "WHI finding", extra=[
        "**Supports:** zhao_2022:harmful (grounded by #whi)",
        "**Correlated-with:** sun_2021:whi (grounded by #whi) "
        "[kind: exact-cohort-reuse; both identify the WHI cohort]"])
    _ledger(claims, "sun_2021", "whi", "WHI finding too",
            extra=["**Supports:** zhao_2022:harmful (grounded by #whi)"])
    _ledger(claims, "dehghan_2020", "pool", "pooled null", extra=[
        "**Supports:** drouin_2020:null (grounded by #pool)",
        "**Correlated-with:** rong_2013:pool (grounded by #pool) "
        "[kind: overlapping-pools; overlapping cohorts of the same design]"])
    _ledger(claims, "rong_2013", "pool", "pooled null too",
            extra=["**Supports:** drouin_2020:null (grounded by #pool)"])
    _ledger(claims, "zhao_2022", "harmful", "eggs are harmful")
    _ledger(claims, "drouin_2020", "null", "no association")

    def record(**kw):
        ar.write_record(ar.build_record(claims_dir=claims, **kw), assess_dir=assess)

    record(kind="correlated-with", rec_id="whi-double-count", subject="chen_2021:whi",
           grounding=["chen_2021:whi", "sun_2021:whi"], span="", assessed_date="20260101")
    record(kind="rhetorical", rec_id="zhao-flag", subject="zhao_2022:harmful",
           grounding=["zhao_2022:harmful"], span="harmful", assessed_date="20260102")
    if finding is not None:
        (content / "finding.md").write_text(finding, encoding="utf-8")
    return tmp_path


def _empty_project(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledger.config.md").write_text(
        "project_name: emptycase\ngated_paths: content/finding.md\n", encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    content = tmp_path / "content"
    (content / "assessments" / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    _ledger(claims, "solo_2020", "c", "a lone claim with no edges")   # no warnings, no records
    return tmp_path


def _pack_index(tmp_path):
    bjp.build_pack(_full_project(tmp_path), tmp_path / "pack")
    return (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")


def _surfaces(tmp_path):
    root = _full_project(tmp_path)
    bjp.build_pack(root, tmp_path / "pack")
    pack = (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")
    dash = jd.render_html(root)
    return pack, dash


# ---- DOM order and shared model ---------------------------------------------

def test_both_surfaces_stack_the_layers_in_the_same_order(tmp_path):
    for html in _surfaces(tmp_path):
        order = [html.index('id="derived"'), html.index('id="judgements"'),
                 html.index('id="interpretation"')]
        assert order == sorted(order)
        # trust state (the verification ceiling) leads everything
        assert html.index("ceiling") < order[0]


def test_both_surfaces_share_the_layer_vocabulary(tmp_path):
    for html in _surfaces(tmp_path):
        for text in (jd.LAYER1_HEADING, jd.LAYER2_HEADING, jd.LAYER3_HEADING,
                     jd.LAYER2_BOUNDARY, jd.LAYER3_BOUNDARY):
            assert text in html


# ---- no layer converts provenance into proof --------------------------------

def test_a_declared_cause_never_renders_as_mechanically_established(tmp_path):
    for html in _surfaces(tmp_path):
        derived = html[html.index('id="derived"'):html.index('id="judgements"')]
        # the kind sits under an author-declared tag, and the layer says as much
        assert "author-declared" in derived
        assert "not a machine-established fact" in derived
        # the basis is labelled DECLARED — it is authored, not a source-verified fact
        assert "Declared basis" in derived and "Declared cause" in derived
        # and never claims the correlation is proven
        assert "confirmed" not in derived.lower() and "proved" not in derived.lower()


def test_a_sealed_record_never_renders_as_correct(tmp_path):
    for html in _surfaces(tmp_path):
        judged = html[html.index('id="judgements"'):html.index('id="interpretation"')]
        assert "sealing does not establish that a judgement is correct" in judged
        assert "confirmed" not in judged.lower() and "proved" not in judged.lower()
        # the role labels are used; never an unqualified "valid"
        assert "sealed record" in judged
        assert " valid " not in judged.lower()


# ---- honest, distinct empty states ------------------------------------------

def test_each_empty_layer_has_its_own_honest_state(tmp_path):
    root = _empty_project(tmp_path)
    dash = jd.render_html(root)
    derived = dash[dash.index('id="derived"'):dash.index('id="judgements"')]
    judged = dash[dash.index('id="judgements"'):dash.index('id="interpretation"')]
    interp = dash[dash.index('id="interpretation"'):]
    d_msg = "no two supporters of one claim are declared correlated"
    j_msg = "No sealed judgements have been recorded"
    # each empty state lands in its OWN layer and nowhere else — three distinct messages
    assert d_msg in derived and j_msg not in derived
    assert j_msg in judged and d_msg not in judged
    assert jd.LAYER3_EMPTY in interp and j_msg not in interp


# ---- boundaries survive without JavaScript ----------------------------------

def test_the_boundaries_are_visible_without_javascript(tmp_path):
    # In the dashboard the tab panels are JS-toggled (data-panel, hidden); the three layers
    # sit in <main> BEFORE them, so every boundary appears ahead of the first panel and is
    # never gated behind a hidden panel or a <details>.
    _pack, dash = _surfaces(tmp_path)
    first_panel = dash.index("data-panel=")
    for boundary in (jd.LAYER2_BOUNDARY, jd.LAYER3_BOUNDARY):
        assert dash.index(boundary) < first_panel
    # the relevant sealed record is open, not folded into <details>
    judged = dash[dash.index('id="judgements"'):dash.index('id="interpretation"')]
    head, _, _tail = judged.partition("<details")
    assert "whi-double-count" in head


# ---- pack actions open a trace anchor, never the page top -------------------

def test_every_pack_action_opens_a_trace_anchor(tmp_path):
    import re
    index = _pack_index(tmp_path)
    assert 'href="trace.html"' not in index          # never the bare page top
    hrefs = re.findall(r'href="trace\.html([^"]*)"', index)
    assert hrefs and all(h.startswith("#") and len(h) > 1 for h in hrefs)
