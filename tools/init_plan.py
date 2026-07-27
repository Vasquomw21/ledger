# === SCRIPT: init_plan — pure construction + validation for `ledger init` ===
# Builds the config and skin a project WOULD have, plus every reason to refuse, without
# touching the disk: text in, text out. Nothing here writes, so a setup that fails
# validation cannot leave a half-configured project behind.
# INPUTS : the current ledger.config.md and skin text, the answers, the subject rules.
# OUTPUTS: an InitPlan — config updates, diffs, dirs to ensure, notes, problems, blockers.
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from string import ascii_uppercase

import config_edit
from check_citations import gated_prefixes
from ledger_doctor import (REQUIRED, SKIN_EMPTY_MARKER, is_placeholder,
                           skin_text_is_empty)

# The config template declares these two and nothing reads the value, so an unrecognised
# one is a typo nobody would ever be told about.
SOURCE_OF_TRUTH_CHOICES = ("markdown+quartz", "docx+python")

DEFAULT_SKIN_FILE = "content/_ledger/skin_rules.md"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

RULE_LINE_RE = re.compile(r"^\s*-\s*\*\*(?P<code>[A-Za-z]+\d*)\*\*\s*(?P<body>.+)$")

# The kit ships one worked example from another project immediately above the sentinel. It
# reads as illustration while the skin is a draft, but nothing marks it as someone else's
# once the skin is confirmed — so materialising a real skin takes the whole block out.
WORKED_EXAMPLE_RE = re.compile(r"^\s*Worked example\b", re.IGNORECASE)

# Substitutes for a rule that carry no rule. Matched against the whole answer, so a real
# rule that happens to contain "none" is untouched.
FILLER = frozenset({"tbd", "t.b.d.", "todo", "to do", "n/a", "na", "none", "nil",
                    "xxx", "...", "-", "?"})


@dataclass(frozen=True)
class Field:
    """One question init asks. The prompt lives here so every caller asks it the same
    way."""
    key: str
    prompt: str
    required: bool = True


FIELDS = (
    Field("project_name", "Project name (a short slug, e.g. water_policy_ke)"),
    Field("deliverable", "Deliverable (thesis chapter | policy white paper | report | ...)"),
    Field("source_of_truth", f"Source of truth ({' | '.join(SOURCE_OF_TRUTH_CHOICES)})"),
    Field("the_reader",
          'The bored reader (e.g. "a busy minister AND a sceptical scientist")'),
    Field("source_types",
          "Source types (peer-reviewed papers | legislation & gov reports | books | mixed)"),
    # The prompt carries no "(optional)" marker: `required` already says so, and each
    # caller words it for its own surface.
    Field("unpaywall_email", "Email for the Unpaywall download rung", required=False),
)


def _values(config_text: str) -> dict[str, str]:
    """The config as its readers see it: last duplicate wins, as parse_config does."""
    return {line.key: line.value for line in config_edit.scan(config_text)}


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def _example_block_end(lines: list[str], start: int) -> int:
    """One past the last rule line of the worked-example block opening at `start`. Blank
    lines between its rules are stepped over; trailing ones are not consumed, so whatever
    separates the block from the next section survives."""
    end = index = start + 1
    while index < len(lines):
        if RULE_LINE_RE.match(lines[index]):
            index += 1
            end = index
        elif not lines[index].strip():
            index += 1
        else:
            break
    return end


def strip_worked_example(text: str) -> str:
    """The skin without the kit's worked-example block.

    Only ever applied to a skin the kernel calls empty, so the block removed is the one
    the kit ships: a skin carrying rules of its own is never re-rendered."""
    lines = text.split("\n")
    out: list[str] = []
    index = 0
    while index < len(lines):
        if WORKED_EXAMPLE_RE.match(lines[index]):
            end = _example_block_end(lines, index)
            # The block sat between blank lines; keeping both leaves a double gap.
            if out and not out[-1].strip() and end < len(lines) \
                    and not lines[end].strip():
                end += 1
            index = end
            continue
        out.append(lines[index])
        index += 1
    return "\n".join(out)


def rule_code(project_name: str, skin_text: str = "") -> str:
    """The letter this subject's rule codes carry (**L1**, **E1**): the first letter of
    its name, as the worked cases do.

    A letter used by a rule the skin RETAINS is passed over, so a reference to a code
    names one rule. The kit's worked example does not reserve anything — it is removed
    when the skin is materialised, leaving a water_policy subject free to use W."""
    taken = {match.group("code")[0].upper()
             for match in map(RULE_LINE_RE.match,
                              strip_worked_example(skin_text).split("\n")) if match}
    for char in list(project_name) + list(ascii_uppercase):
        if char.isalpha() and char.upper() not in taken:
            return char.upper()
    return "S"


def example_rules(skin_text: str) -> set[str]:
    """The rule bodies already in the skin, normalised. The kit ships one worked example
    from another project, which is the only rules prose to hand and so the likeliest
    thing to be pasted back in as this subject's rules."""
    return {_normalise(match.group("body"))
            for match in map(RULE_LINE_RE.match, skin_text.split("\n")) if match}


def answer_problems(answers: dict[str, str]) -> list[str]:
    """Every reason these answers cannot configure a project, or []."""
    found = []
    for field in FIELDS:
        raw = answers.get(field.key, "")
        if field.required and is_placeholder(raw):
            found.append(f"{field.key} is required, and is unset or still a "
                         f"<placeholder>.")
    unknown = sorted(set(answers) - {field.key for field in FIELDS})
    for key in unknown:
        found.append(f"'{key}' is not a field init sets.")

    source_of_truth = answers.get("source_of_truth", "").strip()
    if source_of_truth and not is_placeholder(source_of_truth) \
            and source_of_truth not in SOURCE_OF_TRUTH_CHOICES:
        found.append(f"source_of_truth must be one of "
                     f"{' | '.join(SOURCE_OF_TRUTH_CHOICES)}; got "
                     f"{source_of_truth!r}.")

    email = answers.get("unpaywall_email", "").strip()
    if email and not is_placeholder(email) and not EMAIL_RE.match(email):
        found.append(f"unpaywall_email does not look like an address: {email!r}. Leave "
                     f"it out to skip the Unpaywall rung.")
    return found


def rule_problems(rules: list[str], skin_text: str) -> list[str]:
    """Every reason a proposed rule is a substitute for a rule rather than one.

    HONEST LIMIT: this catches the obvious substitutes — blank, a TBD token, the shipped
    example pasted back in. A fluent sentence that says nothing passes. That judgement is
    what skin_state carries: the rules stay a draft until their author says otherwise."""
    found = []
    shipped = example_rules(skin_text)
    for rule in rules:
        text = _normalise(rule)
        if not text:
            found.append("a rule is blank.")
        elif text in FILLER or rule.strip().startswith("<"):
            found.append(f"{rule.strip()!r} is a placeholder, not a rule. Give a real "
                         f"one, or give none and leave the skin a draft.")
        elif text in shipped:
            found.append(f"{rule.strip()!r} is the worked example the kit ships, not a "
                         f"rule for this subject.")
    return found


def config_updates(answers: dict[str, str], *,
                   mark_skin_draft: bool = True) -> dict[str, str]:
    """The config keys init sets: the answered fields, and the skin's state when init is
    the one drafting it.

    `mark_skin_draft` False leaves skin_state untouched. The skin already holds rules init
    is not rewriting, and whether their author stands behind them is not init's to say —
    stamping 'draft' over a skin someone owns makes a configured project read as broken,
    since a project cannot be configured on rules nobody has stood behind.

    project_state is never among them. It is the author's declaration that the project is
    genuinely finished; stamping it here would make ledger_doctor read a half-built
    project as `broken`, whose gates run LENIENT while the config claims strictness."""
    updates = {field.key: answers[field.key].strip()
               for field in FIELDS
               if answers.get(field.key, "").strip()
               and not is_placeholder(answers[field.key])}
    if mark_skin_draft:
        updates["skin_state"] = "draft"
    return updates


def render_skin(skin_text: str, subject: str, rules: list[str], code: str) -> str:
    """The skin with this subject's rules in place of the sentinel, and the kit's worked
    example gone.

    The shared explanatory preamble is preserved byte-for-byte. The example is not: a
    confirmed skin offers nothing to tell another project's rules from this one's, so
    leaving them behind would hand the writing skill five rules nobody here chose."""
    block = [f"Subject rules — {subject}:"]
    block += [f"- **{code}{n}** {rule.strip()}" for n, rule in enumerate(rules, 1)]

    out: list[str] = []
    replaced = False
    for raw in strip_worked_example(skin_text).split("\n"):
        if not replaced and SKIN_EMPTY_MARKER in raw:
            out.extend(block)
            replaced = True
            continue
        out.append(raw)
    if not replaced:
        # No sentinel to stand in for: append rather than guess an insertion point, so
        # nothing already in the file moves.
        trailing = [out.pop()] if out and out[-1] == "" else []
        if out and out[-1].strip():
            out.append("")
        out.extend(block)
        out.extend(trailing)
    return "\n".join(out)


def declared_skin_file(config_text: str) -> str:
    """The skin this config declares, or the kernel default when it says nothing usable.

    The ONLY source of the write target. Taking it as an argument instead would let a
    caller name a file the config never declared and path_problems never saw."""
    raw = _values(config_text).get("skin_rules_file", "").strip()
    return DEFAULT_SKIN_FILE if not raw or is_placeholder(raw) else raw


def _escape_reason(path_str: str) -> str | None:
    """Why this declared path is not one init may act on inside the project, or None."""
    text = path_str.strip()
    if not text:
        return "is empty"
    if text.startswith("~"):
        return "starts with '~', which expands outside the project"
    path = PurePosixPath(text)
    if path.is_absolute():
        return "is absolute"
    if ".." in path.parts:
        return "climbs out of the project with '..'"
    return None


def path_problems(config_text: str) -> list[str]:
    """Every declared path init must refuse to act on.

    LEXICAL ONLY. It sees an absolute path, a '..' segment and an unusable one. It cannot
    see a symlinked parent, because that needs the filesystem — so the writer must ALSO
    resolve each existing parent and refuse any whose real location leaves the project
    root. Passing here is not evidence that a path stays inside."""
    config = _values(config_text)
    found = []
    for prefix in gated_prefixes(config):
        reason = _escape_reason(prefix)
        if reason:
            found.append(f"gated_paths entry {prefix.strip()!r} {reason}. init will not "
                         f"create or gate a path outside the project.")
    skin = config.get("skin_rules_file", "").strip()
    if skin and not is_placeholder(skin):
        reason = _escape_reason(skin)
        if reason:
            found.append(f"skin_rules_file {skin!r} {reason}. init will not write "
                         f"outside the project.")
    return found


def dirs_to_ensure(config_text: str) -> list[str]:
    """The directories this config declares. Git does not track an empty directory, so a
    gated path can be declared correctly and still be missing from a clone — which
    ledger_doctor reports as broken.

    Only the entries written as directories: a gated_paths entry may name a single file,
    and nothing here can tell which. An escaping path is dropped as well as reported, so
    a caller that ignores path_problems still cannot be handed one."""
    dirs = [prefix for prefix in gated_prefixes(_values(config_text))
            if prefix.endswith("/") and not _escape_reason(prefix)]
    skin = declared_skin_file(config_text)
    if not _escape_reason(skin):
        parent = str(PurePosixPath(skin).parent)
        if parent not in ("", "."):
            dirs.append(parent + "/")
    return sorted(set(dirs))


def blockers(config_text: str, skin_text: str, reconfigure: bool) -> list[str]:
    """Why this project must not be initialised as it stands.

    --reconfigure is consent to re-answer a config that is already filled. It never
    extends to the skin: those rules are the author's, and init cannot tell its own
    earlier output from prose someone wrote, so it only ever writes rules into a skin
    that has none."""
    found = []
    config = _values(config_text)
    filled = [key for key in REQUIRED if not is_placeholder(config.get(key, ""))]
    if filled and not reconfigure:
        found.append(f"this project is already configured ({', '.join(filled)} "
                     f"{'is' if len(filled) == 1 else 'are'} set). Re-run with "
                     f"--reconfigure to answer again.")
    if not skin_text_is_empty(skin_text) and not reconfigure:
        found.append("the skin already holds rules. Re-run with --reconfigure to "
                     "re-answer the config; the rules are left alone either way.")
    return found


@dataclass(frozen=True)
class InitPlan:
    """What init would do, computed from bytes it has read but does not hold.

    Both targets are bound to their bytes: `config_sha256`, and `skin_sha256` (None when
    the skin did not exist, which is not the same as an empty one). The writer compares
    both through staleness() before touching either. `skin_text` None means the skin is
    not being written."""
    config_updates: dict
    config_text: str
    config_diff: str
    config_sha256: str
    skin_file: str
    skin_text: str | None
    skin_diff: str
    skin_sha256: str | None
    dirs: list
    notes: list
    problems: list
    blockers: list

    @property
    def ok(self) -> bool:
        return not self.problems and not self.blockers

    @property
    def skin_existed(self) -> bool:
        return self.skin_sha256 is not None

    @property
    def changes(self) -> list:
        return config_edit.plan(self.config_text, self.config_updates)


def skin_staleness(plan: InitPlan, skin_text: str | None) -> list[str]:
    """Whether the skin has moved since `plan` was computed, or [].

    Separate from staleness() because the writer must ALSO re-check the skin after the
    config is written — by which point the config digest has deliberately changed, so the
    combined check could not be reused. An edit arriving in that window would otherwise
    be overwritten by bytes computed from what the skin used to hold."""
    now = config_edit.digest(skin_text) if skin_text is not None else None
    if now == plan.skin_sha256:
        return []
    if plan.skin_sha256 is None:
        return [f"{plan.skin_file} did not exist when the preview was taken and does "
                f"now. Re-run: nothing in it has been shown to you."]
    if now is None:
        return [f"{plan.skin_file} existed when the preview was taken and is gone now. "
                f"Re-run."]
    return [f"{plan.skin_file} changed after the preview was taken. Re-run: the rules "
            f"you approved are not the ones on disk."]


def staleness(plan: InitPlan, config_text: str, skin_text: str | None) -> list[str]:
    """Every way the targets have moved since `plan` was computed, or [].

    Both are checked before EITHER is written. init changes two files, so a plan stale in
    one is stale entirely: writing the config against a skin that moved would configure
    the project from bytes nobody approved, and writing rules over a skin that appeared
    since the preview would destroy prose that was never shown."""
    found = []
    if config_edit.digest(config_text) != plan.config_sha256:
        found.append("ledger.config.md changed after the preview was taken, so the diff "
                     "you approved is out of date. Re-run to see the current change.")
    return found + skin_staleness(plan, skin_text)


def build(config_text: str, skin_text: str | None, answers: dict[str, str],
          rules: list[str] | None = None, *, reconfigure: bool = False) -> InitPlan:
    """The whole proposed setup, and every reason to refuse it.

    `skin_text` None means the skin file does not exist, which an empty string does not:
    only None lets the writer refuse a skin that appeared after the preview. The write
    target is NOT a parameter — it derives from config_text, so it cannot name a file
    path_problems never validated. Callers locate the skin with declared_skin_file()."""
    rules = list(rules or [])
    skin_file = declared_skin_file(config_text)
    current = skin_text if skin_text is not None else ""
    blank_skin = skin_text_is_empty(current)
    problems = (answer_problems(answers) + rule_problems(rules, current)
                + path_problems(config_text))
    updates = config_updates(answers, mark_skin_draft=blank_skin)
    problems += config_edit.problems(config_text, updates)

    notes: list[str] = []
    new_skin = None
    if not blank_skin:
        notes.append(f"{skin_file} already holds rules — left untouched.")
        if rules:
            problems.append(f"rules were given, but {skin_file} already holds rules and "
                            f"init will not rewrite them. Edit the file yourself.")
    elif rules:
        name = answers.get("project_name", "")
        new_skin = render_skin(current, name or "this subject", rules,
                               rule_code(name, current))
    else:
        notes.append(f"no rules given — {skin_file} stays a draft. Write them there, "
                     f"then set skin_state: confirmed.")

    proposed = config_edit.render(config_text, updates) if not problems else config_text
    return InitPlan(
        config_updates=updates,
        config_text=config_text,
        config_diff=config_edit.diff(config_text, proposed),
        config_sha256=config_edit.digest(config_text),
        skin_file=skin_file,
        skin_text=new_skin,
        skin_diff=config_edit.diff(current, new_skin, skin_file) if new_skin else "",
        skin_sha256=(config_edit.digest(skin_text) if skin_text is not None else None),
        dirs=dirs_to_ensure(config_text),
        notes=notes,
        problems=problems,
        blockers=blockers(config_text, current, reconfigure),
    )
