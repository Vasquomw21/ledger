"""The evaluator-bundle builder: staging -> verify -> publish, no-delete rails."""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_submission as bs  # noqa: E402


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    dest = tmp_path_factory.mktemp("out") / "ledger-submission"
    summary = bs.build_submission(REPO, dest)
    return dest, summary


def test_all_packs_and_files_present(bundle):
    dest, _ = bundle
    for name in bs.CASES:
        assert (dest / "packs" / name / "index.html").exists(), name
    for rel in (bs.GUIDE, "index.html", bs.MANIFEST, bs.CHECKSUMS,
                "corpus-manifest.tsv", "corpus/README.txt"):
        assert (dest / rel).exists(), rel


def test_corpus_manifest_populated_and_nothing_included(bundle):
    dest, _ = bundle
    lines = (dest / "corpus-manifest.tsv").read_text().splitlines()
    assert len(lines) > 1  # header + source rows, not the old header-only stub
    idx = lines[0].split("\t").index("included_in_submission")
    assert all(row.split("\t")[idx] == "no" for row in lines[1:])  # honest empty corpus


def test_refuses_existing_destination(bundle):
    dest, _ = bundle
    before = sorted(p.name for p in dest.iterdir())
    with pytest.raises(bs.DestinationExists):
        bs.build_submission(REPO, dest)
    # the refused run touches nothing
    assert sorted(p.name for p in dest.iterdir()) == before


def test_internal_links_resolve(bundle):
    dest, _ = bundle
    assert bs._internal_link_problems(dest) == []


def test_no_remote_assets(bundle):
    dest, _ = bundle
    assert bs._remote_asset_problems(dest) == []


def test_ceiling_is_attested_not_reproducible(bundle):
    _, summary = bundle
    assert "reproducible" not in summary["levels"].values()
    assert set(summary["levels"].values()) <= {"attested", "unverified", "empty"}


def test_checksums_exclude_self_and_match(bundle):
    dest, _ = bundle
    lines = (dest / bs.CHECKSUMS).read_text().splitlines()
    listed = {ln.split("  ", 1)[1] for ln in lines if "  " in ln}
    assert bs.CHECKSUMS not in listed          # never checksums itself
    assert bs.MANIFEST in listed               # but does cover the manifest
    assert bs._verify_checksums(dest) == []    # every listed hash matches


def test_manifest_has_no_wallclock_or_staging_paths(bundle):
    dest, _ = bundle
    doc = json.loads((dest / bs.MANIFEST).read_text())
    assert doc["source_commit"]
    assert doc["recommended_showcase"] == bs.SHOWCASE
    assert bs.CHECKSUMS not in doc["files"] and bs.MANIFEST not in doc["files"]
    blob = json.dumps(doc)
    assert ".staging-" not in blob
    assert "/private/" not in blob and str(dest) not in blob


def test_deterministic_manifest_and_checksums(bundle, tmp_path):
    dest, _ = bundle
    dest2 = tmp_path / "ledger-submission"
    bs.build_submission(REPO, dest2)
    assert (dest2 / bs.MANIFEST).read_text() == (dest / bs.MANIFEST).read_text()
    assert (dest2 / bs.CHECKSUMS).read_text() == (dest / bs.CHECKSUMS).read_text()


def test_guide_nav_rewritten_prose_intact(bundle):
    dest, _ = bundle
    guide = (dest / bs.GUIDE).read_text()
    assert "](packs/covid_origins/index.html)" in guide   # case link -> pack page
    assert "](cases/" not in guide                         # no repo-only case links


def test_index_links_to_a_rendered_guide(bundle):
    """A link straight at the .md shows a reader Markdown source: no browser
    renders it, and GitHub Pages serves it as text."""
    dest, _ = bundle
    index = (dest / "index.html").read_text()
    assert f'href="{bs.GUIDE_HTML}"' in index
    assert f'href="{bs.GUIDE}"' not in index


def test_rendered_guide_is_html_and_carries_the_guides_links(bundle):
    dest, _ = bundle
    html = (dest / bs.GUIDE_HTML).read_text()
    assert html.startswith("<!doctype html>")
    assert "<h1>" in html and "# Ledger" not in html      # rendered, not escaped source
    assert 'href="packs/covid_origins/index.html"' in html
    assert 'href="index.html"' in html                    # a way back to the bundle
    # a sentence of prose survives rendering verbatim
    assert "the claimed speed-up turns on a single contested result" in html


def _tiny_repo(tmp_path, run):
    """A throwaway git repo, so the source-provenance tests never depend on the
    state of the repo they are running inside."""
    repo = tmp_path / "src"
    (repo / "tools").mkdir(parents=True)
    (repo / "a.txt").write_text("one\n")
    run("git", "init", "-q", "-b", "main", cwd=repo)
    run("git", "config", "user.email", "t@example.invalid", cwd=repo)
    run("git", "config", "user.name", "T", cwd=repo)
    run("git", "add", "-A", cwd=repo)
    run("git", "commit", "-q", "-m", "one", cwd=repo)
    return repo


@pytest.fixture
def run():
    import subprocess

    def _run(*args, cwd):
        out = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        return out.stdout.strip()
    return _run


def test_dirty_tree_never_claims_a_bare_commit(tmp_path, run):
    """The builder reads a TREE but the manifest names a COMMIT: on an unclean
    tree a bare sha would assert provenance for content that never shipped."""
    repo = _tiny_repo(tmp_path, run)
    assert "-dirty" not in bs._git_commit(repo)

    (repo / "a.txt").write_text("edited, uncommitted\n")
    dirty = bs._git_commit(repo)
    assert dirty.endswith("-dirty")
    assert dirty[:-len("-dirty")] == run("git", "rev-parse", "HEAD", cwd=repo)


def test_from_ref_refuses_a_commit_no_reader_could_fetch(tmp_path, run):
    """A published bundle stamps a commit the reader is invited to check."""
    repo = _tiny_repo(tmp_path, run)
    with pytest.raises(bs.UnpublishableRef) as e:
        bs._resolve_publishable_ref(repo, "main")
    assert "remote-tracking" in str(e.value)

    with pytest.raises(bs.UnpublishableRef):
        bs._resolve_publishable_ref(repo, "no-such-ref")


def test_export_ignores_the_working_tree(tmp_path, run):
    """The point of --from-ref: uncommitted work cannot reach the bundle."""
    repo = _tiny_repo(tmp_path, run)
    (repo / "a.txt").write_text("edited, uncommitted\n")
    (repo / "untracked.txt").write_text("never committed\n")

    out = tmp_path / "export"
    bs._export_ref(repo, "main", out)
    assert (out / "a.txt").read_text() == "one\n"      # the commit, not the edit
    assert not (out / "untracked.txt").exists()


def test_audit_pack_and_untracked_work_untouched(bundle):
    dest, _ = bundle
    assert not any(p.name == "audit_pack.py" for p in dest.rglob("*"))
    assert not (dest / "tools").exists()
    # audit_pack.py is untracked local work: when the working tree carries it, the
    # build must still exclude it from the bundle. A committed fresh clone has no
    # such file, so this worktree-protection check applies only when it is present.
    untracked_tool = REPO / "tools" / "audit_pack.py"
    if untracked_tool.exists():
        assert not (dest / "tools" / "audit_pack.py").exists()
