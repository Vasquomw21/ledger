# Tests for the dependency-free markdown renderer used by the judge bundle.
import md_render as md


def test_headers_and_inline():
    html = md.render_markdown("# Title\n\nSome **bold** and *italic* text.")
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_bold_field_line():
    html = md.render_markdown("**ID:** not-from-known-backbone")
    assert "<strong>ID:</strong>" in html
    assert "not-from-known-backbone" in html


def test_underscores_are_not_italics():
    # Claim addresses are full of underscores; they must survive verbatim.
    html = md.render_markdown("See andersen_2020:no-lab-scenario and pekar_2022:multi.")
    assert "andersen_2020:no-lab-scenario" in html
    assert "<em>" not in html


def test_blockquote_quote():
    html = md.render_markdown('> "a verbatim quote"')
    assert "<blockquote>" in html
    assert "a verbatim quote" in html


def test_unordered_and_ordered_lists():
    assert "<ul><li>one</li><li>two</li></ul>" in md.render_markdown("- one\n- two")
    assert "<ol><li>first</li></ol>" in md.render_markdown("1. first")


def test_table():
    html = md.render_markdown("| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<table>" in html and "<th>a</th>" in html and "<td>1</td>" in html


def test_link():
    html = md.render_markdown("see [the paper](https://doi.org/10.1/x)")
    assert '<a href="https://doi.org/10.1/x"' in html and ">the paper</a>" in html


def test_frontmatter_as_table():
    html = md.render_markdown('---\npaper: "A et al."\ndoi: 10.1/x\n---\n\nBody.', frontmatter="table")
    assert 'class="fm"' in html
    assert "<th>paper</th>" in html and "A et al." in html
    assert "<p>Body.</p>" in html


def test_frontmatter_drop():
    html = md.render_markdown("---\nsecret: x\n---\n\nBody.", frontmatter="drop")
    assert "secret" not in html and "<p>Body.</p>" in html


def test_no_script_injection():
    html = md.render_markdown('A <script>alert(1)</script> and `<b>code</b>`.')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<code>&lt;b&gt;code&lt;/b&gt;</code>" in html


def test_split_frontmatter():
    fm, body = md.split_frontmatter('---\nkey: value\n---\nrest')
    assert fm == {"key": "value"}
    assert body.strip() == "rest"
