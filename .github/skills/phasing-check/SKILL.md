---
name: phasing-check
description: >-
  Apply and check UVM phasing and objection correctness per house methodology.
  Use whenever the user writes or reviews build_phase/connect_phase/run_phase
  code, phase ordering, super.<phase> calls, objections, or drain time -- and
  whenever another UVM skill or a review needs the canonical phasing ruleset.
  This is the single source of truth other skills point to.
---

# Phasing and objections (house ruleset)

Apply when authoring; check when reviewing.

## Phase responsibilities

| Phase | Does | Must not |
|---|---|---|
| `build_phase` | create components; `config_db::set` for children; `get` own config | build in reverse order; access siblings |
| `connect_phase` | wire TLM (ports/exports), sequencer<->driver, ap->exports | create components; drive |
| `end_of_elaboration_phase` | print topology / final checks | change structure |
| `run_phase` | time-consuming stimulus; objections | `config_db::set` for structure |
| `check_phase` / `report_phase` | residual checks, summaries | new stimulus |

## Rules

- `super.<phase>(phase)` is called; in `build_phase`/`connect_phase` it is the
  first statement.
- `config_db::set` for structural config happens in `build_phase` (before the
  target builds), never in `run_phase`.
- Objections are raised/dropped in tests and virtual sequences ONLY -- never in
  drivers, monitors, or other components (team standard). Pairs are symmetric
  and reachable on all paths (guard forks so a drop always executes).
- Drain time is set once in the base test (`set_drain_time`), not per-test.
- No `#` delays in tests/sequences/env; timing lives in driver/interface.
- Run-time sub-phases only if the base defines a schedule; then raise/drop in
  the matching phase.

## Review output
Report each violation as: `{rule_id: "phasing.<rule>", severity, file, line,
message, fix}`. Missing `super` in build/connect, asymmetric objections, and
`config_db::set` in `run_phase` are `error`; ordering smells are `warn`.
