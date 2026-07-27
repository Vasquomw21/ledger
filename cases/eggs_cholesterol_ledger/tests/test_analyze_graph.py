# Tests for the read-only validity-assistance analyzer (Layer 4 assist; corpus-free).
# Builds small claim graphs via build_graph and checks each query: degree ranking,
# dependency closure, unassessed-edge listing, shared-premise reuse, and articulation
# (load-bearing cut) detection on a support chain.
import analyze_graph as ag
import build_graph as bg


def _ledger(claims_dir, key, slug, edges=()):
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", "", "## Claim 1: summary", "",
             '> "a quote"', "", f"**ID:** {slug}", "**Location:** Section 1"]
    lines += list(edges)
    lines.append("")
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _graph(tmp_path):
    return bg.build_graph(tmp_path / "vc", tmp_path / "inquiry.md", tmp_path / "assess")


def _chain(tmp_path):
    """leaf:x underpins mid:m underpins top:t (a support chain)."""
    vc = tmp_path / "vc"
    _ledger(vc, "leaf", "x", ["**Supports:** mid:m (grounded by #x)"])
    _ledger(vc, "mid", "m", ["**Supports:** top:t (grounded by #m)"])
    _ledger(vc, "top", "t")
    return _graph(tmp_path)


def test_load_bearing_ranks_in_degree(tmp_path):
    graph = _chain(tmp_path)
    lb = ag.load_bearing(graph)
    assert lb[0]["node"] == "mid:m"          # targeted once + grounds once = weight 2
    assert lb[0]["total"] == 2


def test_dependency_closure_walks_supports(tmp_path):
    graph = _chain(tmp_path)
    closure = ag.dependency_closure(graph, "top:t")
    assert closure == ["leaf:x", "mid:m"]


def test_unassessed_edges_lists_recless(tmp_path):
    graph = _chain(tmp_path)
    ua = ag.unassessed_edges(graph)
    assert len(ua) == 2                       # both supports edges carry no [rec:]
    assert all(e["type"] == "supports" for e in ua)


def test_load_bearing_cut_identifies_articulation(tmp_path):
    graph = _chain(tmp_path)
    cuts = ag.load_bearing_cuts(graph, "top:t")
    assert cuts == ["mid:m"]                   # remove mid and leaf can no longer reach top
    assert "leaf:x" not in cuts


def test_shared_premise_reuses_double_count(tmp_path):
    vc = tmp_path / "vc"
    _ledger(vc, "s1", "c", ["**Supports:** topic:t (grounded by #c)",
                            "**Correlated-with:** s2:c (grounded by #c)"])
    _ledger(vc, "s2", "c", ["**Supports:** topic:t (grounded by #c)"])
    _ledger(vc, "topic", "t")
    findings = ag.shared_premises(vc)
    assert any("s1" in f and "s2" in f for f in findings)


def test_empty_graph_is_quiet(tmp_path):
    (tmp_path / "vc").mkdir()
    graph = _graph(tmp_path)
    assert ag.load_bearing(graph) == []
    assert ag.unassessed_edges(graph) == []
    assert ag.dependency_closure(graph, "nothing:here") == []
    assert ag.load_bearing_cuts(graph, "nothing:here") == []
