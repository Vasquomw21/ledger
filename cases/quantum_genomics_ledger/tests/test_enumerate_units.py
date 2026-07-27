# Tests for tools/enumerate_units.py — the mechanical unit enumerator. Corpus-free:
# a synthetic HTML string in, an expected manifest out, plus the determinism self-test.
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "literature"))
import enumerate_units as eu

HTML = (
    "<html><body>"
    "<h1>The heading here is long enough to be a unit</h1>"
    "<p>First paragraph that is clearly long enough to count.</p>"
    "<p>tiny</p>"  # below UNIT_MIN_CHARS -> dropped
    "<ul><li>A list item that is also sufficiently long to be counted.</li></ul>"
    "</body></html>"
)


def _lit(tmp_path):
    lit = tmp_path / "literature"
    lit.mkdir()
    (lit / "foo.html").write_text(HTML, encoding="utf-8")
    return lit


def test_html_enumeration_drops_short_and_orders(tmp_path):
    lit = _lit(tmp_path)
    m = eu.build_manifest(lit, "foo", "essay", "20260101")
    loci = [u["locus"] for u in m["units"]]
    assert loci == ["p1", "p2", "p3"]            # h1, p, li in document order; 'tiny' dropped
    assert m["units"][0]["text"].startswith("The heading")
    assert m["addressing"] == "html-block"
    assert m["fully_enumerable"] is True


def test_manifest_seal_consistent(tmp_path):
    lit = _lit(tmp_path)
    m = eu.build_manifest(lit, "foo", "essay", "20260101")
    assert m["manifest_sha256"] == eu.manifest_digest(m)


def test_enumeration_is_byte_deterministic(tmp_path):
    lit = _lit(tmp_path)
    a = eu.build_manifest(lit, "foo", "essay", "20260101")
    b = eu.build_manifest(lit, "foo", "essay", "20260101")
    assert eu.render(a) == eu.render(b)


def test_main_writes_and_check_passes(tmp_path):
    lit = _lit(tmp_path)
    rc = eu.main(["--key", "foo", "--source-type", "essay",
                  "--literature-dir", str(lit), "--date", "20260101"])
    assert rc == 0
    out = lit / "units" / "foo.units.json"
    assert out.is_file()
    assert json.loads(out.read_text())["key"] == "foo"
    # --check re-enumerates and must be byte-identical.
    assert eu.main(["--key", "foo", "--source-type", "essay",
                    "--literature-dir", str(lit), "--check"]) == 0


def test_missing_raw_raises(tmp_path):
    lit = tmp_path / "literature"
    lit.mkdir()
    try:
        eu.build_manifest(lit, "absent", "essay", "20260101")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
