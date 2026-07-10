# Definition of Done — verification work item

[TEMPLATE — replace with the team's authoritative DoD from the block
verification standard. The dv-reviewer audits MRs against this list.]

A vplan item / MR is DONE when ALL hold:

1. **Traceability**: MR references the VP id; the item's requirement text
   matches what was implemented. Items marked `[design-intent — spec
   silent]` are closable only after the intent is confirmed in writing
   (spec update, design note, or recorded designer answer).

0. **(Vplan-level, once per block)**: the cross-cutting completeness
   matrix is fully resolved — every common topic mapped to items or a
   justified N/A — before the block enters coverage-closure phase.
2. **Compile & lint**: compile clean (`make compile`; wrapper: `dv
   compile`); deprecation-lint `lint.py` clean on the touched TB paths
   (wrapper: `dv lint --diff`).
3. **Simulation evidence**: passing verdicts attached verbatim for ≥3
   seeds (listed) — verif_matrix.yaml records / UVM report summaries
   (wrapper: JSON verdicts) — zero UVM_ERROR/FATAL, end-of-test marker
   present, zero new UVM_WARNINGs vs. baseline.
4. **Coverage evidence**: the item's mapped bins hit (verdict attached);
   no unexplained coverage regression in touched groups.
5. **Check evidence**: the item's mapped check IDs exist, were exercised
   (Gate-3 style sampling proof for new checks), and have a chkq negative
   test in dv/lists/chkq.list.
6. **Ripple safety**: sanity list passing if shared stimulus was touched.
7. **No shortcut markers**: no exclusions applied, no severity demotions,
   no checker semantics relaxed, no `+CHKQ_ENABLE` outside negative
   tests, no forces outside chkq-kit (deterministic gate + reviewer).
8. **Report**: session report per the evidence contract, including the
   "not verified" section, attached to the MR.
9. **Human review**: MR approved; checker-touching MRs carry explicit
   checker sign-off.
