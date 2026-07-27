# === SCRIPT: faithfulness_eval — measure a detector's out-of-context hit-rate ===
# Layer 1 (Fidelity) splits in two. "Is the quote verbatim?" is GUARANTEED by
# verify_quotes. "Is the verbatim quote used IN CONTEXT, or stretched to support an
# inference it does not warrant?" is the harder half — currently Assisted, never
# measured (faithfulness_probe lists edges; a human/agent files disputes).
#
# This puts a NUMBER on that second half, the way repro.py put one on determinism.
# It is a MEASUREMENT TOOL, NOT A GATE — no posture, no pre-commit/CI hook. It runs a
# detector (the agent/human layer; the kit ships no model) over a small, hand-labelled
# benchmark of real (verbatim quote -> inference) pairs and reports its confusion
# matrix + recall/specificity/precision/accuracy.
#
#   --emit-blind   prints {id, source, slug, quote, inference} WITHOUT the gold label
#                  or rationale — the detector's input (it must not see the answer).
#   --score V.jsonl  joins detector verdicts {id, verdict} with gold and scores them.
#   --claims-dir D   re-proves each embedded quote verbatim against ledger D/<key>.md
#                    (norm-substring, the same normalisation as the verbatim gate).
#
# HONEST BOUNDARY: this measures A
# DETECTOR on a SMALL hand-labelled benchmark — not a kit guarantee, not a property
# that transfers beyond these cases. The gold labels are AUTHOR JUDGEMENT, each
# quote-pinned with a rationale so a sceptic contests a specific label, not the method.
# The benchmark is class-balanced so recall AND specificity are both meaningful (an
# always-"out-of-context" detector scores 100% recall, 0% specificity). The positive
# class is "out-of-context" — the misuse we want to catch.
#
# INPUTS : spec/examples/faithfulness_bench.jsonl (the labelled benchmark);
#          a verdicts JSONL for --score; optionally a verified_claims dir for re-proof.
# OUTPUTS: [INFO] lines or --json; exit 0 ok, 2 on bad input / missing verdicts.
# Run    : python3 tools/faithfulness_eval.py --emit-blind
#          python3 tools/faithfulness_eval.py --score verdicts.jsonl [--json]
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import norm   # the verbatim gate's normalisation, reused verbatim

BENCH = REPO_ROOT / "spec" / "examples" / "faithfulness_bench.jsonl"

# The positive class is the failure we want to catch.
POSITIVE = "out-of-context"
NEGATIVE = "apt"

# Detectors phrase the verdict loosely; map the common synonyms onto the two labels.
_OOC_WORDS = {"out-of-context", "out of context", "ooc", "misuse", "misused",
              "unfaithful", "stretch", "overreach", "no", "fail"}
_APT_WORDS = {"apt", "faithful", "in-context", "in context", "ok", "fine",
              "warranted", "yes", "pass"}


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def load_bench(path: Path) -> list[dict]:
    """Parse the JSONL benchmark; raise on a malformed or incomplete line."""
    cases: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        missing = {"id", "quote", "inference", "gold"} - case.keys()
        if missing:
            raise ValueError(f"{path.name}:{i} missing fields {sorted(missing)}")
        if case["gold"] not in (POSITIVE, NEGATIVE):
            raise ValueError(f"{path.name}:{i} bad gold label {case['gold']!r}")
        cases.append(case)
    return cases


def class_balance(bench: list[dict]) -> dict[str, int]:
    """Count cases per gold class — a benchmark with an empty class is meaningless."""
    return {
        POSITIVE: sum(1 for c in bench if c["gold"] == POSITIVE),
        NEGATIVE: sum(1 for c in bench if c["gold"] == NEGATIVE),
    }


def blind_view(bench: list[dict]) -> list[dict]:
    """The detector's input: the quote and the inference, never the gold or rationale."""
    return [{"id": c["id"], "source": c.get("source_key", ""), "slug": c.get("slug", ""),
             "quote": c["quote"], "inference": c["inference"]} for c in bench]


def normalise_verdict(raw: str) -> str | None:
    """Map a free-text verdict onto out-of-context | apt, or None if unrecognised."""
    v = raw.strip().lower()
    if v in _OOC_WORDS:
        return POSITIVE
    if v in _APT_WORDS:
        return NEGATIVE
    return None


def load_verdicts(path: Path) -> dict[str, str]:
    """Parse a verdicts JSONL ({id, verdict}) into {id: normalised-verdict}."""
    out: dict[str, str] = {}
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if "id" not in rec or "verdict" not in rec:
            raise ValueError(f"{path.name}:{i} needs both 'id' and 'verdict'")
        norm_v = normalise_verdict(str(rec["verdict"]))
        if norm_v is None:
            raise ValueError(f"{path.name}:{i} unrecognised verdict {rec['verdict']!r}")
        out[rec["id"]] = norm_v
    return out


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def score(bench: list[dict], verdicts: dict[str, str]) -> dict:
    """Confusion matrix + rates, positive class = out-of-context. Cases with no
    verdict are reported as `unscored`, never silently counted as correct."""
    tp = fp = tn = fn = 0
    unscored: list[str] = []
    for c in bench:
        v = verdicts.get(c["id"])
        if v is None:
            unscored.append(c["id"])
            continue
        gold = c["gold"]
        if gold == POSITIVE and v == POSITIVE:
            tp += 1
        elif gold == POSITIVE and v == NEGATIVE:
            fn += 1
        elif gold == NEGATIVE and v == NEGATIVE:
            tn += 1
        else:  # gold apt, verdict out-of-context
            fp += 1
    scored = tp + fp + tn + fn
    return {
        "n_cases": len(bench),
        "n_scored": scored,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "recall": _rate(tp, tp + fn),          # out-of-context caught / all out-of-context
        "specificity": _rate(tn, tn + fp),     # apt correctly passed / all apt
        "precision": _rate(tp, tp + fp),       # flagged that are truly out-of-context
        "accuracy": _rate(tp + tn, scored),
        "unscored": unscored,
    }


def reprove(bench: list[dict], claims_dir: Path) -> tuple[list[str], list[str]]:
    """Re-prove each embedded quote is a verbatim span of ledger <claims-dir>/<key>.md
    (norm-substring). Returns (proved-ids, problems). A line whose ledger is absent is
    skipped, not failed — one dir holds one case's ledgers."""
    proved: list[str] = []
    problems: list[str] = []
    for c in bench:
        key = c.get("source_key")
        if not key:
            continue
        ledger = claims_dir / f"{key}.md"
        if not ledger.is_file():
            continue
        body = norm(ledger.read_text(encoding="utf-8", errors="ignore"))
        if norm(c["quote"]) in body:
            proved.append(c["id"])
        else:
            problems.append(f"{c['id']}: quote not found verbatim in {ledger.name}")
    return proved, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure a detector's out-of-context detection rate on the benchmark.")
    ap.add_argument("--bench", default=str(BENCH), help="benchmark JSONL")
    ap.add_argument("--emit-blind", action="store_true",
                    help="print the detector's input (no gold labels)")
    ap.add_argument("--score", metavar="VERDICTS.jsonl",
                    help="score a verdicts JSONL ({id, verdict}) against gold")
    ap.add_argument("--claims-dir", help="re-prove embedded quotes against ledgers in DIR")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    bench = load_bench(Path(args.bench))
    balance = class_balance(bench)
    if 0 in balance.values():
        log_error(f"benchmark is not class-balanced: {balance} — recall/specificity "
                  "are only meaningful with both classes present")
        return 2

    if args.emit_blind:
        for case in blind_view(bench):
            print(json.dumps(case, ensure_ascii=False))
        return 0

    if args.claims_dir:
        proved, problems = reprove(bench, Path(args.claims_dir))
        for p in problems:
            log_error(p)
        log_info(f"re-proved {len(proved)} embedded quote(s) verbatim against "
                 f"{args.claims_dir}; {len(problems)} mismatch(es)")
        if not args.score:
            return 2 if problems else 0

    if args.score:
        verdicts = load_verdicts(Path(args.score))
        result = score(bench, verdicts)
        if args.json:
            print(json.dumps(result, indent=2))
            return 0
        c = result["confusion"]
        log_info(f"benchmark {result['n_cases']} cases "
                 f"({balance[POSITIVE]} out-of-context, {balance[NEGATIVE]} apt); "
                 f"scored {result['n_scored']}")
        log_info(f"confusion: tp={c['tp']} fp={c['fp']} tn={c['tn']} fn={c['fn']} "
                 f"(positive class = out-of-context)")
        log_info(f"recall {result['recall']} · specificity {result['specificity']} · "
                 f"precision {result['precision']} · accuracy {result['accuracy']}")
        if result["unscored"]:
            log_info(f"unscored (no verdict): {', '.join(result['unscored'])}")
        return 0

    # No action flag: report the benchmark's shape.
    log_info(f"benchmark: {len(bench)} cases — {balance[POSITIVE]} out-of-context, "
             f"{balance[NEGATIVE]} apt. Use --emit-blind, --score, or --claims-dir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
