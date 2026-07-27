# === SCRIPT: config_edit — byte-preserving mutation primitives for ledger.config.md ===
# scan/plan/render/diff are pure: text in, text out, no file touched. apply() is the only
# writer, and validates first — so a rejected change never reaches the disk and there is
# no partial write to roll back.
# INPUTS : ledger.config.md text + the {key: value} updates proposed.
# OUTPUTS: pure scan/plan/render/diff results; apply() performs one atomic replace.
from __future__ import annotations

import difflib
import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

# `<indent><key>:<padding><value>`. Comment lines must be excluded before this runs: the
# file's own commentary contains colons ("# ... (claim_ids: required, ...)"), so a
# colon-first scan invents keys out of prose. parse_config skips `#` lines first too.
KEY_LINE_RE = re.compile(r"^(?P<pre>[ \t]*(?P<key>[A-Za-z_][A-Za-z0-9_]*)[ \t]*:[ \t]*)"
                         r"(?P<rest>.*)$")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# ledger.config.md aligns values at column 21; a longer key (semantic_max_age_days:) gets
# one space instead, which is what the file already does.
VALUE_COLUMN = 21


@dataclass(frozen=True)
class Line:
    """One parsed config line. `pre + value + post` reconstructs the raw line exactly, so
    replacing `value` alone cannot disturb indentation, padding or a trailing comment."""
    key: str
    pre: str
    value: str
    post: str


def _parse_line(line: str) -> Line | None:
    """The parsed key line, or None for a comment / blank / non-key line."""
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    match = KEY_LINE_RE.match(line)
    if not match:
        return None
    rest = match.group("rest")
    # `#` starts an inline comment — the convention every posture reader applies
    # (value.split("#", 1)[0]). Everything from it on is preserved verbatim.
    cut = rest.find("#")
    value = (rest if cut == -1 else rest[:cut]).rstrip()
    return Line(match.group("key"), match.group("pre"), value, rest[len(value):])


def scan(text: str) -> list[Line]:
    """Every key line in the file, in order, duplicates included."""
    return [line for line in map(_parse_line, text.split("\n")) if line]


def malformed_lines(text: str) -> list[tuple[int, str]]:
    """(line number, raw) for every non-blank, non-comment line that is not a
    declaration. `claim_ids required` — a dropped colon — is the case that matters: every
    reader skips it, so the posture silently falls to its kernel default while the line
    still reads as a declaration to a human.

    Indented declarations ARE valid: parse_config strips before partitioning, so
    `  claim_ids: required` is read by every gate and is not reported here."""
    return [(i, raw) for i, raw in enumerate(text.split("\n"), 1)
            if raw.strip() and not raw.lstrip().startswith("#")
            and _parse_line(raw) is None]


def digest(text: str) -> str:
    """The identity a preview is bound to."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def duplicate_keys(text: str) -> list[str]:
    """Keys declared more than once. parse_config keeps the LAST occurrence, so editing
    the first is a silent no-op — the file means something other than it appears to."""
    seen: dict[str, int] = {}
    for line in scan(text):
        seen[line.key] = seen.get(line.key, 0) + 1
    return sorted(key for key, count in seen.items() if count > 1)


@dataclass(frozen=True)
class Change:
    """One proposed edit. `old is None` means the key is absent and would be appended."""
    key: str
    old: str | None
    new: str

    @property
    def adds(self) -> bool:
        return self.old is None


def plan(text: str, updates: dict[str, str]) -> list[Change]:
    """The changes `updates` would make; keys already at their value are omitted, so a
    re-run is a no-op rather than a rewrite."""
    current = {line.key: line.value for line in scan(text)}
    return [Change(key, current.get(key), value)
            for key, value in updates.items()
            if current.get(key) != value]


def problems(text: str, updates: dict[str, str]) -> list[str]:
    """Every reason this write must be refused, or []."""
    found = []
    for key in duplicate_keys(text):
        # Refused even for keys not being written: the file is already ambiguous.
        found.append(f"'{key}' is declared more than once — the file is ambiguous "
                     f"(readers keep the last). Reconcile it by hand first.")
    for number, raw in malformed_lines(text):
        found.append(f"line {number} is neither a comment nor a `key: value` "
                     f"declaration, so every reader skips it: {raw.strip()!r}")
    for key, value in sorted(updates.items()):
        if not KEY_RE.match(key):
            found.append(f"'{key}' is not a valid config key.")
        if "\n" in value or "\r" in value:
            found.append(f"value for '{key}' spans lines; a config value is one line.")
        if "#" in value:
            found.append(f"value for '{key}' contains '#', which every reader treats as "
                         f"the start of a comment — it would silently truncate.")
        if not value.strip():
            found.append(f"value for '{key}' is empty.")
        elif value != value.strip():
            found.append(f"value for '{key}' has leading or trailing whitespace.")
    return found


def render(text: str, updates: dict[str, str]) -> str:
    """The file with `updates` applied — byte-identical outside the changed values.
    split("\\n"), not splitlines(): it round-trips a missing trailing newline."""
    lines = text.split("\n")
    written: set[str] = set()
    out = []
    for raw in lines:
        parsed = _parse_line(raw)
        if parsed and parsed.key in updates:
            written.add(parsed.key)
            new = updates[parsed.key]
            if parsed.value != new:
                raw = parsed.pre + new + parsed.post
        out.append(raw)

    missing = [key for key in updates if key not in written]
    if missing:
        # Appended at the end: guessing an insertion point next to the relevant comment
        # block would rewrite lines the caller never asked to touch.
        trailing = [out.pop()] if out and out[-1] == "" else []
        out.extend(f"{(key + ':').ljust(VALUE_COLUMN - 1)} {updates[key]}"
                   for key in missing)
        out.extend(trailing)
    return "\n".join(out)


def diff(before: str, after: str, path: str = "ledger.config.md") -> str:
    """A unified diff for preview. Empty when nothing would change."""
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}", n=1))


def temp_path(path: Path) -> Path:
    """The sibling the atomic write stages through."""
    return path.with_name(f".{path.name}.ledger-new")


def write_atomically(path: Path, text: str) -> None:
    """One atomic swap: write a sibling temp, fsync, os.replace. A crash mid-write leaves
    the original intact. The temp is a SIBLING so the replace stays on one filesystem —
    os.replace is atomic only within a filesystem and raises EXDEV across one.

    O_EXCL, because the temp path is predictable: without it, anything already sitting
    there is opened and truncated, and a SYMLINK there is followed — so an unrelated file
    would be filled with this config and then consumed by the replace. O_EXCL|O_CREAT
    refuses a symlink outright, dangling or not. Raises FileExistsError if the path is
    occupied; the caller reports that rather than clearing it.

    The temp is created 0600 and then given the original's mode: a fresh file would
    otherwise take the umask, silently WIDENING a config the user had restricted, and
    creating it permissively first would expose the contents for the write's duration."""
    mode = stat.S_IMODE(path.stat().st_mode)
    tmp = temp_path(path)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def apply(path: Path, updates: dict[str, str],
          expect_sha256: str) -> tuple[list[Change], list[str]]:
    """Validate, then write iff there is something to write and nothing to refuse.
    Returns (changes, problems); either being empty means nothing was written.

    `expect_sha256` is the digest of the bytes the caller previewed and the user
    consented to, and is required rather than optional so it cannot be forgotten: a file
    edited between preview and confirmation is refused, because otherwise the write would
    land on bytes nobody approved. Re-validating alone would only keep the OUTPUT
    well-formed, not make it the change that was shown."""
    text = path.read_text(encoding="utf-8")
    if digest(text) != expect_sha256:
        return [], [f"{path.name} changed after the preview was taken, so the diff you "
                    f"approved is out of date. Re-run to see the current change."]
    found = problems(text, updates)
    if found:
        return [], found
    changes = plan(text, updates)
    if not changes:
        return [], []
    try:
        write_atomically(path, render(text, updates))
    except FileExistsError:
        # Left in place deliberately, not cleared: it may be a leftover from an
        # interrupted run, or a file that has nothing to do with Ledger. Deciding it is
        # disposable is the user's call, not this tool's.
        return [], [f"the staging path {temp_path(path).name} is already occupied, so "
                    f"the write was refused and {path.name} is unchanged. Inspect it — "
                    f"it may be a leftover from an interrupted run — and move or remove "
                    f"it yourself, then re-run."]
    return changes, []
