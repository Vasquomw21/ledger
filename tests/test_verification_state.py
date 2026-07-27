# The two axes a "verified" badge conflates: what was proved upstream, and what this
# artefact lets its reader repeat. Fixtures build all three states from real stamps.
import json
import sys
from pathlib import Path

import build_judge_pack as bjp
import judge_dashboard as jd
from verify_quotes import ledger_body, sha256_text, run_record_digest

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_HTML = "<html><body><p>the quoted sentence</p></body></html>"


def _ledger_text(key: str, source_rel: str, source_hash: str) -> str:
    return "\n".join([
        "---", f'paper: "{key} (2020)"', 'doi: "10.1/x"',
        f'file: "{source_rel}"', 'source_version: "published"', 'retrieved: "20260101"',
        f"source_sha256: {source_hash}", "extract_sha256: " + ("e" * 64),
        "body_sha256: __BODY__", 'verifier_version: "2"',
        'verified_verdict: "pass"', 'verified_date: "20260101"', "---", "",
        f"# Verified Claims — {key}", "",
        "## Claim 1: the claim", "", '> "the quoted sentence"', "",
        "**ID:** the-claim", "**Location:** Abstract", "",
    ])


def _stamp(claims_dir: Path, key: str, source_rel: str, source_hash: str) -> None:
    """A ledger + run-record that check_manifest accepts, as verify_quotes --stamp
    writes them. The body hash covers only the text below the frontmatter, so writing
    it back into the stamp cannot invalidate it."""
    path = claims_dir / f"{key}.md"
    path.write_text(_ledger_text(key, source_rel, source_hash), encoding="utf-8")
    body = sha256_text(ledger_body(path))
    path.write_text(_ledger_text(key, source_rel, source_hash).replace("__BODY__", body),
                    encoding="utf-8")
    record = {
        "body_sha256": body, "command": "literature/verify_quotes.py --stamp",
        "doi": "10.1/x", "extract_sha256": "e" * 64, "extract_tool": "extract_text.py",
        "extract_tool_version": "test=1", "file": source_rel, "key": key, "pmcid": "",
        "retrieved": "20260101", "source_sha256": source_hash, "url": "",
        "verified_date": "20260101", "verified_verdict": "pass", "verifier_version": "2",
    }
    record["record_sha256"] = run_record_digest(record)
    runs = claims_dir / "_runs"
    runs.mkdir(exist_ok=True)
    (runs / f"{key}.run.json").write_text(json.dumps(record, indent=2, sort_keys=True),
                                          encoding="utf-8")


def _project(tmp_path: Path, *, with_corpus: bool = False, attested: bool = True) -> Path:
    (tmp_path / "ledger.config.md").write_text(
        "project_name: statecase\nprovenance: required\n", encoding="utf-8")
    claims = tmp_path / "literature" / "verified_claims"
    claims.mkdir(parents=True)
    source_rel = "literature/x_2020.html"
    source_hash = sha256_text(SOURCE_HTML)
    if with_corpus:
        (tmp_path / source_rel).write_text(SOURCE_HTML, encoding="utf-8")
    if attested:
        _stamp(claims, "x_2020", source_rel, source_hash)
    else:
        (claims / "x_2020.md").write_text(
            "\n".join(["---", 'paper: "x (2020)"', "---", "", "## Claim 1: c", "",
                       '> "the quoted sentence"', "", "**ID:** c", ""]),
            encoding="utf-8")
    content = tmp_path / "content"
    (content / "assessments" / "_records").mkdir(parents=True)
    (content / "inquiry.md").write_text("# Inquiry\n", encoding="utf-8")
    return tmp_path


# ---- the three states ------------------------------------------------------

def test_corpus_absent_with_stamps_reads_attested_not_guaranteed(tmp_path):
    state = jd.verification_state(_project(tmp_path), artefact="pack")
    assert state["level"] == "attested"
    assert state["quote_badge"] == "Attested"
    assert state["attested"] == 1 and state["sources_at_build"] == 0
    assert "cannot re-prove quotations against source bytes" in state["ceiling"]
    assert "Guaranteed" not in state["ceiling"]


def test_corpus_present_at_build_is_recorded_but_still_not_reproducible(tmp_path):
    state = jd.verification_state(_project(tmp_path, with_corpus=True), artefact="pack")
    assert state["sources_at_build"] == 1 and not state["drifted"]
    assert state["build_note"]
    # Bytes on the BUILDER's disk are not bytes in the READER's hands.
    assert state["level"] == "attested"
    assert state["quote_badge"] == "Attested"


def test_neither_corpus_nor_attestation_reads_unverified(tmp_path):
    state = jd.verification_state(_project(tmp_path, attested=False), artefact="pack")
    assert state["level"] == "unverified"
    assert state["quote_badge"] == "Unverified"
    assert state["unattested"] == ["x_2020"]
    assert "unverified" in state["ceiling"]


def test_a_source_that_drifted_from_its_stamp_is_not_attested(tmp_path):
    root = _project(tmp_path, with_corpus=True)
    (root / "literature" / "x_2020.html").write_text("<html>tampered</html>",
                                                     encoding="utf-8")
    state = jd.verification_state(root, artefact="pack")
    assert state["level"] == "unverified"
    assert state["drifted"] == ["x_2020"]
    assert not state["build_note"]


def test_a_quote_edited_after_stamping_is_caught_without_the_corpus(tmp_path):
    # The trust table sells this as enforced in the reader's hands, so it must hold with
    # no source bytes anywhere: the body hash travels inside the ledger.
    root = _project(tmp_path)
    ledger = root / "literature" / "verified_claims" / "x_2020.md"
    ledger.write_text(ledger.read_text(encoding="utf-8").replace(
        "the quoted sentence", "a sentence nobody ever verified"), encoding="utf-8")
    state = jd.verification_state(root)
    assert state["level"] == "unverified"
    assert state["unattested"] == ["x_2020"]


def test_a_run_record_edited_after_sealing_is_not_attested(tmp_path):
    root = _project(tmp_path)
    record = root / "literature" / "verified_claims" / "_runs" / "x_2020.run.json"
    data = json.loads(record.read_text(encoding="utf-8"))
    data["source_sha256"] = "0" * 64
    record.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    state = jd.verification_state(root)
    assert state["level"] == "unverified"
    assert state["unattested"] == ["x_2020"]


def test_a_project_with_no_ledgers_claims_nothing(tmp_path):
    (tmp_path / "ledger.config.md").write_text("project_name: empty\n", encoding="utf-8")
    state = jd.verification_state(tmp_path)
    assert state["level"] == "empty" and state["ledgers"] == 0
    assert "nothing to verify" in state["ceiling"]


def _bundle_with_corpus(root: Path, bundle: Path) -> Path:
    """An export that really does carry the bytes, at the path the ledger records."""
    shipped = bundle / "literature" / "x_2020.html"
    shipped.parent.mkdir(parents=True, exist_ok=True)
    shipped.write_text(SOURCE_HTML, encoding="utf-8")
    return bundle


def test_a_corpus_on_the_builders_disk_never_licenses_guaranteed(tmp_path):
    # The confusion the whole axis exists to stop: the builder holding the corpus says
    # nothing about what the reader holds. Only bytes in the artefact count.
    root = _project(tmp_path, with_corpus=True)
    empty_bundle = tmp_path / "bundle"
    empty_bundle.mkdir()
    state = jd.verification_state(root, bundle_dir=empty_bundle)
    assert state["sources_at_build"] == 1 and state["build_note"]
    assert state["corpus_included"] is False
    assert state["quote_badge"] == "Attested"


def test_only_bytes_inside_the_artefact_read_guaranteed(tmp_path):
    root = _project(tmp_path, with_corpus=True)
    bundle = _bundle_with_corpus(root, tmp_path / "bundle")
    state = jd.verification_state(root, bundle_dir=bundle)
    assert state["corpus_included"] is True
    assert state["quote_badge"] == "Guaranteed"
    assert state["level"] == "reproducible"


def test_a_shipped_source_that_fails_its_hash_is_not_included(tmp_path):
    # Shipping *a* file is not shipping *the* source: inclusion is proved by hash, so a
    # wrong or tampered copy cannot buy the badge.
    root = _project(tmp_path, with_corpus=True)
    bundle = _bundle_with_corpus(root, tmp_path / "bundle")
    (bundle / "literature" / "x_2020.html").write_text("<html>not it</html>",
                                                       encoding="utf-8")
    state = jd.verification_state(root, bundle_dir=bundle)
    assert state["corpus_included"] is False
    assert state["quote_badge"] == "Attested"


def test_a_bundle_missing_one_source_is_not_included(tmp_path):
    root = _project(tmp_path, with_corpus=True)
    _stamp(root / "literature" / "verified_claims", "y_2021",
           "literature/y_2021.html", sha256_text(SOURCE_HTML))
    (root / "literature" / "y_2021.html").write_text(SOURCE_HTML, encoding="utf-8")
    bundle = _bundle_with_corpus(root, tmp_path / "bundle")  # ships x_2020 only
    assert jd.verification_state(root, bundle_dir=bundle)["corpus_included"] is False


# ---- what the built page actually says -------------------------------------

def _index(tmp_path: Path, **kwargs) -> str:
    root = _project(tmp_path, **kwargs)
    bjp.build_pack(root, tmp_path / "pack")
    return (tmp_path / "pack" / "index.html").read_text(encoding="utf-8")


def test_the_pack_states_the_ceiling_exactly_once(tmp_path):
    assert _index(tmp_path).count("cannot re-prove quotations against source bytes") == 1


def test_the_pack_never_says_guaranteed_beside_the_quote_row(tmp_path):
    index = _index(tmp_path)
    assert '<span class="badge neu">Attested</span>' in index
    assert "badge ok\">Guaranteed" not in index


def test_the_ingestion_chip_follows_the_state(tmp_path):
    # The green "guaranteed" chip sat on the ingestion gate regardless of whether the
    # reader could repeat it — the same overclaim as the table, in a picture.
    assert 'class="ig-chip">attested' in _index(tmp_path)


def test_a_pack_built_where_the_corpus_lives_still_reads_attested(tmp_path):
    # Guards the CALLER, not just the model: the bundle ships no sources even when the
    # builder holds every one, so handing the project in as the bundle would render a
    # guarantee for a reader who has nothing to check it with.
    index = _index(tmp_path, with_corpus=True)
    assert '<span class="badge neu">Attested</span>' in index
    assert 'badge ok">Guaranteed' not in index
    assert "cannot re-prove quotations against source bytes" in index


def test_the_pack_never_claims_a_reproof_it_did_not_run(tmp_path):
    # Bytes present at build say the hashes still bind; they do not say this build
    # re-ran the quote scan, and the page must not imply it did.
    index = _index(tmp_path, with_corpus=True)
    assert "Source bytes were on disk when this was generated" in index
    assert "re-proved against source bytes when this pack was generated" not in index.lower()


def test_an_unverified_project_says_so_on_the_first_screen(tmp_path):
    index = _index(tmp_path, attested=False)
    assert 'class="badge bad">Unverified</span>' in index
    assert "carry no valid verification record" in index


def test_pack_and_dashboard_state_the_same_ceiling(tmp_path):
    # One model, two artefacts: the wording may name a different noun, but the two
    # cannot disagree about what the reader may trust.
    root = _project(tmp_path)
    pack = jd.verification_state(root, artefact="pack")
    page = jd.verification_state(root, artefact="page")
    assert pack["level"] == page["level"]
    assert pack["quote_badge"] == page["quote_badge"]
    assert pack["ceiling"].replace("pack", "X") == page["ceiling"].replace("page", "X")


def test_the_dashboard_renders_the_ceiling(tmp_path):
    html = jd.render_html(_project(tmp_path))
    assert html.count("cannot re-prove quotations against source bytes") == 1
    assert 'class="ceiling"' in html


def test_every_shipped_case_is_attested_and_says_so(tmp_path):
    # The real artefacts a judge opens: raw sources are git-ignored, so every case must
    # land on 'attested' and none may read as a guarantee.
    cases = sorted(p for p in (REPO_ROOT / "cases").iterdir() if p.is_dir())
    assert cases, "no vendored cases found"
    for case in cases:
        state = jd.verification_state(case, artefact="pack")
        assert state["level"] == "attested", f"{case.name}: {state['unattested']}"
        assert state["quote_badge"] == "Attested", case.name
