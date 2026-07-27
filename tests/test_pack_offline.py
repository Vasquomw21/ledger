# The pack is the judge's only interface: a folder, opened from disk, with no repository,
# no Python and no network. These pin what that reader is owed — every link resolving from
# the page it is written on, the evidence readable without scripts, and the palette legible
# in both themes. String-matching a link on the index cannot see a sub-page link that is
# missing its prefix, so these resolve against the built bundle instead.
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag

import assess_record as ar
import build_judge_pack as bjp

FINDING = """# Finding — a case

The lesson this case teaches, stated first.

## Detail
The inference is contested [rec: a-faith].
"""


def _project(tmp_path):
    (tmp_path / "ledger.config.md").write_text(
        "project_name: offlinecase\nprovenance: required\n"
        "gated_paths: content/finding.md\n", encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    (claims / "a_2020.md").write_text("\n".join([
        "---", 'paper: "A et al. (2020)"', 'doi: "10.1/a"', "verified_verdict: pass",
        "body_sha256: " + ("a" * 64), "---", "",
        "## Claim 1: premise", "", '> "the grounding quote"', "",
        "**ID:** p", "**Location:** Abstract",
        "**Supports:** b_2021:c (grounded by #p) [rec: a-supports-c]", "",
    ]), encoding="utf-8")
    (claims / "b_2021.md").write_text("\n".join([
        "---", 'paper: "B et al. (2021)"', "verified_verdict: pass",
        "body_sha256: " + ("b" * 64), "---", "",
        "## Claim 1: conclusion", "", '> "we do not believe it is plausible"', "",
        "**ID:** c", "**Location:** Discussion", "",
    ]), encoding="utf-8")
    content = tmp_path / "content"
    assess = content / "assessments"
    (assess / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    (content / "finding.md").write_text(FINDING, encoding="utf-8")

    def record(**kw):
        ar.write_record(ar.build_record(claims_dir=claims, **kw), assess_dir=assess)

    record(kind="edge", rec_id="a-supports-c", subject="b_2021:c",
           grounding=["a_2020:p"], span="", assessed_date="20260101")
    record(kind="faithfulness", rec_id="a-faith", subject="b_2021:c",
           grounding=["a_2020:p"], span="the grounding quote",
           assessed_date="20260101", disputes=["a-supports-c"])
    return tmp_path


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self._text = [], set(), []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        if a.get("id"):
            self.ids.add(a["id"])
        for attr in ("href", "src"):
            if attr in a:
                self.links.append((tag, a[attr]))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    @property
    def text(self):
        # A reader sees collapsed whitespace: a source line-wrap inside a sentence
        # renders correctly and must not read as absent text.
        return re.sub(r"\s+", " ", " ".join(self._text))


def _build(tmp_path):
    out = tmp_path / "pack"
    bjp.build_pack(_project(tmp_path), out)
    pages = {}
    for p in sorted(out.rglob("*.html")):
        page = _Page()
        page.feed(p.read_text(encoding="utf-8"))
        pages[p.relative_to(out).as_posix()] = page
    return out, pages


# ---- the bundle is self-contained -------------------------------------------

def test_every_internal_link_resolves_from_the_page_it_is_written_on(tmp_path):
    out, pages = _build(tmp_path)
    broken = []
    for name, page in pages.items():
        base = (out / name).parent
        for _tag, val in page.links:
            if val.startswith(("http", "mailto:", "data:", "//")):
                continue
            target, _frag = urldefrag(val)
            if target and not (base / unquote(target)).resolve().is_file():
                broken.append(f"{name} -> {val}")
    assert not broken, f"dead links in the bundle: {broken}"


def test_every_fragment_resolves_to_an_id_that_exists(tmp_path):
    out, pages = _build(tmp_path)
    dangling = []
    for name, page in pages.items():
        base = (out / name).parent
        for _tag, val in page.links:
            if val.startswith(("http", "mailto:", "data:", "//")):
                continue
            target, frag = urldefrag(val)
            if not frag:
                continue
            key = (base / unquote(target)).resolve().relative_to(out).as_posix() \
                if target else name
            if key in pages and frag not in pages[key].ids:
                dangling.append(f"{name} -> {val}")
    assert not dangling, f"fragments pointing at no id: {dangling}"


def test_a_sub_page_links_back_to_the_index_above_it(tmp_path):
    # The bug this pins: a ledger page is written to ledgers/, so a bare "index.html"
    # back-link resolves to ledgers/index.html and 404s for a reader opening the folder.
    _out, pages = _build(tmp_path)
    to_index = [v for tag, v in pages["ledgers/a_2020.html"].links
                if tag == "a" and "index.html" in v]
    assert to_index, "a ledger page must link back to the index"
    assert all(v.startswith("../") for v in to_index), to_index


def test_the_index_offers_no_page_the_build_did_not_write(tmp_path):
    # A content sub-page exists only where its source file does. Naming one unconditionally
    # sends a reader with no source register to a 404 — and the case that has every file
    # cannot show it.
    out, pages = _build(tmp_path)
    for tag, val in pages["index.html"].links:
        if val.endswith(".html") and not val.startswith("http"):
            assert (out / urldefrag(val)[0]).is_file(), f"index offers missing {val}"


def test_no_page_loads_a_remote_asset(tmp_path):
    # Outbound <a href="https://doi.org/…"> is navigation the reader chooses; a src= or
    # a stylesheet link reaches the network on open, and the folder must not.
    out, _pages = _build(tmp_path)
    loaders = re.compile(
        r"""<(?!a[\s>])\w+[^>]*\bsrc\s*=\s*["'](?:https?:)?//"""
        r"""|<link[^>]*\bhref\s*=\s*["'](?:https?:)?//"""
        r"""|url\(\s*["']?(?:https?:)?//""", re.I)
    for p in out.rglob("*"):
        if p.is_file():
            assert not loaders.search(p.read_text(encoding="utf-8", errors="ignore")), p


def test_the_bundle_carries_no_path_from_the_builders_machine(tmp_path):
    out, _pages = _build(tmp_path)
    for p in out.rglob("*"):
        if p.is_file():
            assert "/Users/" not in p.read_text(encoding="utf-8", errors="ignore"), p


# ---- the evidence survives without JavaScript --------------------------------

def test_the_evidence_path_renders_without_scripts(tmp_path):
    _out, pages = _build(tmp_path)
    assert "The lesson this case teaches, stated first." in pages["index.html"].text
    trace = pages["trace.html"].text
    for needle in ("we do not believe it is plausible",   # the subject's quote
                   "Discussion",                          # its locus
                   "the grounding quote",                 # the edge's grounding
                   "a-faith",                             # the judgement record
                   "challenged span",                     # what the dispute contests
                   "does not settle them"):               # the boundary
        assert needle in trace, needle


# ---- the palette is legible in both themes -----------------------------------

def _ratio(fg: str, bg: str) -> float:
    def lum(c):
        v = [int(c.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        f = [(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4) for x in v]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _mix(fg: str, bg: str, pct: float) -> str:
    def ch(c, i):
        return int(c.lstrip("#")[i:i + 2], 16)
    return "#" + "".join(
        f"{int(round(ch(fg, i) * pct + ch(bg, i) * (1 - pct))):02x}" for i in (0, 2, 4))


def _palettes(css: str) -> dict:
    def tokens(block):
        return {m.group(1): m.group(2) for m in
                re.finditer(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;", block)}
    light = tokens(re.search(r":root\s*\{(.*?)\}", css, re.S).group(1))
    dark = tokens(re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S).group(1))
    return {"light": light, "dark": {**light, **dark}}


def _rule(css: str, selector: str) -> str:
    """The winning declaration block for a selector — later rules override earlier ones,
    and the pack deliberately re-asserts its badges after the shared GRAPH_CSS."""
    blocks = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert blocks, f"no rule for {selector}"
    return blocks[-1]


def _decl(block: str, prop: str) -> str:
    m = re.search(rf"(?:^|;)\s*{prop}\s*:\s*([^;]+)", block)
    assert m, f"no {prop} in {block!r}"
    return m.group(1).strip()


def _colour(value: str, tokens: dict) -> str:
    """Resolve a declaration to a hex colour, following var() and color-mix().

    The point is to read what the stylesheet SAYS rather than what the test expects it to
    say: assuming the token makes the check agree with itself even after a rule reverts to
    a colour that cannot be read.
    """
    value = value.strip()
    mix = re.match(r"color-mix\(\s*in\s+srgb\s*,\s*(.+?)\s+([\d.]+)%\s*,\s*(.+?)\s*\)$",
                   value)
    if mix:
        return _mix(_colour(mix.group(1), tokens), _colour(mix.group(3), tokens),
                    float(mix.group(2)) / 100)
    var = re.match(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+?)\s*)?\)$", value)
    if var:
        name = var.group(1)[2:]
        if name in tokens:
            return _colour(tokens[name], tokens)
        assert var.group(2), f"unresolvable var({var.group(1)}) with no fallback"
        return _colour(var.group(2), tokens)
    hexc = re.match(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", value)
    assert hexc, f"unresolvable colour: {value!r}"
    h = hexc.group(1)
    return "#" + ("".join(c * 2 for c in h) if len(h) == 3 else h)


# Each pair names the rule whose colours are read, so a rule that stops using its readable
# token is a failure here rather than an assumption the test quietly preserves.
CONTRAST_PAIRS = [
    ("badge ok", ".badge.ok", "color", "background"),
    ("badge warn", ".badge.warn", "color", "background"),
    ("badge bad", ".badge.bad", "color", "background"),
    ("badge neu", ".badge.neu", "color", "background"),
    ("action label", ".action", "color", "background"),
]


def test_text_meets_wcag_aa_in_both_themes(tmp_path):
    # Read from the shipped stylesheet, not a copy of the palette: a transcription would
    # keep agreeing with itself after the source moved.
    out, _pages = _build(tmp_path)
    css = (out / "assets" / "ledger.css").read_text(encoding="utf-8")
    fails = []
    for theme, c in _palettes(css).items():
        for label, selector, fg_prop, bg_prop in CONTRAST_PAIRS:
            block = _rule(css, selector)
            r = _ratio(_colour(_decl(block, fg_prop), c),
                       _colour(_decl(block, bg_prop), c))
            if r < 4.5:
                fails.append(f"{theme}/{label}: {r:.2f}")
        # the .action label again over its hover fill, and the plain-token pairs
        r = _ratio(_colour(_decl(_rule(css, ".action"), "color"), c),
                   _colour(_decl(_rule(css, ".action:hover"), "background"), c))
        if r < 4.5:
            fails.append(f"{theme}/action label hover: {r:.2f}")
        for label, fg, bg in [("body on page", c["ink"], c["bg"]),
                              ("muted on panel", c["muted"], c["panel"]),
                              ("link on panel", c["accent"], c["panel"]),
                              ("quote on exhibit", c["ink"], c["exhibit-bg"])]:
            r = _ratio(_colour(fg, c), _colour(bg, c))
            if r < 4.5:
                fails.append(f"{theme}/{label}: {r:.2f}")
    assert not fails, f"below WCAG AA (4.5:1): {fails}"


def test_the_keyboard_path_has_a_visible_focus_ring(tmp_path):
    # Every step of finding -> trace is a real link, so the ring is the only thing telling
    # a keyboard reader where they are.
    out, pages = _build(tmp_path)
    css = (out / "assets" / "ledger.css").read_text(encoding="utf-8")
    assert re.search(r":focus-visible\s*(,|\{)", css)
    action = [v for tag, v in pages["index.html"].links
              if tag == "a" and v.startswith("trace.html")]
    assert action, "the action must be an anchor, not a scripted click target"
