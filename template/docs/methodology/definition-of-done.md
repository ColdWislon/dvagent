# Definition of Done — verification work item

[TEMPLATE — replace with the team's authoritative DoD from the block
verification standard. The dv-reviewer audits MRs against this list.]

A vplan item / MR is DONE when ALL hold:

1. **Traceability**: MR references the VP id; the item's requirement text
   matches what was implemented. Items marked `[design-intent — spec
   silent]` are closable only after the intent is confirmed in writing
   (spec update, design note, or recorded designer answer).
2. **(Vplan-level, once per block)**: the cross-cutting completeness
   matrix is fully resolved — every common topic mapped to items or a
   justified N/A — before the block enters coverage-closure phase.
3. **Compile & lint**: compile clean (`make compile`; wrapper: `dv
   compile`); deprecation-lint `lint.py` clean on the touched TB paths
   (wrapper: `dv lint --diff`).
4. **Simulation evidence**: passing verdicts attached verbatim for ≥3
   seeds (listed) — verif_matrix.yaml records / UVM report summaries
   (wrapper: JSON verdicts) — zero UVM_ERROR/FATAL, end-of-test marker
   present, zero new UVM_WARNINGs vs. baseline.
5. **Coverage evidence**: the item's mapped bins hit (verdict attached);
   no unexplained coverage regression in touched groups.
6. **Check evidence**: the item's mapped check IDs exist, were exercised
   (Gate-3 style sampling proof for new checks), and have a chkq negative
   test in dv/lists/chkq.list.
7. **Ripple safety**: sanity list passing if shared stimulus was touched.
8. **No shortcut markers**: no exclusions applied, no severity demotions,
   no checker semantics relaxed, no `+CHKQ_ENABLE` outside negative
   tests, no forces outside chkq-kit (deterministic gate + reviewer).
9. **Report**: session report per the evidence contract, including the
   "not verified" section, attached to the MR.
10. **Human review**: MR approved; checker-touching MRs carry explicit
   checker sign-off.
