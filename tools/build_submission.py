#!/usr/bin/env python3
"""Assemble the offline evaluator bundle from the five vendored cases.

Reuses build_judge_pack.build_pack and judge_dashboard.verification_state and
adds the index page, manifests, checksums and the staging -> verify -> publish
sequence. It never deletes: publication is an os.rename into an ABSENT
destination on the same filesystem as the staging tree, and a build that fails a
verification gate leaves its staging tree in place for inspection rather than
removing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_judge_pack
import corpus_manifest
import judge_dashboard
import ledger_cli
import ledger_doctor
import md_render

# Bundle order is showcase-first; the rest follow the guide's ordering.
SHOWCASE = "covid_origins"
CASES = ("covid_origins", "eggs_cholesterol", "lhc_safety", "quantum_genomics",
         "covid_debate")

CASE_META = {
    "covid_origins": ("COVID-origins",
        "A belief presented as a result — one disputed support, two supporters "
        "marked as potentially correlated. Recommended starting point."),
    "eggs_cholesterol": ("Eggs and cholesterol",
        "Sixteen studies reduce to a handful of reused patient cohorts; three "
        "possible-dependence warnings fire, on both sides of the question."),
    "lhc_safety": ("LHC safety",
        "The safety argument traced from its headline claim down to the exact "
        "sentence and reply it rests on."),
    "quantum_genomics": ("Quantum computing for genomics",
        "A subject outside the author's field, where the claimed speed-up turns "
        "on a single contested result."),
    "covid_debate": ("COVID debate",
        "A recorded public debate with no authored finding — an empty "
        "interpretation layer, with the missing transcript declared as a gap."),
}

GUIDE = "EVALUATOR_GUIDE.md"
GUIDE_HTML = "EVALUATOR_GUIDE.html"
MANIFEST = "release-manifest.json"
CHECKSUMS = "checksums.sha256"

# A remote URL in one of these resource-load positions means the page cannot
# render offline. A remote <a href> is navigation, not a loaded asset, and is
# allowed; prose/source URLs in .md/.json are never scanned.
_REMOTE_ASSET_RE = re.compile(
    r"""(?ix)
    (?: <script\b[^>]*\bsrc\s*=\s*["']\s*(?:https?:)?// )
    | (?: <link\b[^>]*\bhref\s*=\s*["']\s*(?:https?:)?// )
    | (?: \burl\(\s*["']?\s*(?:https?:)?// )
    | (?: @import\s+["']\s*(?:https?:)?// )
    | (?: \bfetch\(\s*["']\s*(?:https?:)?// )
    """)

_ATTR_URL_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
_MD_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
_MD_LINK_PARTS_RE = re.compile(r'\[([^\]]*)\]\(([^)\s]+)\)')
_SCHEME_RE = re.compile(r'^[a-z][a-z0-9+.-]*:', re.I)


class SubmissionError(Exception):
    pass


class DestinationExists(SubmissionError):
    pass


class UnpublishableRef(SubmissionError):
    """A --from-ref that cannot honestly back a published bundle."""


class GateFailure(SubmissionError):
    def __init__(self, problems, staging=None):
        self.problems = list(problems)
        self.staging = staging
        super().__init__("; ".join(self.problems))


def _case_root(repo_root: Path, name: str) -> Path:
    return repo_root / "cases" / f"{name}_ledger"


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo_root),
                          capture_output=True, text=True)


def _git_commit(repo_root: Path) -> str:
    """The commit the bundle claims, suffixed `-dirty` when the tree carries
    uncommitted work.

    The builder reads a working TREE while the manifest names a COMMIT, so on an
    unclean tree a bare sha would assert provenance for content that never
    shipped. The suffix keeps the claim honest without blocking a local build;
    --from-ref removes the gap entirely by building from an export.
    """
    out = _git(repo_root, "rev-parse", "HEAD")
    if out.returncode != 0:
        return "unknown"
    commit = out.stdout.strip()
    status = _git(repo_root, "status", "--porcelain")
    dirty = status.returncode == 0 and status.stdout.strip()
    return f"{commit}-dirty" if dirty else commit


def _resolve_publishable_ref(repo_root: Path, ref: str) -> str:
    """The commit `ref` names, once it is established a reader could fetch it.

    A published bundle stamps a commit the reader is invited to check, so a ref
    that exists only in this clone would name an unreachable object. Reachability
    is read from the remote-tracking refs, which is as far as a local check can
    honestly go: it proves the commit was pushed at last fetch, not that the
    remote still carries it.
    """
    out = _git(repo_root, "rev-parse", f"{ref}^{{commit}}")
    if out.returncode != 0:
        raise UnpublishableRef(f"unknown ref: {ref}")
    commit = out.stdout.strip()
    remotes = _git(repo_root, "branch", "-r", "--contains", commit)
    if remotes.returncode != 0 or not remotes.stdout.strip():
        raise UnpublishableRef(
            f"{ref} ({commit[:12]}) is on no remote-tracking branch — a reader "
            f"could not fetch the commit the bundle would claim; push it first")
    return commit


def _export_ref(repo_root: Path, ref: str, dest: Path) -> None:
    """Extract `ref` into `dest` via git archive.

    The working tree is never read, so uncommitted or stashed work cannot reach a
    published bundle — the same reason build_pristine.sh exports rather than
    clones.
    """
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "archive", "--format=tar", ref],
                             cwd=str(repo_root), capture_output=True)
    if archive.returncode != 0:
        raise UnpublishableRef(
            f"could not export {ref}: {archive.stderr.decode(errors='ignore').strip()}")
    unpack = subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout,
                            capture_output=True)
    if unpack.returncode != 0:
        raise UnpublishableRef(
            f"could not unpack the export of {ref}: "
            f"{unpack.stderr.decode(errors='ignore').strip()}")


def _stage_packs(repo_root: Path, staging: Path) -> dict:
    """Build each case's pack under packs/<name>; return {name: ceiling level}."""
    levels = {}
    for name in CASES:
        case = _case_root(repo_root, name)
        out = staging / "packs" / name
        build_judge_pack.build_pack(case, out)
        state = judge_dashboard.verification_state(case, bundle_dir=out,
                                                   artefact="pack")
        levels[name] = state["level"]
    return levels


def _is_external(url: str) -> bool:
    u = url.split("#", 1)[0].split("?", 1)[0]
    return (not u) or u.startswith("//") or bool(_SCHEME_RE.match(u))


def _stage_guide(repo_root: Path, staging: Path) -> None:
    """Copy the guide, rewriting only navigation references: case-directory links
    become bundle pack pages, and any relative link with no target in the bundle
    is unlinked to plain text. Prose words are never altered."""
    text = (repo_root / GUIDE).read_text(encoding="utf-8")
    for name in CASES:
        text = text.replace(f"](cases/{name}_ledger/)",
                            f"](packs/{name}/index.html)")

    def _keep_or_unlink(m):
        label, target = m.group(1), m.group(2)
        if _is_external(target):
            return m.group(0)
        rel = target.split("#", 1)[0].split("?", 1)[0]
        return m.group(0) if (staging / rel).exists() else label

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _keep_or_unlink, text)
    (staging / GUIDE).write_text(text, encoding="utf-8")
    # No browser renders Markdown, so a link straight at the .md shows a reader
    # its source. The rendered page is built from the SAME rewritten text, so the
    # two carry identical links and the unlinking above applies to both.
    html = md_render.render_markdown(text, frontmatter="drop")
    (staging / GUIDE_HTML).write_text(
        _GUIDE_TEMPLATE.format(body=_link_bundle_targets(html, staging)),
        encoding="utf-8")


def _link_bundle_targets(html: str, staging: Path) -> str:
    """Anchor the relative links md_render leaves as literal `[label](target)`.

    md_render linkifies absolute URLs only, so a pack page can never grow a
    dangling cross-link. The bundle is the one place that knows which relative
    targets it contains, so it resolves them here — and only when the file is
    present, which keeps the internal-link gate satisfied by construction.
    """
    def _anchor(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        rel = target.split("#", 1)[0].split("?", 1)[0]
        if _is_external(target) or not (staging / rel).exists():
            return label
        return f'<a href="{target}">{label}</a>'

    return _MD_LINK_PARTS_RE.sub(_anchor, html)


_GUIDE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ledger — evaluator guide</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.65 system-ui, -apple-system, sans-serif;
         max-width: 46rem; margin: 3rem auto; padding: 0 1.2rem; }}
  h1 {{ font-size: 1.6rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 2.4rem; }}
  h3 {{ font-size: 1.05rem; }}
  pre {{ overflow-x: auto; padding: 0.8rem; border-radius: 4px; background: #f4f4f4; }}
  table {{ border-collapse: collapse; display: block; overflow-x: auto; }}
  th, td {{ border: 1px solid #ccc; padding: 0.35rem 0.6rem; text-align: left; }}
  blockquote {{ margin: 1rem 0; padding: 0 0 0 1rem; border-left: 3px solid #ccc;
                color: #555; }}
  a.back {{ display: inline-block; margin-bottom: 1.5rem; }}
  @media (prefers-color-scheme: dark) {{
    pre {{ background: #222; }}
    th, td {{ border-color: #444; }}
    blockquote {{ border-color: #444; color: #aaa; }} }}
</style>
</head>
<body>
<p><a class="back" href="index.html">&larr; Bundle index</a></p>
{body}
</body>
</html>
"""


_INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ledger — evaluator bundle</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, -apple-system, sans-serif;
         max-width: 46rem; margin: 3rem auto; padding: 0 1.2rem; }}
  h1 {{ font-size: 1.6rem; }}
  p.lead {{ color: #555; }}
  ul.cases {{ list-style: none; padding: 0; }}
  ul.cases li {{ margin: 0 0 1rem; }}
  ul.cases a {{ font-weight: 600; font-size: 1.05rem; }}
  ul.cases span {{ display: block; color: #555; font-size: 0.95rem; }}
  a.guide {{ display: inline-block; margin-top: 1rem; font-weight: 600; }}
  @media (prefers-color-scheme: dark) {{
    p.lead, ul.cases span {{ color: #aaa; }} }}
</style>
</head>
<body>
<h1>Ledger — evaluator bundle</h1>
<p class="lead">Ledger is a research toolkit for people and AI working together: every citation
in gated, authored prose points to a quotation checked against the original source. Start with the
recommended case, then read the guide.</p>
<ul class="cases">
{cards}
</ul>
<p><a class="guide" href="EVALUATOR_GUIDE.html">Read the evaluator guide &rarr;</a></p>
</body>
</html>
"""


def _stage_index(staging: Path) -> None:
    cards = []
    for name in CASES:
        title, blurb = CASE_META[name]
        star = " ★" if name == SHOWCASE else ""
        cards.append(f'  <li><a href="packs/{name}/index.html">{title}{star}</a>'
                     f'<span>{blurb}</span></li>')
    (staging / "index.html").write_text(
        _INDEX_TEMPLATE.format(cards="\n".join(cards)), encoding="utf-8")


def _stage_corpus(repo_root: Path, staging: Path) -> None:
    """The bundle ships no source bytes; the manifest travels fully triaged so a
    later corpus-carrying build fills the same table without a schema change."""
    corpus = staging / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "README.txt").write_text(
        "No source bytes ship in this bundle. Quotations are attested from the "
        "committed verification records; re-proof requires acquiring the "
        "sources. corpus-manifest.tsv triages each source's redistribution "
        "status; release-manifest.json records corpus.included = false.\n",
        encoding="utf-8")
    (staging / "corpus-manifest.tsv").write_text(
        corpus_manifest.render_tsv(corpus_manifest.build_rows(repo_root)),
        encoding="utf-8")


def _profiles(repo_root: Path) -> dict:
    out = {}
    for name in CASES:
        root = _case_root(repo_root, name)
        cfg = ledger_cli._parse_config(root)
        out[name] = {
            "project_state": ledger_doctor.declared_state(cfg) or "pristine",
            "strict": ledger_cli._is_strict(cfg, root),
            "postures": {k: ledger_cli.effective_posture(cfg, k)
                         for k in sorted(ledger_cli.POSTURE_DEFAULTS)},
        }
    return out


def _internal_link_problems(bundle: Path) -> list:
    """Relative href/src in bundle HTML, and relative markdown links in the
    guide, must resolve to a file in the bundle."""
    problems = []

    def _check(path, url):
        if _is_external(url):
            return
        rel = url.split("#", 1)[0].split("?", 1)[0]
        if not (path.parent / rel).exists():
            problems.append(f"{path.relative_to(bundle)} -> {url}")

    for html in bundle.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="ignore")
        for m in _ATTR_URL_RE.finditer(text):
            _check(html, m.group(1))
    guide = bundle / GUIDE
    if guide.exists():
        for m in _MD_LINK_RE.finditer(guide.read_text(encoding="utf-8")):
            _check(guide, m.group(1))
    return problems


def _remote_asset_problems(bundle: Path) -> list:
    return [f"{h.relative_to(bundle)} loads a remote asset"
            for h in bundle.rglob("*.html")
            if _REMOTE_ASSET_RE.search(h.read_text(encoding="utf-8", errors="ignore"))]


def _ceiling_problems(levels: dict) -> list:
    return [f"pack '{n}' claims '{lvl}' without shipped corpus"
            for n, lvl in levels.items() if lvl == "reproducible"]


def _bundle_files(bundle: Path) -> list:
    return sorted(p.relative_to(bundle).as_posix()
                  for p in bundle.rglob("*") if p.is_file())


def _write_manifest(staging: Path, commit: str, levels: dict,
                    profiles: dict) -> None:
    files = [f for f in _bundle_files(staging) if f not in (MANIFEST, CHECKSUMS)]
    doc = {
        "schema": "ledger-submission/v0",
        "source_commit": commit,
        "recommended_showcase": SHOWCASE,
        "corpus": {"included": False,
                   "note": "no source bytes ship; quotations are attested, "
                           "not re-proved"},
        "packs": [{"case": n, "verification_level": levels[n], **profiles[n]}
                  for n in CASES],
        "files": files,
    }
    (staging / MANIFEST).write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_checksums(staging: Path) -> None:
    rels = [f for f in _bundle_files(staging) if f != CHECKSUMS]
    (staging / CHECKSUMS).write_text(
        "".join(f"{_sha256(staging / rel)}  {rel}\n" for rel in rels),
        encoding="utf-8")


def _verify_checksums(bundle: Path) -> list:
    problems = []
    for line in (bundle / CHECKSUMS).read_text(encoding="utf-8").splitlines():
        expect, sep, rel = line.partition("  ")
        if not sep:
            continue
        if _sha256(bundle / rel) != expect:
            problems.append(f"{rel}: checksum mismatch")
    return problems


def build_submission(repo_root, dest, from_ref: str | None = None) -> dict:
    repo_root = Path(repo_root).resolve()
    dest = Path(dest).resolve()
    if dest.exists():
        raise DestinationExists(
            f"destination exists: {dest} — remove it yourself; this tool never "
            f"overwrites or clears a destination")
    dest.parent.mkdir(parents=True, exist_ok=True)

    export: tempfile.TemporaryDirectory | None = None
    if from_ref is not None:
        commit = _resolve_publishable_ref(repo_root, from_ref)
        export = tempfile.TemporaryDirectory(prefix="ledger-export-")
        _export_ref(repo_root, from_ref, Path(export.name))
        source_root = Path(export.name)
    else:
        commit = _git_commit(repo_root)
        source_root = repo_root

    try:
        return _build(source_root, dest, commit)
    finally:
        if export is not None:
            export.cleanup()


def _build(repo_root: Path, dest: Path, commit: str) -> dict:
    staging = Path(tempfile.mkdtemp(dir=str(dest.parent),
                                    prefix=f".{dest.name}.staging-"))

    levels = _stage_packs(repo_root, staging)
    _stage_guide(repo_root, staging)
    _stage_index(staging)
    _stage_corpus(repo_root, staging)

    problems = (_ceiling_problems(levels)
                + _remote_asset_problems(staging)
                + _internal_link_problems(staging))
    if problems:
        raise GateFailure(problems, staging=staging)

    _write_manifest(staging, commit, levels, _profiles(repo_root))
    _write_checksums(staging)

    os.rename(str(staging), str(dest))
    corrupt = _verify_checksums(dest)
    if corrupt:
        raise GateFailure(corrupt)
    return {"dest": dest, "commit": commit, "levels": levels,
            "files": len(_bundle_files(dest))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Assemble the offline evaluator bundle.")
    ap.add_argument("repo_root", nargs="?", default=str(REPO))
    ap.add_argument("--out", required=True, help="destination bundle directory "
                    "(must not already exist)")
    ap.add_argument("--from-ref", default=None, metavar="REF",
                    help="build from an export of REF (a tag or branch) instead "
                         "of the working tree — required for a bundle you "
                         "publish, since it is what stops uncommitted work "
                         "reaching it")
    args = ap.parse_args(argv)
    try:
        summary = build_submission(args.repo_root, args.out, args.from_ref)
    except DestinationExists as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    except UnpublishableRef as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    except GateFailure as e:
        print("[ERROR] verification failed before publish; destination not "
              "created.", file=sys.stderr)
        for p in e.problems:
            print(f"  - {p}", file=sys.stderr)
        if e.staging:
            print(f"[INFO] staging left for inspection: {e.staging}",
                  file=sys.stderr)
        return 1
    print(f"[INFO] bundle published: {summary['dest']}")
    source = args.from_ref or "working tree"
    # Abbreviate the sha, never the `-dirty` marker: it is the one part of the
    # line a reader must not lose.
    sha, _, mark = summary["commit"].partition("-")
    shown = f"{sha[:12]}-{mark}" if mark else sha[:12]
    print(f"[INFO] {summary['files']} files, commit {shown} (from {source})")
    if summary["commit"].endswith("-dirty"):
        print("[WARNING] built from a tree with uncommitted changes — the "
              "manifest records this and the bundle must not be published; "
              "rebuild with --from-ref", file=sys.stderr)
    print(f"[INFO] ceilings: {summary['levels']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
