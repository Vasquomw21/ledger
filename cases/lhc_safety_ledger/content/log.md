# Activity log

Append-only, chronological. Each entry starts with a consistent prefix so the log stays
greppable — `grep "^## \[" content/log.md | tail -5` gives the last five actions.

Entry kinds:
- `ingest` — a source was added and propagated across the knowledge base
- `answer` — a worthwhile query answer was filed back as a note
- `lint`   — a health-check pass was run

<!-- Template (copy, do not edit this comment):
## [YYYY-MM-DD] ingest | Author Year — Title
- key: author_year
- touched: concept_notes/<note>, literature_reviews/<review>_lit.md, crosswalk.md
- contradictions flagged: none
- new pages: none
-->
