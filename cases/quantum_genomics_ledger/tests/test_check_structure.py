# Tests for the structure gate (corpus-free; tmp fixtures). Proves the
# pristine-path invariant (empty graph passes under optional AND required) and
# that real problems — dangling target, missing/unresolvable grounding,
# contradictory edges, a bad qid reference — are caught.
import check_structure as cs


def _ledger(claims_dir, key, *, claims=("c-a",), edges=(), fields=()):
    """Minimal ledger: one `## Claim` + `**ID:**` per slug, with any in-band edge
    or qid-field lines appended under the first claim."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'paper: "X"', "---", ""]
    for i, slug in enumerate(claims, start=1):
        lines += [f"## Claim {i}: summary", "", '> "a verbatim quote"', "",
                  f"**ID:** {slug}", "**Location:** Section 1"]
        if i == 1:
            lines += list(edges) + list(fields)
        lines.append("")
    (claims_dir / f"{key}.md").write_text("\n".join(lines), encoding="utf-8")


def _inquiry(tmp_path, *qids):
    path = tmp_path / "inquiry.md"
    body = "\n\n".join(f"## Sub-question\n**id:** {q}" for q in qids)
    path.write_text(f"# Inquiry\n\n{body}\n", encoding="utf-8")
    return path


# --- pristine-path invariant ----------------------------------------------

def test_empty_graph_passes_optional(tmp_path):
    claims = tmp_path / "verified_claims"
    claims.mkdir()
    assert cs.structure_problems(claims, tmp_path / "inquiry.md") == []


def test_empty_graph_passes_required_via_main(tmp_path, monkeypatch, capsys):
    claims = tmp_path / "verified_claims"
    claims.mkdir()
    # The invariant that matters: an empty graph is clean even under required.
    assert _run_main(monkeypatch, claims, tmp_path / "inquiry.md", "required") == 0


def test_off_skips(tmp_path, monkeypatch, capsys):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", edges=["**Rebuts:** ghost:x (grounded by #c-a)"])
    rc = _run_main(monkeypatch, claims, tmp_path / "inquiry.md", "off")
    assert rc == 0
    assert "off" in capsys.readouterr().out


# --- real problems are caught ---------------------------------------------

def test_valid_edge_passes(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020",
            edges=["**Rebuts:** b_2021:c-b (grounded by #c-a)"])
    _ledger(claims, "b_2021", claims=("c-b",))
    assert cs.structure_problems(claims, tmp_path / "inquiry.md") == []


def test_dangling_target(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020",
            edges=["**Rebuts:** ghost_2099:x (grounded by #c-a)"])
    problems = cs.structure_problems(claims, tmp_path / "inquiry.md")
    assert any("target unresolved" in p for p in problems)


def test_missing_grounding(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", edges=["**Supports:** b_2021:c-b"])
    _ledger(claims, "b_2021", claims=("c-b",))
    problems = cs.structure_problems(claims, tmp_path / "inquiry.md")
    assert any("missing (grounded by" in p for p in problems)


def test_unresolvable_grounding(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020",
            edges=["**Supports:** b_2021:c-b (grounded by #no-such-claim)"])
    _ledger(claims, "b_2021", claims=("c-b",))
    problems = cs.structure_problems(claims, tmp_path / "inquiry.md")
    assert any("grounding unresolved" in p for p in problems)


def test_contradictory_edges(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020",
            edges=["**Supports:** b_2021:c-b (grounded by #c-a)",
                   "**Rebuts:** b_2021:c-b (grounded by #c-a)"])
    _ledger(claims, "b_2021", claims=("c-b",))
    problems = cs.structure_problems(claims, tmp_path / "inquiry.md")
    assert any("contradictory edges" in p for p in problems)


def test_bad_addresses_qid(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", fields=["**Addresses:** no-such-q"])
    problems = cs.structure_problems(claims, _inquiry(tmp_path, "real-q"))
    assert any("addresses" in p.lower() and "no-such-q" in p for p in problems)


def test_good_addresses_qid_passes(tmp_path):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", fields=["**Addresses:** real-q"])
    assert cs.structure_problems(claims, _inquiry(tmp_path, "real-q")) == []


# --- posture exit codes via main() ----------------------------------------

def test_required_fails_on_problem(tmp_path, monkeypatch, capsys):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", edges=["**Rebuts:** ghost:x (grounded by #c-a)"])
    assert _run_main(monkeypatch, claims, tmp_path / "inquiry.md", "required") == 1


def test_optional_warns_but_passes(tmp_path, monkeypatch, capsys):
    claims = tmp_path / "verified_claims"
    _ledger(claims, "a_2020", edges=["**Rebuts:** ghost:x (grounded by #c-a)"])
    assert _run_main(monkeypatch, claims, tmp_path / "inquiry.md", "optional") == 0


def _run_main(monkeypatch, claims_dir, inquiry, mode):
    argv = ["check_structure.py", "--claims-dir", str(claims_dir),
            "--inquiry", str(inquiry), "--structure", mode]
    monkeypatch.setattr("sys.argv", argv)
    return cs.main()
