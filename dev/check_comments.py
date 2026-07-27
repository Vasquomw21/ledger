#!/usr/bin/env python3
# === SCRIPT: check_comments — comments carry contracts, not plans ===
# Flags a comment or docstring that names a plan item. Such a line is false as soon as the
# plan moves and is not the reader's to act on, whereas a constraint stays true and changes
# what they do.
# Only comments and docstrings are read — never code, string literals or identifiers — so an
# identifier, a fixture, or a quoted source is not a finding.
# INPUTS : paths (.py/.sh; directories are walked), or --stdin for one fragment.
# OUTPUTS: one line per finding on stdout; exit 1 if any, 0 if none, 2 if a path is unusable.
#
# HONEST LIMIT: this detects a NAMED CATEGORY, not padding. It cannot tell whether a comment
# merely restates well-named code. Structure carries what a checker cannot: express the
# invariant in names, types and tests, and the comment becomes unnecessary.
from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

# Every pattern is checked against the whole tracked tree before it is added (see
# tests/test_comment_discipline.py): a watchlist that cries wolf gets switched off, which
# costs more than the tic it caught.
PATTERNS = (
    (re.compile(r"\bM\d+\.\d+\b"), "names a plan item"),
    (re.compile(r"\bC\d[a-z]\b"), "names a plan item"),
    (re.compile(r"--- C\d"), "a plan section label"),
    (re.compile(r"\bPhase \d"), "names a plan phase"),
    (re.compile(r"\broadmap\b", re.I), "points at the plan"),
    (re.compile(r"\bmilestone\b", re.I), "points at the plan"),
    (re.compile(r"(point|boundary|spec) of C\d"), "argues a plan item's scope"),
    (re.compile(r"arrives in C\d"), "sequences future work"),
    (re.compile(r"\bC\d (adds|rewrites|promotes|moves|boundary)"), "sequences future work"),
    (re.compile(r"(will|must|would) (then )?(de-|re-)?vendor"), "sequences future work"),
    (re.compile(r"\bstep \d+ (of|adds|does)\b", re.I), "sequences a plan step"),
    (re.compile(r"\((Issue|issue) \d"), "an internal tracker ref"),
    (re.compile(r"[A-Za-z]+-pass review"), "a development review pass"),
    (re.compile(r"\bFLF\b"), "names the evaluation"),
    (re.compile(r"mock[ -]?judge", re.I), "names the evaluation"),
)


# A watchlist and its fixtures necessarily contain the tokens they define, so a checker
# that policed them could never be edited. Skipped here rather than by each caller, so
# pre-commit, pytest and the write-time hook cannot disagree about the scope.
SELF_REFERENTIAL = ("dev/check_comments.py",
                    "tests/test_comment_discipline.py",
                    ".claude/hooks/check-self-narration.sh")


def exempt(path) -> bool:
    text = str(path).replace("\\", "/")
    return any(text == name or text.endswith("/" + name) for name in SELF_REFERENTIAL)


def _hit(text: str):
    for pattern, why in PATTERNS:
        if pattern.search(text):
            return why
    return None


def python_prose(text: str):
    """Every comment and docstring, as (line, text). Raises on unparseable input."""
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            yield token.start[0], token.string
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                yield node.body[0].lineno, doc


def hash_prose(text: str):
    """Comment LINES only — the whole story for shell, and the fallback elsewhere. A `#`
    inside a string cannot be told from a comment without parsing."""
    for number, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            yield number, stripped


def prose(text: str, *, python: bool):
    if not python:
        return list(hash_prose(text))
    try:
        return list(python_prose(text))
    except (SyntaxError, tokenize.TokenError, IndentationError):
        # An editor's replacement text is a fragment, not a whole module. Reading its `#`
        # lines still beats scanning raw text, which is what keeps an identifier safe.
        return list(hash_prose(text))


def findings(text: str, *, python: bool, where: str = "-"):
    found = []
    for line, chunk in prose(text, python=python):
        why = _hit(chunk)
        if why:
            first = chunk.strip().split("\n")[0]
            found.append(f"{where}:{line}: {why} — {first[:72]}")
    return found


def _paths(given):
    for raw in given:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*")
                              if p.suffix in (".py", ".sh") and p.is_file())
        else:
            yield path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Comments carry contracts, not plans.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--stdin", action="store_true",
                        help="read one fragment from stdin")
    parser.add_argument("--python", action="store_true",
                        help="with --stdin: treat the fragment as Python")
    args = parser.parse_args(argv)

    if args.stdin:
        found = findings(sys.stdin.read(), python=args.python)
    else:
        found = []
        for path in _paths(args.paths):
            if exempt(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as error:
                print(f"[check_comments] cannot read {path}: {error}", file=sys.stderr)
                return 2
            found += findings(text, python=path.suffix == ".py", where=str(path))

    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} comment(s) name a plan instead of a contract. State the "
              f"constraint that stays true, or delete it: if removing a comment does not "
              f"make the code harder to use safely, it was not carrying one.",
              file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
