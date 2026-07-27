# === SCRIPT: faithfulness_baseline — transparent detector for benchmark sanity ===
# A deliberately small, inspectable detector for the faithfulness benchmark. It is
# not a model and not a gate; it provides a reproducible baseline score so the
# evaluation harness is exercised end-to-end. The rules look for common inflation
# patterns: possibility -> certainty, non-exclusion -> likelihood, finding -> proof,
# association -> causation, subgroup -> general population, and overlap -> independent
# confirmation.
# INPUTS : JSONL from faithfulness_eval.py --emit-blind.
# OUTPUTS: verdict JSONL {id, verdict, rationale}.
# Run    : python3 tools/faithfulness_eval.py --emit-blind | python3 tools/faithfulness_baseline.py
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def verdict(case: dict) -> tuple[str, str]:
    quote = str(case.get("quote", ""))
    inference = str(case.get("inference", ""))
    q = quote.lower()
    i = inference.lower()

    if _has(i, r"\b(proves?|therefore no|must have|categorically|mathematically proven|perfectly safe)\b"):
        return "out-of-context", "inference upgrades the source into categorical proof/certainty"
    if _has(i, r"\bmost likely\b") and _has(q, r"cannot be excluded|possible|might"):
        return "out-of-context", "inference upgrades possibility/non-exclusion into likelihood"
    if _has(q, r"\bmight\b|can arise|cannot be excluded|warrant further studies") \
            and _has(i, r"\b(was|is|cause|causes|therefore)\b") \
            and not _has(i, r"\bconsistent|possible|might|may|could|warrant|conclude\b"):
        return "out-of-context", "inference drops the source hedge"
    if _has(i, r"\bindependent(?:ly)? confirms?\b|separate lines? of evidence") \
            and _has(q, r"not associated|associated|consumption|risk"):
        return "out-of-context", "inference asserts independence from a result quote alone"
    if _has(i, r"\bgeneral population\b") and _has(q, r"subgroup|diabetic"):
        return "out-of-context", "inference generalises a subgroup statement"
    if _has(i, r"\bcause|causes|caused\b") and _has(q, r"associated|not associated"):
        return "out-of-context", "inference upgrades association language to causation"
    return "apt", "no rule fired; treated as scope-preserving"


def iter_cases(path: Path | None) -> list[dict]:
    text = path.read_text(encoding="utf-8") if path else sys.stdin.read()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rule-based baseline for faithfulness benchmark.")
    ap.add_argument("blind_jsonl", nargs="?", help="blind JSONL; stdin when omitted")
    args = ap.parse_args(argv)

    for case in iter_cases(Path(args.blind_jsonl) if args.blind_jsonl else None):
        v, rationale = verdict(case)
        print(json.dumps({"id": case["id"], "verdict": v, "rationale": rationale},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
