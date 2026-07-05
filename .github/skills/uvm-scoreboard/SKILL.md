---
name: uvm-scoreboard
description: >-
  Create a UVM scoreboard / checker conforming to house methodology. Use
  whenever the user wants to write, add, create, or scaffold a scoreboard, a
  checker, a reference-model comparison, or the component that receives
  monitored transactions and verifies correctness -- even if the word "skill"
  is never used. Covers analysis imp/exports, expected-vs-actual compare, and
  end-of-test residual checks.
---

# Write a UVM scoreboard

The scoreboard receives monitored transactions and checks them against a
reference model or an expected queue. It is where `` `uvm_error `` for functional
mismatch belongs.

**Check independence.** Predict the expected result from the *observed input*
(an input monitor) run through an *independent reference* -- spec, golden model,
or reference implementation. Never predict from the *intended stimulus*: the
sequence item, the randomized knobs, or config read as golden. Predicting from
what you meant to send re-derives your own assumptions, so a DUT bug that
happens to match a stimulus-model bug passes silently. Predicting from what the
DUT actually saw also catches driver bugs.

## Inputs to confirm
1. Scoreboard name -> class `<proj>_scoreboard`.
2. Input streams (e.g. stimulus-side and result-side) and their item types.
3. Checking model: reference function, transfer function, or in/out ordering.

## Procedure
1. Create `<proj>_scoreboard.svh` from `assets/templates/scoreboard.svh.tmpl`.
2. For one stream use `uvm_analysis_imp`; for multiple streams use
   `` `uvm_analysis_imp_decl(_<name>) `` to get `write_<name>` methods.
3. Feed the expected/input side from an **input monitor**, transform it through
   an **independent reference**, and compare against the result side; emit
   `` `uvm_error `` with a STABLE, UNIQUE check ID per distinct check
   (`SCBD_DATA_CMP`, `SCBD_ORDER`, ...) and a message carrying the compared
   values and transaction identifiers. Check IDs are API: chkq negative tests
   and triage bucketing key on them.
4. In `check_phase`, flag any unmatched/residual transactions as errors.

## Hard rules (never violate)
- Extends `uvm_scoreboard` (or `uvm_component`) with analysis imp/exports.
- Compares expected vs actual; `` `uvm_error `` on mismatch, never silent.
- **Expected values derive from monitored inputs plus an independent reference
  (spec / golden model) -- never from the sequence item, the randomized stimulus
  knobs, or `config_db` read as golden. The scoreboard is fed by monitors only,
  never by a driver.**
- Reports residual/unmatched items at `check_phase` -- an empty compare is not
  a pass.
- No stimulus generation and no pin access.
- `` `uvm_fatal `` reserved for TB integrity (null handle, config miss), never
  for DUT behavior checks; no severity demotions anywhere.
- Modifying EXISTING check semantics is out of scope for agents (additive-only
  rule; see the `dv-checker-writer` agent protocol) -- a human owns that.

## Definition of Done
- [ ] `dv compile <ip>` verdict clean (never call xrun directly).
- [ ] Detects an injected mismatch (fails when it should).
- [ ] Reports leftover/unmatched transactions at end of test.
- [ ] No false pass on zero traffic (checks that traffic occurred).
- [ ] Expected derived from observed input + independent reference, not from the
      stimulus; no sequence/stimulus handle or `include` in the scoreboard.
- [ ] Every new check ID has a chkq negative test registered in
      `dv/lists/chkq.list` (fault injection via `chkq_injector` proves the
      check fires); injection evidence table in the session report.

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks this.
