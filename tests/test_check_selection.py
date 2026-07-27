# Tests for the selection-audit gate (Layer 2; corpus-free). A stamped ledger with no
# register entry is flagged; a source missing discovery/rationale/position is flagged; a
# **Source:** with no ledger is a phantom; a **Position:** not declared is an orphan; a
# declared position with no source and no known-gap is a silent empty side; a gap that
# names it satisfies the invariant. Off posture and the empty/pristine case are not checked.
import check_selection as cs


def _ledger(claims_dir, key, *, stamped=True):
    claims_dir.mkdir(parents=True, exist_ok=True)
    fm = ["---", 'paper: "X"']
    if stamped:
        fm.append('body_sha256: "deadbeef"')
    fm += ["---", "", "## Claim 1: summary", "", '> "a quote"', "", "**ID:** c1", ""]
    (claims_dir / f"{key}.md").write_text("\n".join(fm), encoding="utf-8")


def _register(content_dir, *, positions=(), sources=(), gaps=()):
    content_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "status: active", "---", "", "# Source Register — test", ""]
    lines += ["## Positions", ""]
    for slug, desc in positions:
        lines.append(f"**Position:** {slug} — {desc}")
    lines += ["", "## Sources", ""]
    for heading, fields in sources:
        lines.append(f"### {heading}")
        for field, value in fields:
            lines.append(f"**{field}:** {value}")
        lines.append("")
    lines += ["## Known gaps", ""]
    for gap in gaps:
        lines.append(f"**Gap:** {gap}")
    (content_dir / "source_register.md").write_text("\n".join(lines), encoding="utf-8")


def _paths(tmp_path):
    return (tmp_path / "verified_claims", tmp_path / "content",
            tmp_path / "content" / "source_register.md", tmp_path / "content" / "inquiry.md")


def test_empty_passes(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    claims.mkdir(parents=True)
    content.mkdir(parents=True)
    assert cs.selection_problems(claims, register, inquiry) == []


def test_unregistered_source_flagged(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content)                       # register exists but lists no sources
    problems = cs.selection_problems(claims, register, inquiry)
    assert any("andersen_2020" in p and "unregistered" in p for p in problems)


def test_missing_field_flagged(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content, positions=[("natural-origin", "natural processes")],
              sources=[("Andersen (2020)",
                        [("Source", "andersen_2020"), ("Position", "natural-origin")])])
    problems = cs.selection_problems(claims, register, inquiry)
    assert any("Discovery" in p for p in problems)
    assert any("Rationale" in p for p in problems)


def test_phantom_source_flagged(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    claims.mkdir(parents=True)               # no ledger files → no unregistered noise
    _register(content, positions=[("p1", "view one")],
              sources=[("Ghost (2099)",
                        [("Source", "ghost_2099"), ("Discovery", "x"),
                         ("Rationale", "y"), ("Position", "p1")])])
    problems = cs.selection_problems(claims, register, inquiry)
    assert any("phantom" in p for p in problems)


def test_orphan_position_flagged(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content,
              sources=[("Andersen (2020)",
                        [("Source", "andersen_2020"), ("Discovery", "x"),
                         ("Rationale", "y"), ("Position", "undeclared")])])
    problems = cs.selection_problems(claims, register, inquiry)
    assert any("orphan position" in p for p in problems)


def test_uncovered_position_flagged(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content,
              positions=[("natural-origin", "n"), ("lab-origin", "l")],
              sources=[("Andersen (2020)",
                        [("Source", "andersen_2020"), ("Discovery", "x"),
                         ("Rationale", "y"), ("Position", "natural-origin")])])
    problems = cs.selection_problems(claims, register, inquiry)
    assert any("lab-origin" in p and "empty side" in p for p in problems)


def test_uncovered_position_satisfied_by_gap(tmp_path):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content,
              positions=[("natural-origin", "n"), ("lab-origin", "l")],
              sources=[("Andersen (2020)",
                        [("Source", "andersen_2020"), ("Discovery", "x"),
                         ("Rationale", "y"), ("Position", "natural-origin")])],
              gaps=["lab-origin — no primary lab-leak document ingested yet"])
    assert cs.selection_problems(claims, register, inquiry) == []


def test_off_skips(tmp_path, monkeypatch, capsys):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content)
    assert _run_main(monkeypatch, claims, register, inquiry, "off") == 0
    assert "off" in capsys.readouterr().out


def test_required_fails_warn_warns(tmp_path, monkeypatch):
    claims, content, register, inquiry = _paths(tmp_path)
    _ledger(claims, "andersen_2020")
    _register(content)                       # unregistered source → a problem
    assert _run_main(monkeypatch, claims, register, inquiry, "required") == 1
    assert _run_main(monkeypatch, claims, register, inquiry, "warn") == 0


def _run_main(monkeypatch, claims, register, inquiry, mode):
    argv = ["check_selection.py", "--claims-dir", str(claims),
            "--register", str(register), "--inquiry", str(inquiry),
            "--selection", mode]
    monkeypatch.setattr("sys.argv", argv)
    return cs.main()
