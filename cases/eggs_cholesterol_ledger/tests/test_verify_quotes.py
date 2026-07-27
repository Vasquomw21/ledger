# Tests for the verbatim quote verifier. All fixtures are built in tmp_path —
# the suite never touches the git-ignored corpus, so it runs in CI.
import json

import verify_quotes as vq


def classify(span, source):
    """Run classify_span against a source string, pre-computing the three
    normalised haystacks exactly as check_ledger does."""
    return vq.classify_span(span, vq.norm(source), vq.letters(source),
                            vq.mathless(source))


# --- classify_span: the PASS tiers and the digit guard ---

def test_exact_match_passes():
    src = "the algorithm runs in linear time on the input array"
    assert classify("the algorithm runs in linear time", src) == "PASS"


def test_ligature_source_still_passes():
    # Ledger holds true letters; source typeset with ﬁ / eﬃ ligature glyphs.
    src = "the most eﬃcient method we ﬁnd in the ﬁrst experiment overall"
    assert classify("the most efficient method we find in the first", src) == "PASS"


def test_letters_only_fallback_passes_when_digit_free():
    # Source carries an inline citation superscript number the ledger omits;
    # the span itself has no digits, so PASS* is legitimate.
    src = "the method,54 was applied to the sample under controlled conditions"
    assert classify("the method was applied to the sample", src) == "PASS*"


def test_maths_fallback_passes():
    src = "the cost grows as  and dominates every other term in the bound here"
    span = "the cost grows as O(√N) and dominates every other term"
    assert classify(span, src) == "PASS~"


def test_paraphrase_fails():
    src = "we observe a double exponential rate of growth in the regime studied"
    assert classify("double exponential growth rate in the regime", src) == "FAIL"


def test_digit_mismatch_fails():
    # The whole point: a digit-bearing span must match exactly or FAIL — the
    # letters-only fallback must NOT rescue "70%" against a source "90%".
    src = "infection rates fell by 90% across the treated population overall"
    assert classify("infection rates fell by 70% across the treated", src) == "FAIL"


def test_digit_exact_still_passes():
    src = "infection rates fell by 90% across the treated population overall"
    assert classify("infection rates fell by 90% across the treated", src) == "PASS"


def test_short_span_skipped():
    assert classify("too short", "irrelevant source text here") == "SKIP"


# --- extract_quotes: quoted vs editorial blockquotes ---

def test_extract_quotes_separates_notes(tmp_path):
    ledger = tmp_path / "smith_2020.md"
    ledger.write_text(
        '> "a verbatim quoted claim from the paper"\n'
        "> an editorial note with no quotation marks\n",
        encoding="utf-8")
    quotes, n_notes = vq.extract_quotes(ledger)
    assert quotes == ["a verbatim quoted claim from the paper"]
    assert n_notes == 1


# --- check_ledger / main integration on a tmp corpus ---

def test_check_ledger_happy(tmp_path):
    (tmp_path / "smith_2020.txt").write_text(
        "the algorithm runs in linear time on the input", encoding="utf-8")
    ledger = tmp_path / "smith_2020.md"
    ledger.write_text('> "the algorithm runs in linear time"\n', encoding="utf-8")
    tally = vq.check_ledger("smith_2020", ledger, extracted_dir=tmp_path)
    assert tally["pass"] == 1 and tally["fail"] == 0


def test_check_ledger_missing_extract(tmp_path):
    ledger = tmp_path / "smith_2020.md"
    ledger.write_text('> "anything"\n', encoding="utf-8")
    tally = vq.check_ledger("smith_2020", ledger, extracted_dir=tmp_path)
    assert tally["fail"] == 1


def test_main_empty_ledger_dir_is_clean(tmp_path):
    # An empty verified_claims/ is a valid fresh-project state — warn, exit 0,
    # do not abort the commit.
    assert vq.main(ledger_dir=tmp_path, extracted_dir=tmp_path) == 0


def test_main_missing_ledger_dir_errors(tmp_path):
    assert vq.main(ledger_dir=tmp_path / "nope", extracted_dir=tmp_path) == 2


# --- provenance stamp + bound check ---

def _provenance_project(tmp_path, quote="the algorithm runs in linear time"):
    """A tmp project: source + extract + a ledger whose `file:` points at the
    source. Returns (repo_root, ledger_path, extract_path, source_path)."""
    lit = tmp_path / "literature"
    (lit / "verified_claims").mkdir(parents=True)
    (lit / "extracted").mkdir(parents=True)
    source = lit / "smith_2020.html"
    source.write_text("x" * 600 + quote, encoding="utf-8")
    extract = lit / "extracted" / "smith_2020.txt"
    extract.write_text(quote + " on the input array", encoding="utf-8")
    ledger = lit / "verified_claims" / "smith_2020.md"
    ledger.write_text(
        '---\n'
        'file: "literature/smith_2020.html"\n'
        'source_version: "published"\n'
        'retrieved: "20260101"\n'
        'doi: "10.1234/example"\n'
        f'---\n\n> "{quote}"\n', encoding="utf-8")
    return tmp_path, ledger, extract, source


def test_stamp_writes_64hex_hashes(tmp_path):
    _, ledger, extract, source = _provenance_project(tmp_path)
    vq.stamp_ledger(ledger, extract, source, "pass")
    fm = vq.read_frontmatter(ledger)
    assert len(fm["source_sha256"]) == 64 and len(fm["extract_sha256"]) == 64
    assert fm["verified_verdict"] == "pass" and fm["verifier_version"] == vq.VERIFIER_VERSION


def test_binding_passes_then_detects_tamper(tmp_path):
    _, ledger, extract, source = _provenance_project(tmp_path)
    vq.stamp_ledger(ledger, extract, source, "pass")
    assert vq.check_binding(ledger, extract, source) == []
    extract.write_text("a completely different extract body now", encoding="utf-8")
    assert any("extract_sha256 stale" in p for p in vq.check_binding(ledger, extract, source))


def test_binding_missing_stamp(tmp_path):
    _, ledger, extract, source = _provenance_project(tmp_path)
    problems = vq.check_binding(ledger, extract, source)
    assert len(problems) == 1 and "no provenance stamp" in problems[0]


def test_main_required_blocks_unstamped_then_passes_after_stamp(tmp_path):
    repo, _, _, _ = _provenance_project(tmp_path)
    lit = repo / "literature"
    kw = dict(ledger_dir=lit / "verified_claims", extracted_dir=lit / "extracted",
              repo_root=repo, config_path=repo / "absent.config")
    assert vq.main(**kw, provenance="required") == 1   # unstamped → blocked
    assert vq.main(**kw, stamp=True) == 0              # write the stamp
    assert vq.main(**kw, provenance="required") == 0   # now bound → passes
    assert vq.main(**kw, provenance="warn") == 0       # warn never blocks


def test_binding_identity_required(tmp_path):
    # A stamped ledger that carries only `file:` (no version/retrieved/locator)
    # binds fine by default, but fails the source-identity check under required.
    _, ledger, extract, source = _provenance_project(tmp_path)
    ledger.write_text('---\nfile: "literature/smith_2020.html"\n---\n\n'
                      '> "the algorithm runs in linear time"\n', encoding="utf-8")
    vq.stamp_ledger(ledger, extract, source, "pass")
    assert vq.check_binding(ledger, extract, source) == []
    probs = vq.check_binding(ledger, extract, source, require_identity=True)
    assert any("source identity" in p or "locator" in p for p in probs)


def test_main_strict_blocks_when_corpus_absent(tmp_path, capsys):
    # Configured (strict) project: a committed ledger with no extracted text to
    # verify it against is a hard failure (the pristine 'skip' becomes a block).
    lit = tmp_path / "literature"
    (lit / "verified_claims").mkdir(parents=True)
    (lit / "extracted").mkdir(parents=True)
    (lit / "verified_claims" / "smith_2020.md").write_text(
        '---\nfile: "literature/smith_2020.html"\n---\n\n> "a quote"\n', encoding="utf-8")
    kw = dict(ledger_dir=lit / "verified_claims", extracted_dir=lit / "extracted",
              repo_root=tmp_path, config_path=tmp_path / "absent.config")
    assert vq.main(**kw, strict=True) == 1
    assert "no extracted text" in capsys.readouterr().err


def test_main_strict_passes_when_corpus_present(tmp_path):
    # Strict but the corpus IS present: the guard does not fire and the verbatim
    # quote verifies (provenance warn → an unstamped ledger does not block).
    repo, _, _, _ = _provenance_project(tmp_path)
    lit = repo / "literature"
    assert vq.main(ledger_dir=lit / "verified_claims", extracted_dir=lit / "extracted",
                   repo_root=repo, config_path=repo / "absent.config", strict=True) == 0


def test_provenance_mode_off_skips_binding(tmp_path):
    repo, _, _, _ = _provenance_project(tmp_path)
    lit = repo / "literature"
    assert vq.main(ledger_dir=lit / "verified_claims", extracted_dir=lit / "extracted",
                   repo_root=repo, config_path=repo / "absent.config",
                   provenance="off") == 0   # unstamped but off → no bind, exit 0


# --- body binding (corpus-free quote-integrity) ---

def test_ledger_body_excludes_frontmatter(tmp_path):
    p = tmp_path / "x.md"
    p.write_text('---\nfile: "a"\n---\n\n> "the body quote"\n', encoding="utf-8")
    body = vq.ledger_body(p)
    assert "file:" not in body and "the body quote" in body


def test_stamp_writes_body_hash(tmp_path):
    _, ledger, extract, source = _provenance_project(tmp_path)
    vq.stamp_ledger(ledger, extract, source, "pass")
    assert len(vq.read_frontmatter(ledger)["body_sha256"]) == 64


def test_binding_detects_body_edit(tmp_path):
    # The headline gap: a quote edited after stamping (source/extract untouched)
    # is caught by the body hash alone — the check CI can also run.
    _, ledger, extract, source = _provenance_project(tmp_path)
    vq.stamp_ledger(ledger, extract, source, "pass")
    assert vq.check_binding(ledger, extract, source) == []
    ledger.write_text(ledger.read_text(encoding="utf-8").replace(
        "linear time", "constant time"), encoding="utf-8")
    assert any("body_sha256 stale" in p
               for p in vq.check_binding(ledger, extract, source))


def test_binding_flags_pre_v2_stamp(tmp_path):
    # A v1 stamp (source/extract bound, no body) must be flagged for re-stamp.
    _, ledger, extract, source = _provenance_project(tmp_path)
    vq.stamp_ledger(ledger, extract, source, "pass")
    vq.upsert_frontmatter(ledger, {"body_sha256": ""})
    assert any("predates body binding" in p
               for p in vq.check_binding(ledger, extract, source))


# --- verification run-record ---

def test_stamp_writes_run_record(tmp_path):
    # --stamp also writes an auditable run-record mirroring the stamp, sealed by
    # record_sha256, with the transcript hash, toolchain, and source identity.
    repo, ledger, extract, source = _provenance_project(tmp_path)
    lit = repo / "literature"
    kw = dict(ledger_dir=lit / "verified_claims", extracted_dir=lit / "extracted",
              repo_root=repo, config_path=repo / "absent.config")
    assert vq.main(**kw, stamp=True) == 0
    rec_path = lit / "verified_claims" / "_runs" / "smith_2020.run.json"
    assert rec_path.is_file()
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["record_sha256"] == vq.run_record_digest(rec)        # seal consistent
    assert rec["body_sha256"] == vq.read_frontmatter(ledger)["body_sha256"]  # mirrors stamp
    assert len(rec["transcript_sha256"]) == 64 and rec["extract_tool_version"]
    assert rec["doi"] == "10.1234/example"
    assert rec["file"] == "literature/smith_2020.html"
