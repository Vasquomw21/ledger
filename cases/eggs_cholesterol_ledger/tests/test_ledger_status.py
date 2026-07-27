# Tests for the read-only status dashboard. Builds tmp projects and
# checks the report reflects state, strictness, and blocking postures. Corpus-free.
import ledger_status as ls

PRISTINE = """\
project_name:        <e.g. x>
deliverable:         <thesis | report>
source_of_truth:     <markdown+quartz>
the_reader:          <the reader>
source_types:        <papers>
skin_rules_file:     content/_ledger/skin_rules.md
"""

CONFIGURED = """\
project_name:        water_ke
deliverable:         report
source_of_truth:     markdown+quartz
the_reader:          a minister
source_types:        gov reports
gated_paths:         content/concept_notes/, content/literature_reviews/
claim_ids:           required
numeric_citations:   block
provenance:          required
structure_layer:     required
assessment_layer:    required
skin_rules_file:     content/_ledger/skin_rules.md
"""

SKIN_EMPTY = "# skin\n\n_(empty — the bootstrap helper drafts this here)_\n"
SKIN_WRITTEN = "# skin\n\n- **W1** a real rule\n"


def _project(tmp_path, config_text, skin_text, gated=False):
    (tmp_path / "ledger.config.md").write_text(config_text, encoding="utf-8")
    skin = tmp_path / "content" / "_ledger" / "skin_rules.md"
    skin.parent.mkdir(parents=True)
    skin.write_text(skin_text, encoding="utf-8")
    if gated:
        (tmp_path / "content" / "concept_notes").mkdir(parents=True)
        (tmp_path / "content" / "literature_reviews").mkdir(parents=True)
    return tmp_path


def test_pristine_report(tmp_path):
    proj = _project(tmp_path, PRISTINE, SKIN_EMPTY)
    report = "\n".join(ls.build_report(proj))
    assert "project state : pristine" in report
    assert "lenient" in report
    assert "(none — lenient)" in report


def test_configured_report_shows_blocking(tmp_path):
    proj = _project(tmp_path, CONFIGURED, SKIN_WRITTEN, gated=True)
    report = "\n".join(ls.build_report(proj))
    assert "project state : configured" in report
    assert "strict (configured)" in report
    assert "BLOCKING" in report
    assert "claim_ids" in report


def test_main_exit_0(tmp_path, monkeypatch):
    proj = _project(tmp_path, PRISTINE, SKIN_EMPTY)
    monkeypatch.setattr("sys.argv", ["ledger_status.py", "--repo-root", str(proj)])
    assert ls.main() == 0
