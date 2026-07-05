---
name: uvm-coverage
description: >-
  Create a UVM functional coverage collector conforming to house methodology.
  Use whenever the user wants to write, add, create, or scaffold coverage, a
  covergroup, a coverage collector/subscriber, or map a vPlan feature to
  measurable bins -- even if the word "skill" is never used. Covers subscriber
  sampling, covergroup/bins/cross, illegal/ignore bins, and vPlan tagging.
---

# Write a UVM coverage collector

A coverage collector subscribes to a monitor's transactions and samples
covergroups. Every coverpoint traces back to a vPlan feature.

## Inputs to confirm
1. Collector name -> class `<proj>_coverage`.
2. Item type sampled (`<proto>_item`).
3. Coverage goals: which fields, which crosses, and the vPlan feature IDs.
4. Illegal and don't-care value spaces.

## Procedure
1. Create `<proj>_coverage.svh` from `assets/templates/coverage.svh.tmpl`.
2. Extend `uvm_subscriber#(<proto>_item)` (gives `write()` + `analysis_export`).
3. Define the covergroup with coverpoints, crosses, `illegal_bins` and
   `ignore_bins`; set `option.per_instance = 1`.
4. Sample in `write()`. Tag each coverpoint/cross with `// VP-xxx`.

## Hard rules (never violate)
- Extends `uvm_subscriber#(<proto>_item)`; covergroup sampled in `write()`.
- `illegal_bins` defined for value spaces that must never occur;
  `ignore_bins`/`illegal_bins` carry a spec-referenced justification comment
  (team standard) -- exclusions/waivers are proposed, humans apply them.
- Bins encode the vplan intent's named values/crosses/boundaries; no catch-all
  ranges that hit on any traffic; no `option.at_least` below team default.
- Every coverpoint/cross carries a `VP-xxx` reference for traceability.
- No checking (`` `uvm_error ``) here -- coverage measures, scoreboard judges.
- Coverage samples observed behavior via monitors; never `sample()` from
  stimulus code (team standard).

## Definition of Done
- [ ] `dv compile <ip>` verdict clean (never call xrun directly).
- [ ] Covergroups sample on traffic; hits appear in IMC.
- [ ] `illegal_bins`/`ignore_bins` defined; no spurious illegal hits on legal runs.
- [ ] Every coverpoint/cross `VP-xxx`-referenced and resolvable.

Naming and deprecation rules are enforced by the `naming-conventions` and
`deprecation-lint` skills; `verif-env-review` checks tagging and connectivity.
