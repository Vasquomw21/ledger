# Dependencies — Ledger

Every dependency, with its **purpose**, by tier. Deps are tiered so the **demo** needs none.
pip is primary (`pip install -r requirements.txt`); conda (`environment.yml`) is the optional route
to the binary intake/publish deps. Update this file on any dependency change.

## By tier

| Tier | Dependency | Purpose |
|---|---|---|
| **Demo** | `python3` ≥3.10 | Runs the read-only demo + gates — pure stdlib, **zero installs**. (The `.githooks/pre-commit` invokes system `python3`, maybe 3.9; scripts carry `from __future__ import annotations` so `X \| None` works.) |
| **Test** (pip `test`) | `pytest>=9,<10` | Runs `tests/` — the enforcement-layer suite; also in CI. |
| **Intake** (pip `intake`) | `beautifulsoup4>=4.15,<5` (`bs4`) | `build_register.py` / `extract_text.py` — HTML parsing. Pinned: extraction output must stay stable or quote checks flip. |
| **Intake** | `lxml>=6.1,<7` | `extract_text.py` — bs4's HTML backend. |
| **Intake** | `pypdf>=6.13,<7` | `extract_text.py` — PDF text extraction. |
| **Intake** (binaries, conda) | `jq`, `curl` | `fetch_paper.sh` — JSON parsing + the download ladder. |
| **Publish** (binaries, conda) | `nodejs`, `gh` | Quartz static-site publishing; GitHub CLI for repo create/push. |

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
