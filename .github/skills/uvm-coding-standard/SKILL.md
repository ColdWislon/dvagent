---
name: uvm-coding-standard
description: Team SystemVerilog/UVM coding rules. Use whenever writing or reviewing testbench code — sequences, tests, components, checkers, covergroups.
---

# UVM Coding Standard (agent-enforceable rules)

Rules are written to be checkable. "MUST" rules are review findings when
violated; "SHOULD" rules need a stated justification to deviate.
[TEAM: merge your authoritative standard here — this file is the baseline.]

Detail layer: `naming-conventions`, `phasing-check`, and `deprecation-lint`
expand these rules with full tables, review-finding schemas, and a
deterministic linter (`deprecation-lint/scripts/lint.py`, CI-side). On any
conflict, THIS file wins.

## Classes and factory
- Every class MUST be registered with the factory (`uvm_component_utils` /
  `uvm_object_utils`); creation MUST use `type_id::create()`, never `new()`
  (constructor use allowed only for report catchers and pure-utility
  objects).
- One class per file; filename equals class name.
- Extend existing base classes; a new parallel hierarchy when a base
  exists is a defect.

## Configuration
- Configuration flows through nested config objects (env config contains
  agent configs), set once at test level. `uvm_config_db` reads happen in
  `build_phase` and are cached in fields — never in run-time hot paths.
- Every `uvm_config_db::get` MUST check the return value and `uvm_fatal`
  on a missing mandatory entry.
- No plusarg reads scattered in components; plusargs are parsed in the
  test/config layer only.

## Sequences and stimulus
- No `#delay` in sequence bodies; synchronize on interface events, TLM, or
  sequencer grants.
- Every `randomize()` call MUST be checked:
  `if (!req.randomize() with {...}) `uvm_fatal(...)`.
- Constraints layered: legal space in the item, scenario shaping in the
  sequence, corners as overridable layers. Corners MUST NOT be baked into
  item base constraints.
- Sequences MUST NOT reach into DUT hierarchy (no hierarchical paths, no
  forces) and MUST NOT use `uvm_config_db` writes to steer components
  mid-run.

## Components and phasing
- Objections raised/dropped in tests and virtual sequences only, not in
  drivers/monitors.
- Monitors are passive: no stimulus side effects, no protocol state
  correction.
- `check_phase`/`report_phase` used for end-of-test consistency checks
  (scoreboard emptiness, outstanding-transaction counters).

## Checkers and messaging (chkq-critical)
- Every check reports via `uvm_error` with a STABLE, UNIQUE message ID
  (e.g. `SCBD_DATA_CMP`, `SCBD_ORDER`, `CHK_EXCL_RESP`), one ID per
  distinct check. IDs are API: chkq negative tests and triage bucketing
  key on them — renaming an ID is a breaking change requiring the chkq
  list to be updated in the same MR.
- `uvm_fatal` reserved for TB integrity failures (null handles, config
  misses, connection errors), never for DUT behavior checks.
- No `UVM_ERROR`→`UVM_WARNING` demotions, no severity overrides in
  functional code; expected-error handling exists only in chkq negative
  tests via `chkq_expectation`.
- Message text MUST carry the compared values and transaction identifiers
  (debuggability is part of check quality).

## Assertions (SVA)
- One property per check intent, labeled with the check ID.
- `disable iff` restricted to reset.
- Every `assert property` paired with a `cover property` of its
  antecedent (vacuity visibility).

## Covergroups
- Every covergroup bin carries a `// VP-xxx` vplan reference comment.
- Bins encode the vplan intent's named values/crosses/boundaries; no
  catch-all ranges that hit on any traffic.
- No `option.at_least` reductions below team default; `ignore_bins`/
  `illegal_bins` require a spec-referenced justification comment.
- Sampling event explicit and documented; no `sample()` from stimulus
  code (coverage samples observed behavior via monitors).

## General
- No `$display` in class-based code — UVM reporting only.
- No dead code committed (`// TODO remove`, commented-out blocks).
- Lint (`dv lint --diff`) clean before any MR.
