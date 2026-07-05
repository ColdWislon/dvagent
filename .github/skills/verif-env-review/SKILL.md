---
name: verif-env-review
description: >-
  Review or audit a complete verification environment -- not just the UVM
  testbench, but the build, regression, coverage, assertion, vPlan and CI layers
  around it -- and emit a gate-ready scorecard. Use whenever the user wants to
  audit, review, sign off, or assess milestone / tapeout readiness of a
  verification environment or a block/IP deliverable, wants a project-level or
  multi-axis quality review, or a pre-merge / pre-milestone gate -- even if the
  word "skill" is never used. This is the single review entry point: it covers
  the testbench code (as its first axis) and the infrastructure around it.
---

# Review a full verification environment

Audit the whole delivered verification environment against house methodology and
produce a scorecard plus a machine-readable verdict a CI gate can act on. The
UVM testbench code is one axis of nine; the rest cover everything needed to run,
regress, measure and reproduce the verification. Report findings with
`file:line` and a fix; do not rewrite.

## Inputs to confirm
1. Scope: the project / repo root (not just the `tb/` classes).
2. Milestone under assessment (M0-M3), if rolling up to the DoD ladder.
3. Fail policy: errors only (default) or errors + warnings.

## Axes
Run each axis; collect findings. Location hints are conventions -- adapt to the
house layout.

1. **Testbench code** — apply the testbench-code review in
   `references/testbench-code-review.md` (components, naming, phasing, TLM,
   factory/config, reuse, checking independence), reusing the three law skills
   (`naming-conventions`, `phasing-check`, `deprecation-lint`) and
   `deprecation-lint/scripts/lint.py`. Roll its findings up as this axis.
2. **DUT integration / TB top** (`*_tb_top.sv`, `hdl_top` / `hvl_top`) — DUT and
   interfaces instantiated; clock / reset generation present; `run_test()` called
   once; virtual interfaces set into `config_db` at the top; timescale set; test
   selected via `+UVM_TESTNAME`; no test logic in the top.
3. **Build & packaging** (`*.f`, `*_pkg.sv`, compile scripts; all tool access
   via the `dv` wrapper, never raw xrun) — filelists
   complete and correctly ordered; package does `import uvm_pkg::*` and
   `` `include "uvm_macros.svh" ``; incdirs / defines / `-uvmhome` correct;
   zero-warning compile policy; no absolute or user-specific paths.
4. **Regression (vManager)** (`*.vsif`) — tests grouped into sessions; seed
   policy is random *and* captured for rerun; run counts set; the test list is
   version-controlled and reproducible.
5. **Coverage flow (IMC)** (merge / rank scripts, coverage config) — functional
   and code coverage targets defined; merge / rank in place; every exclusion is
   justified and reviewed; ucdb archived.
6. **Assertions (SVA)** (`*_bind.sv`, assertion files) — assertions bound to the
   DUT; concurrent assertions carry a reset guard (`disable iff`); assertion
   results are checked in regression, not merely elaborated.
7. **vPlan & traceability** — a vPlan exists; every `VP-xxx` reference resolves to a
   real feature; every feature has at least one test and one coverage item;
   the closure metric is tied to the M0-M3 ladder and the DoD gate.
8. **CI gates (Jenkins)** — pipeline runs compile -> smoke -> nightly regression
   -> coverage merge -> review; deterministic gates are wired (the review JSON,
   the DoD checklists, the lint exit code, `dv lint --diff`); logs / ucdb /
   reports archived; a failing gate blocks merge. The per-item DoD is the
   team's `docs/methodology/definition-of-done.md`; this review's milestone
   verdict must not contradict it. Complementary to the `dv-reviewer` agent:
   dv-reviewer reviews one DIFF pre-MR (semantic shortcuts); this skill audits
   the delivered ENVIRONMENT.
9. **Reproducibility & hygiene** — tool versions pinned; seeds captured; a
   clean-checkout build runs; a README documents how to build / run / regress;
   ownership is clear.

## Output (both)

A human scorecard, then one JSON block (the gate parses the JSON):

```json
{
  "summary": { "errors": 0, "warnings": 0, "dod_pass": true, "milestone_ready": "M2" },
  "axes": [
    { "axis": "testbench_code", "status": "pass", "errors": 0, "warnings": 1 },
    { "axis": "regression",     "status": "fail", "errors": 1, "warnings": 0 }
  ],
  "findings": [
    { "axis": "regression", "rule_id": "vsif.no_seed_capture", "severity": "error",
      "file": "regr/nightly.vsif", "line": 12,
      "message": "seeds not captured; reruns not reproducible",
      "fix": "record sv_seed per run and support rerun from the session" }
  ]
}
```

`status` per axis: `pass` (no findings), `warn` (warnings only), `fail` (>=1
error).

## Gate rule (deterministic)
`dod_pass` is `false` and the gate **fails** on any `error` finding (or any
`warning` under an errors+warnings policy). `milestone_ready` is the highest
M-level whose required axes are all `pass`. Wire the JSON into the Jenkins
milestone gate.

## Hard rules (never violate)
- Cover all nine axes over the project root, not just `tb/`.
- Report, do not rewrite; every finding has `file`, `line`, `fix`.
- Reuse the testbench-code review and the law skills verbatim for the code axis;
  do not restate their rules with different severities.
- Emit valid JSON exactly once, after the human scorecard.

## Definition of Done (of the review itself)
- [ ] All nine axes assessed over the project root.
- [ ] `testbench_code` axis backed by `references/testbench-code-review.md` + lint output.
- [ ] Every finding has axis, file, line, severity, message, fix.
- [ ] JSON validates; per-axis rollup matches findings; milestone verdict justified.
