---
name: coverage-closure
description: Hole classification taxonomy, exclusion policy, and closure evidence rules. Use when analyzing coverage holes, proposing exclusions, or closing coverage.
---

# Coverage Closure Policy

## Hole taxonomy (mandatory classification before action)
- **A — reachable, stimulus gap**: constrained-random can reach it with
  constraint/sequence work. Action: stimulus improvement, prove with
  `dv cov delta`.
- **B — reachable, needs directed**: a corner requiring explicit setup
  randomization won't plausibly produce. Action: small directed sequence,
  still through interfaces, still judged by existing checkers.
- **C — unreachable**: impossible by design, configuration, or spec.
  Action: exclusion PROPOSAL with spec/config reference. Humans apply.
- **D — covergroup defect**: bin wrong, ill-defined, or measuring the
  wrong thing. Action: documented fix proposal. Humans approve semantics
  changes.

## Exclusion policy (hard rules)
- Exclusions/waivers/refinements are applied by humans only, via the
  reviewed refinement file — never inline `ignore_bins` retrofits to make
  numbers green.
- Every exclusion request needs: hole path, classification C rationale,
  spec or configuration reference, requester, date. Template:
  `dv/cov/exclusion_requests.md`.
- An exclusion justified by "we ran out of time" is a sign-off risk
  decision for the program level, not an exclusion — route it upward.

## Closure evidence rules
- Delta claims come from `dv cov delta` verdicts, labeled targeted-run;
  the merged CI database is the binding number.
- A hole is closed by stimulus that exercises the INTENT (vplan text),
  not by any means that touches the bin: no forces, no config backdoors,
  no bin redefinition. If honest stimulus can't hit an honest bin, the
  hole is C or D — reclassify, don't cheat.
- Code coverage holes (branch/expression) in DUT logic: analyze
  reachability from the spec; TB cannot exclude DUT code paths without
  designer confirmation — flag for the block owner.

## Prioritization
Work holes by weight × vplan criticality; a low-weight bin blocking a
sign-off criterion outranks a high-weight nice-to-have. When in doubt,
surface the ranking to the engineer rather than guessing.
