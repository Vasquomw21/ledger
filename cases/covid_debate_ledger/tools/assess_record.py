# === SCRIPT: Assessment-record helper — attested, grounded judgement records ===
# Purpose: the assessment layer's authoring half (analogue of verify_quotes.py
#          --stamp for the provenance layer). A judgement about a claim — this
#          span is rhetorical, these two supports are correlated, this is the crux
#          — is recorded as content/assessments/_records/<id>.assess.json, sealed
#          EXACTLY like a verification run-record: it reuses verify_quotes'
#          run_record_digest (self-seal), git_committer (attribution) and
#          sha256_text (body binding), so the two record kinds share one schema
#          discipline. body_sha256 binds the judgement to the SUBJECT claim's
#          current text (via claim_graph.claim_body), so an edit to the assessed
#          claim staleness-flags the judgement, just as a quote edit does a stamp.
#
#          HONEST BOUNDARY (the central seam, stated in code): this buys an
#          attributable, tamper-evident, grounded, staleness-aware judgement. It
#          does NOT prove the judgement is correct — it makes it re-judgeable: a
#          reviewer fetches the record and writes a competing one. check_assessment
#          validates these records; this module writes/reseals them.
# INPUTS : --subject / --grounding as <ledger_key>:<slug> claim addresses;
#          literature/verified_claims/<key>.md for the subject body hash.
# OUTPUTS: content/assessments/_records/<id>.assess.json; stdout the path.
# Run    : python3 tools/assess_record.py --write --kind rhetorical --id <id> \
#            --subject andersen_2020:fcs-not-expected \
#            --grounding andersen_2020:fcs-not-expected --span "irrefutably show"
#          python3 tools/assess_record.py --reseal content/assessments/_records/<id>.assess.json
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# verify_quotes owns the digest + identity helpers; reuse them verbatim so an
# assess-record seals identically to a verification run-record.
sys.path.insert(0, str(REPO_ROOT / "literature"))
from verify_quotes import git_committer, run_record_digest, sha256_text  # noqa: E402

import claim_graph as cg  # noqa: E402

CLAIMS_DIR = REPO_ROOT / "literature" / "verified_claims"
ASSESS_DIR = REPO_ROOT / "content" / "assessments"
RECORDS_DIR_NAME = "_records"
ASSESSOR_TOOL = "assess_record.py"
ASSESS_VERSION = "1"

# The judgement kinds an attested record may carry. Small + closed on purpose:
# each maps to one assessment dimension and one in-band marker.
#   edge — judges a supports/rebuts edge APT (the inference it asserts is
#   warranted, not merely that the edge resolves). It is the record an
#   edge_assessments `[rec:]` points to; subject = the edge's target claim,
#   grounding = the claim the edge is grounded by. (Without it, the only way to
#   satisfy edge_assessments was to mislabel a rhetorical/crux-of record.)
#   faithfulness — the adversarial-faithfulness finding: the grounding quote does
#   NOT warrant the inference an `edge` record claims (it is read out of context or
#   tendentiously). subject = the edge's target claim, grounding = the edge's
#   grounding claim (the quote being challenged), span = the quote-pinned substring
#   read unfaithfully, disputes = [the edge record id it contests]. This moves L1
#   "quote out of context" from Uncovered to Assisted: the challenge is now a
#   first-class, sealed, re-judgeable record, not loose commentary — though
#   faithful use is still judgement, never proven.
#   faithfulness-pass — the paired positive review: an adversarial read was
#   performed over an edge record and no quote-context dispute was filed. It is
#   still judgement, not a proof; `reviews` names the edge record reviewed.
ASSESS_KINDS = frozenset({"rhetorical", "correlated-with", "crux-of",
                          "calibration", "status", "edge", "faithfulness",
                          "faithfulness-pass"})

# Every record carries these; record_sha256 self-seals all the others.
REQUIRED_FIELDS = ("kind", "id", "subject", "grounding", "assessed_date",
                   "assessor", "assessor_tool", "assess_version",
                   "body_sha256", "record_sha256")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def subject_body_sha256(subject: str, claims_dir: Path = CLAIMS_DIR) -> str:
    """sha256 of the SUBJECT claim's current body, or "" if it does not resolve.
    Global address only (key:slug) — a judgement names the claim it is about
    unambiguously, so a bare slug (no ledger) cannot bind."""
    addr = cg.parse_address(subject)
    if addr.key is None:
        return ""
    ledger = cg.ledger_for_key(claims_dir, addr.key)
    if ledger is None:
        return ""
    body = cg.claim_body(ledger, addr.slug)
    return sha256_text(body) if body is not None else ""


def build_record(kind: str, rec_id: str, subject: str, grounding: list[str],
                 span: str, assessed_date: str,
                 claims_dir: Path = CLAIMS_DIR,
                 repo_root: Path = REPO_ROOT,
                 disputes: list[str] | None = None,
                 reviews: list[str] | None = None) -> dict:
    """Assemble + self-seal a judgement record. body_sha256 binds to the subject
    claim's current text; record_sha256 seals everything else (run_record_digest).
    `disputes` names the record id(s) this judgement CONTESTS — competing/reviewer
    assessments are first-class, explicitly linked, not loose commentary."""
    record = {
        "kind": kind,
        "id": rec_id,
        "subject": subject,
        "grounding": list(grounding),
        "span": span or "",
        "disputes": list(disputes or []),
        "reviews": list(reviews or []),
        "assessed_date": assessed_date,
        "assessor": git_committer(repo_root),
        "assessor_tool": ASSESSOR_TOOL,
        "assess_version": ASSESS_VERSION,
        "body_sha256": subject_body_sha256(subject, claims_dir),
    }
    record["record_sha256"] = run_record_digest(record)
    return record


def records_dir(assess_dir: Path = ASSESS_DIR) -> Path:
    return assess_dir / RECORDS_DIR_NAME


def record_path(rec_id: str, assess_dir: Path = ASSESS_DIR) -> Path:
    return records_dir(assess_dir) / f"{rec_id}.assess.json"


def write_record(record: dict, assess_dir: Path = ASSESS_DIR) -> Path:
    """Write a sealed record to content/assessments/_records/<id>.assess.json."""
    rd = records_dir(assess_dir)
    rd.mkdir(parents=True, exist_ok=True)
    path = rd / f"{record['id']}.assess.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def reseal(path: Path, claims_dir: Path = CLAIMS_DIR,
           repo_root: Path = REPO_ROOT) -> dict:
    """Recompute body_sha256 (subject may have changed) + record_sha256 and
    rewrite the record in place — the explicit re-attestation after a subject edit
    (the assess analogue of verify_quotes --stamp). Returns the resealed record."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    record["body_sha256"] = subject_body_sha256(record.get("subject", ""), claims_dir)
    record["assessor"] = git_committer(repo_root)
    record["record_sha256"] = run_record_digest(record)
    Path(path).write_text(json.dumps(record, indent=2, sort_keys=True,
                                     ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Write/reseal an attested, grounded judgement record.")
    ap.add_argument("--write", action="store_true", help="write a new record")
    ap.add_argument("--reseal", metavar="PATH",
                    help="recompute body_sha256 + record_sha256 of an existing record")
    ap.add_argument("--kind", choices=sorted(ASSESS_KINDS))
    ap.add_argument("--id")
    ap.add_argument("--subject", help="the assessed claim, as <ledger_key>:<slug>")
    ap.add_argument("--grounding", action="append", default=[],
                    help="a grounding claim address (repeatable)")
    ap.add_argument("--span", default="",
                    help="the quote-pinned span (kind=rhetorical or faithfulness)")
    ap.add_argument("--disputes", action="append", default=[],
                    help="a record id this judgement contests (repeatable)")
    ap.add_argument("--reviews", action="append", default=[],
                    help="a record id this judgement positively reviews (repeatable)")
    ap.add_argument("--date", required=False, help="assessed date YYYYMMDD")
    ap.add_argument("--claims-dir", default=str(CLAIMS_DIR))
    ap.add_argument("--assess-dir", default=str(ASSESS_DIR))
    args = ap.parse_args()

    if args.reseal:
        rec = reseal(Path(args.reseal), Path(args.claims_dir))
        log_info(f"resealed {args.reseal} (body={rec['body_sha256'][:12] or '<unresolved>'}…)")
        return 0
    if not args.write:
        log_error("nothing to do — pass --write or --reseal")
        return 2
    for req in ("kind", "id", "subject", "date"):
        if not getattr(args, req):
            log_error(f"--{req} is required with --write")
            return 2
    record = build_record(args.kind, args.id, args.subject, args.grounding,
                          args.span, args.date, Path(args.claims_dir),
                          disputes=args.disputes, reviews=args.reviews)
    path = write_record(record, Path(args.assess_dir))
    log_info(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
