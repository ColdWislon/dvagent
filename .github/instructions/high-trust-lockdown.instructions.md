---
name: 'High-trust zone lockdown'
description: 'RTL, SVA, scoreboards, checkers, and coverage waivers are not agent-editable'
applyTo: '**/rtl/**,**/sva/**,**/*scoreboard*,**/*checker*,**/*waiver*,**/*refinement*,**/exclusion*'
---

# High-trust zone — do not modify

Files matching this scope are outside agent editing authority:

- `rtl/` is the design under test. It is read-only for all verification
  work. You may read it to understand behavior; you may never change it.
- Assertions (`sva/`), scoreboards, and checkers define correctness. Any
  change here can silently convert a failing design into a passing report.
  MODIFYING existing check semantics (relaxing compares, demoting
  severities, editing/disabling assertions, restructuring existing checks)
  is forbidden for all agents, in every framing. Even fixes that look
  obviously right require a human author or explicit human sign-off
  recorded in the MR.
- AUTHORING NEW checks is permitted only through the dv-checker-writer
  agent's full protocol: spec-derived plan approved by the engineer before
  code, additive-only diff, clean-pass baseline, and a fault-injection
  evidence table proving every new check fires. The resulting MR still
  requires human sign-off — the protocol earns the right to propose, not
  to merge.
- Coverage waivers/refinements/exclusions are applied by humans only.
  Write proposals to `dv/cov/exclusion_requests.md` with justification.

If a task cannot proceed without changing one of these files, stop, explain
precisely which file and which change is needed and why, and hand the
decision back to the engineer. This is not an obstacle to route around —
attempting the change via generated scripts, git commands, or any other
indirection is the same violation.
