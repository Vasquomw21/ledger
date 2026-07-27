# Dependencies — Ledger

Every dependency of the Ledger starter kit, with its **purpose** (not just name/version).
The toolchain is pinned in `environment.yml` (conda-forge only) — recreate with
`conda env create -f environment.yml && conda activate ledger_env`. Update this file whenever
a dependency is added, removed, upgraded, or found to be optional/platform-specific.

## Runtime — conda env `ledger_env` (conda-forge)

| Dependency | Purpose |
|---|---|
| `python=3.12` | Runs the intake pipeline (`build_register.py`, `extract_text.py`, `verify_quotes.py` incl. `--stamp` provenance binding), `tools/lint_wiki.py`, `tools/check_citations.py`, `tools/check_manifest.py`, and `tools/ledger_doctor.py`. NB: the `.githooks/pre-commit` gate invokes the system `python3` (may be 3.9) — the scripts carry `from __future__ import annotations` so 3.10+ syntax (`X | None`) works there. |
| `nodejs` | Quartz static-site publishing of `content/`. |
| `gh` | GitHub CLI — repo create / push for the shareable layer. |
| `jq` | `fetch_paper.sh` — JSON parsing of Unpaywall / OpenAlex responses. |
| `curl` | `fetch_paper.sh` — the download ladder (PMC / DOI / Unpaywall / OpenAlex / web). |
| `beautifulsoup4=4.15` (import `bs4`) | `build_register.py` / `extract_text.py` — HTML parsing. Minor-pinned: extraction output must stay stable or quote checks flip on a fresh clone. |
| `lxml=6.1` | `extract_text.py` — HTML parser backend for bs4. Minor-pinned (see above). |
| `pypdf=6.13` | `extract_text.py` — PDF text extraction. Minor-pinned (see above). |
| `pytest=9.0` | Runs `tests/` — the enforcement-layer suite (`verify_quotes.py` + `check_citations.py`), also run in CI. |
| `pip` | Fallback installer inside the env. |

## System-level

| Dependency | Purpose |
|---|---|
| `git` (≥ 2.49) | Version control; the sole sync for the shareable layer; backs `fetch_paper.sh` gist/repo clones. |
| `conda` (miniconda + conda-forge) | Environment manager; pins the whole toolchain reproducibly. |
| `bash` | Runs `check.sh`, `fetch_paper.sh`, and the `.claude/hooks/` guards. |

## Claude Code harness (not conda-managed)

| Dependency | Purpose |
|---|---|
| Claude Code | Hosts the skills and runs the PreToolUse guard (`.claude/hooks/verify-citations.sh`). |
| Global skills in `~/.claude/skills/` | `skill-ledger-write`, `-bootstrap`, `-curate` — the writing/setup/curate assistants; installed once, not shipped per repo. |

## Optional / platform-specific

| Dependency | Purpose |
|---|---|
| Obsidian | Browse `content/` and the vault-backed design docs (SPEC / BOOTSTRAP / HISTORY) with backlinks; desktop is the source of truth. |
| Unpaywall email | `fetch_paper.sh` API identity (set in `ledger.config.md`); only needed for the Unpaywall rung. |
