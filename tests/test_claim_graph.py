# Tests for the claim-graph resolver keystone (corpus-free; tmp fixtures).
# Proves the one definition the structure + assessment gates inherit: address
# parsing, edge-line parsing (incl. a missing grounding clause), and resolution
# of a cross-ledger / bare / absent endpoint.
import claim_graph as cg


def _ledger(claims_dir, key, *, claims=("fcs-not-expected",), edges=()):
    """Write a minimal ledger with one `## Claim` + `**ID:**` per slug and any
    in-band edge lines appended under the first claim. Returns the file path."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", ""]
    for i, slug in enumerate(claims, start=1):
        lines += [f"## Claim {i}: summary", "", '> "a verbatim quote"', "",
                  f"**ID:** {slug}", "**Location:** Section 1"]
        if i == 1:
            lines += list(edges)
        lines.append("")
    path = claims_dir / f"{key}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --- address parsing -------------------------------------------------------

def test_parse_address_key_slug():
    addr = cg.parse_address("andersen_2020:fcs-not-expected")
    assert addr.key == "andersen_2020"
    assert addr.slug == "fcs-not-expected"


def test_parse_address_bare_slug_is_this_ledger():
    addr = cg.parse_address("local-claim")
    assert addr.key is None
    assert addr.slug == "local-claim"


def test_parse_address_lowercases():
    addr = cg.parse_address("Andersen_2020:FCS-Not-Expected")
    assert addr == cg.Address("andersen_2020", "fcs-not-expected")


# --- edge-line parsing -----------------------------------------------------

def test_parse_edge_line_full():
    edge = cg.parse_edge_line(
        "**Rebuts:** segreto_2021:fcs-implies-engineering (grounded by #not-from-backbone)",
        originating_key="andersen_2020", line_no=12)
    assert edge.edge_type == "rebuts"
    assert edge.target == cg.Address("segreto_2021", "fcs-implies-engineering")
    assert edge.grounding == "not-from-backbone"
    assert edge.originating_key == "andersen_2020"
    assert edge.line_no == 12


def test_parse_edge_line_hyphenated_type_and_bare_target():
    edge = cg.parse_edge_line("**Depends-on:** local-premise (grounded by #g1)",
                              originating_key="x_2020")
    assert edge.edge_type == "depends-on"
    assert edge.target == cg.Address(None, "local-premise")


def test_parse_edge_line_missing_grounding_is_none():
    edge = cg.parse_edge_line("**Supports:** smith_2020:c1",
                              originating_key="x_2020")
    assert edge is not None
    assert edge.grounding is None


def test_parse_edge_line_non_edge_returns_none():
    assert cg.parse_edge_line("**Location:** Section 3", "x_2020") is None
    assert cg.parse_edge_line("> a quoted line", "x_2020") is None


def test_parse_edge_line_case_insensitive():
    edge = cg.parse_edge_line("**REBUTS:** a_2020:s (grounded by #g)", "b_2020")
    assert edge.edge_type == "rebuts"


# --- ledger-level parsing --------------------------------------------------

def test_parse_ledger_edges_and_iter(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020",
            edges=["**Rebuts:** segreto_2021:fcs-implies-engineering "
                   "(grounded by #fcs-not-expected)"])
    _ledger(claims, "segreto_2021", claims=("fcs-implies-engineering",))
    edges = cg.parse_ledger_edges(claims / "andersen_2020.md")
    assert len(edges) == 1
    assert edges[0].originating_key == "andersen_2020"
    # iter_edges sweeps the whole corpus and skips TEMPLATE.
    (claims / "TEMPLATE.md").write_text("**Rebuts:** a:b (grounded by #c)\n")
    assert len(list(cg.iter_edges(claims))) == 1


# --- resolution ------------------------------------------------------------

def test_resolve_cross_ledger_present(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "segreto_2021", claims=("fcs-implies-engineering",))
    res = cg.resolve(cg.Address("segreto_2021", "fcs-implies-engineering"),
                     "andersen_2020", claims)
    assert res.exists and res.reason == ""
    assert res.ledger_path == claims / "segreto_2021.md"


def test_resolve_bare_slug_uses_originating_ledger(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020", claims=("fcs-not-expected",))
    res = cg.resolve(cg.Address(None, "fcs-not-expected"), "andersen_2020", claims)
    assert res.exists
    assert res.key == "andersen_2020"


def test_resolve_absent_ledger(tmp_path):
    claims = tmp_path / "verified_claims"
    claims.mkdir(parents=True)
    res = cg.resolve(cg.Address("ghost_2099", "x"), "andersen_2020", claims)
    assert not res.exists
    assert "no ledger" in res.reason


def test_resolve_absent_slug(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020", claims=("fcs-not-expected",))
    res = cg.resolve(cg.Address("andersen_2020", "no-such-claim"), "andersen_2020", claims)
    assert not res.exists
    assert "no claim" in res.reason


def test_resolve_ordinal_slug(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020", claims=("fcs-not-expected",))
    # The `## Claim 1` header gives a c1 ordinal even without an explicit slug.
    res = cg.resolve(cg.Address("andersen_2020", "c1"), "andersen_2020", claims)
    assert res.exists


def test_resolve_edge_target_and_grounding(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020",
            edges=["**Rebuts:** segreto_2021:fcs-implies-engineering "
                   "(grounded by #fcs-not-expected)"])
    _ledger(claims, "segreto_2021", claims=("fcs-implies-engineering",))
    edge = cg.parse_ledger_edges(claims / "andersen_2020.md")[0]
    target, grounding = cg.resolve_edge(edge, claims)
    assert target.exists
    assert grounding is not None and grounding.exists


def test_resolve_edge_dangling_target(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020",
            edges=["**Rebuts:** ghost_2099:x (grounded by #fcs-not-expected)"])
    edge = cg.parse_ledger_edges(claims / "andersen_2020.md")[0]
    target, grounding = cg.resolve_edge(edge, claims)
    assert not target.exists
    assert grounding is not None and grounding.exists


# --- per-claim body / quote (assessment binding primitives) ----------------

def test_claim_body_isolates_the_named_claim(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020", claims=("first-claim", "second-claim"))
    body = cg.claim_body(claims / "andersen_2020.md", "second-claim")
    assert body is not None
    assert "**ID:** second-claim" in body
    assert "first-claim" not in body          # the block is isolated


def test_claim_body_resolves_ordinal(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "andersen_2020", claims=("a", "b"))
    assert cg.claim_body(claims / "andersen_2020.md", "c2") is not None
    assert cg.claim_body(claims / "andersen_2020.md", "no-such") is None


def test_claim_quote_extracts_verbatim_text(tmp_path):
    claims = tmp_path / "verified_claims"
    path = claims / "andersen_2020.md"
    claims.mkdir(parents=True)
    path.write_text('---\np: "x"\n---\n\n## Claim 1: s\n\n'
                    '> "the furin cleavage site is not expected"\n\n'
                    "**ID:** fcs\n**Location:** S1\n", encoding="utf-8")
    assert "furin cleavage site is not expected" in cg.claim_quote(path, "fcs")
