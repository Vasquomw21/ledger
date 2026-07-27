# === SCRIPT: init_apply — the writer for `ledger init` ===
# Every mutation is a REPLACE of a file that already exists, so every one of them is
# undone by writing retained bytes back. Nothing is created: not a directory, not a file.
# A creation can only be undone by deleting, and this kit never deletes — so a plan that
# would need one is refused before anything is written, not rolled back afterwards.
# INPUTS : a project root + an InitPlan built from that project's current bytes.
# OUTPUTS: (applied, problems). A failure restores what init wrote; a file edited by
#          someone else meanwhile is left as they left it.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import config_edit
import init_plan
import ledger_doctor
from check_citations import gated_prefixes, parse_config

CONFIG_FILE = "ledger.config.md"


def _read(path: Path) -> str | None:
    """The file's text, or None if it is not there."""
    return path.read_text(encoding="utf-8") if path.is_file() else None


def escapes_root(root: Path, declared: str) -> bool:
    """Whether this declared path's REAL location leaves the project.

    init_plan.path_problems is lexical and cannot see a symlinked parent, which would put
    both the staging temp and the replace outside the project. Only the nearest EXISTING
    ancestor is resolved: parts that do not exist cannot redirect a write."""
    root_real = root.resolve()
    probe = (root / declared)
    while not (probe.exists() or probe.is_symlink()):
        if probe == probe.parent:
            return True
        probe = probe.parent
    real = probe.resolve()
    return real != root_real and root_real not in real.parents


def containment_problems(root: Path, config_text: str) -> list[str]:
    """Declared paths whose real location is outside the project."""
    found = []
    values = {line.key: line.value for line in config_edit.scan(config_text)}
    for prefix in gated_prefixes(values):
        if escapes_root(root, prefix):
            found.append(f"gated_paths entry {prefix.strip()!r} resolves outside the "
                         f"project — a parent of it is a link elsewhere.")
    skin = init_plan.declared_skin_file(config_text)
    if escapes_root(root, skin):
        found.append(f"skin_rules_file {skin!r} resolves outside the project — a parent "
                     f"of it is a link elsewhere.")
    return found


@dataclass(frozen=True)
class Target:
    """One file init replaces: what it held (`before`) and what init put there
    (`written`, None if init never wrote it).

    `written` is what makes rollback safe. Content matching neither arrived after init
    wrote, and reverting it would destroy an edit init never saw. `name` is
    project-relative: a recovery instruction must name the file to go and look at, not
    its basename."""
    name: str
    path: Path
    before: str
    written: str | None = None


def _symlink_problem(name: str, path: Path) -> str | None:
    """Whether this target is a symlink, which init must not write through.

    An atomic replace swaps the directory ENTRY: the link would become a regular file and
    be lost, rather than its target being updated. That holds even when the link resolves
    inside the project, so escapes_root does not cover it."""
    if not path.is_symlink():
        return None
    return (f"{name} is a symlink. init replaces a file in place, which would swap the "
            f"link itself for a regular file and lose it — point the config at the real "
            f"file, or replace the link with one, and re-run.")


def preflight(root: Path, plan: init_plan.InitPlan) -> list[str]:
    """Every reason to refuse, checked before a single byte is written.

    init only ever REPLACES the starter kit's own scaffold. A missing file or directory
    is a refusal rather than a creation request: creating one is irreversible here, so a
    later failure could not be rolled back and the project would keep something no
    verification approved."""
    found = list(plan.problems) + list(plan.blockers)

    config_path = root / CONFIG_FILE
    if not config_path.is_file():
        found.append(f"{CONFIG_FILE} is not in {root} — init configures an existing "
                     f"starter-kit clone, it does not create one.")
        return found

    config_text = _read(config_path) or ""
    found += containment_problems(root, config_text)
    found += [p for p in (_symlink_problem(CONFIG_FILE, config_path),) if p]

    skin_name = init_plan.declared_skin_file(config_text)
    skin_path = root / skin_name
    if skin_path.is_symlink():
        found.append(_symlink_problem(skin_name, skin_path))
    elif not skin_path.is_file():
        found.append(f"{skin_name} is not there. init replaces the kit's skin, it does "
                     f"not create one — restore the file from the starter kit first.")

    for declared in plan.dirs:
        if not (root / declared).is_dir():
            found.append(f"{declared} is not there. init writes into the kit's existing "
                         f"directories and creates none, because a directory it made "
                         f"could not be removed again if a later step failed.")
    return found


def _restore(targets: list[Target]) -> list[str]:
    """Put back only what init itself wrote, and report what could not be put back.

    A write, never a delete — and never over somebody else's work: a file holding neither
    its original nor what init wrote was changed after init wrote it, so reverting it
    would destroy an edit that was never init's to touch."""
    failed = []
    for target in targets:
        current = _read(target.path)
        if current == target.before:
            continue
        if current != target.written:
            failed.append(f"{target.name} no longer holds what init wrote, so something "
                          f"else changed it — it was left exactly as it is. The original "
                          f"is in git: `git restore -p {target.name}`.")
            continue
        try:
            config_edit.write_atomically(target.path, target.before)
        except OSError as error:
            failed.append(f"{target.name} could NOT be put back ({error}). The original "
                          f"is in git: `git restore -p {target.name}`.")
    return failed


def _rolled_back(problems: list[str], targets: list[Target]) -> list[str]:
    """Restore, THEN report what the restore actually did — composing the message first
    would claim a rollback that may not have happened."""
    failed = _restore(targets)
    if failed:
        return problems + ["", "Rollback INCOMPLETE:"] + [f"  {f}" for f in failed]
    return problems + ["", "Put back as it was: "
                       + ", ".join(target.name for target in targets) + "."]


def _verify(root: Path) -> list[str]:
    """The COMPLETE ledger_doctor contract over the written project, not just its derived
    state: a configured project is strict by definition, so diagnose() alone would accept
    a lax posture bundle that the real doctor — and every gate — rejects."""
    config = parse_config(root / CONFIG_FILE)
    problems = ledger_doctor.blocking_problems(config, root)
    if not problems:
        return []
    state, _ = ledger_doctor.diagnose(config, root)
    return [f"ledger_doctor rejects the project init would leave behind — it reads as "
            f"'{state}':"] + [f"  {p}" for p in problems]


def apply_plan(root: Path, plan: init_plan.InitPlan) -> tuple[bool, list[str]]:
    """Write the plan, or leave the project exactly as it was.

    Order is forced by the rule that nothing is ever deleted: the config is replaced
    first and the skin second, and if either the skin write or the verification fails,
    both are restored from the bytes retained here."""
    found = preflight(root, plan)
    if found:
        return False, found

    config_path = root / CONFIG_FILE
    skin_path = root / plan.skin_file
    config_text = _read(config_path)
    skin_text = _read(skin_path)

    stale = init_plan.staleness(plan, config_text, skin_text)
    if stale:
        return False, stale

    _, problems = config_edit.apply(config_path, plan.config_updates, plan.config_sha256)
    if problems:
        # Nothing was written: config_edit validates before it opens anything.
        return False, problems

    config_target = Target(CONFIG_FILE, config_path, config_text,
                           config_edit.render(config_text, plan.config_updates))
    skin_target = Target(plan.skin_file, skin_path, skin_text)

    if plan.skin_text is not None:
        moved = init_plan.skin_staleness(plan, _read(skin_path))
        if moved:
            # Re-read: the skin was last checked before the config write. Only the config
            # is restored — an edit that landed in that window is not ours to revert.
            return False, _rolled_back(moved, [config_target])
        try:
            config_edit.write_atomically(skin_path, plan.skin_text)
        except OSError as error:
            return False, _rolled_back(
                [f"{plan.skin_file} could not be written ({error})."],
                [config_target, skin_target])
        skin_target = Target(plan.skin_file, skin_path, skin_text, plan.skin_text)

    verified = _verify(root)
    if verified:
        return False, _rolled_back(verified, [config_target, skin_target])
    return True, []
