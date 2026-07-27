# Subject-specific writing rules (the "skin") — Quantum KE white paper

The universal rules (Mara test, A/B/C/D/E/F, gates G0–G4) live in `skill-ledger-write`. This
file holds **only** the rules specific to a hype-prone, dual-audience, policy-facing science
white paper. `skill-ledger-write` loads these at Step 2 and audits against them at Step 4; rules
tagged **[gate]** block apply if violated (GS).

**Voice.** Multi-author white paper: use a defined collective "we" for the authoring team, or
impersonal construction. Never an undefined "we". State who did what only where it matters.

---

**W1 — Dual-audience register.** Every section serves both readers. The opening lands the
**policy stake** (why this matters for Kenya's choices) in plain language; the body carries the
**evidence** at a depth a scientist cannot fault. No unexplained jargon for the minister; no
hand-waving for the scientist. Diagnostic: can you point to the sentence that gives the
policymaker the "so-what", and to the sentences that give the scientist the verifiable basis? If
either is missing, the section fails W1.

**W2 — No-hype discipline. [gate]** (The most important rule for a quantum topic.) Every
capability claim is explicitly positioned on a three-level ladder:
- **Demonstrated** — shown in a peer-reviewed result on real (or clearly-stated toy) data.
- **Plausible / projected** — supported by resource estimates or theory but not yet realised.
- **Aspirational** — a hope or roadmap item, not yet substantiated.
Use calibrated verbs (B.9): *has been shown* vs *could, in principle* vs *is hoped*. An unlabelled
claim that reads as established but is only projected/aspirational is a W2 failure. Banned:
"quantum will revolutionise…", "exponential speed-up" without naming the problem class and its
assumptions, any speed-up claim that omits the NISQ/error-correction caveat.

**W3 — Primary-source-for-policy. [gate]** Any statistic, policy provision, legal fact, or
institutional claim cites the **primary source** — legislation, an official government
report/PDF, a peer-reviewed paper — never a news article, blog, or press release, and never a
secondary summary. Verify the number against the cited source before it enters prose (the
verified_claims ledger is the record). If a primary source cannot be found, the claim is dropped
or marked unverified — it is not backfilled with a news link.

**W4 — Honest-on-Kenya/Africa. [gate]** Surface genuine African/Kenyan touchpoints (talent,
genomics capacity, infrastructure, policy) where the evidence supports them; where it is thin,
**say so plainly**. Never inflate a handful of facts into a manufactured national narrative, and
never imply Kenyan involvement in a milestone the sources do not support. Aspirational framing of
what Kenya *could* build is allowed only under W2 labelling ("aspirational").

**W5 — Progressive disclosure.** The main line of each section is readable by a non-specialist.
Technical depth (formal definitions, algorithm internals, resource estimates, derivations) goes
in clearly-marked callout boxes (`> [!note]` / `> [!math]`) or appendix concept notes reachable
via a `[[wikilink]]`. A section that forces the policymaker through the maths to reach the point
fails W5.
