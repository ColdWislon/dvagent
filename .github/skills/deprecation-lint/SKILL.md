---
name: deprecation-lint
description: >-
  Detect deprecated UVM API and house-standard deviations in SystemVerilog/UVM
  code. Use whenever the user wants to lint, modernise, review, or clean up UVM
  code, or asks whether an API is deprecated -- and whenever another UVM skill
  or a review needs the canonical deprecation/anti-pattern ruleset. This is the
  single source of truth other skills point to.
---

# Deprecation and anti-pattern lint (house ruleset)

Scan code for the left column; apply the fix. Severity drives the Jenkins gate.

## Ruleset

| Anti-pattern / deprecated | Fix | Severity |
|---|---|---|
| `extends uvm_test` | `extends <proj>_base_test` | error |
| missing `` `uvm_*_utils `` registration | add factory registration | error |
| `new()` for a component/sequence | `::type_id::create` | error |
| `#<n>` delay in test/seq/env | move timing to driver/interface; events/objections | error |
| `run_test()` inside a test | remove; select via `+UVM_TESTNAME`/vsif | error |
| asymmetric raise/drop objection | one symmetric, reachable pair | error |
| `config_db::set` (structural) in `run_phase` | move to `build_phase` | error |
| missing `super.build_phase`/`connect_phase` | add as first statement | error |
| `starting_phase = ...` (variable) | `get_starting_phase()`/`set_starting_phase()` | warn |
| legacy `set_config_*` / `get_config_*` | `uvm_config_db#(T)::set/get` | warn |
| `` `uvm_do `` / `` `uvm_do_with `` (house policy) | explicit `create`+`start_item`/`finish_item` | warn |
| global `config_db` `"*"` scope | scope to target subtree | warn |
| raw `$display` for status | `` `uvm_info(get_type_name(), ...) `` | warn |
| driver/monitor referencing DUT hierarchy | go through the virtual interface | error |
| checking (`` `uvm_error ``) inside a monitor | move to scoreboard | warn |
| covergroup coverpoint without `VP-xxx` reference | add `// VP-xxx` | warn |
| `UVM_ERROR`->`UVM_WARNING` demotion / severity override in functional code | remove; expected errors exist only in chkq negative tests | error |
| `force` / `uvm_hdl_force` / `uvm_hdl_deposit` outside `dv/tests/negative/` or not via `chkq_injector` | route through the chkq kit or delete | error |
| unchecked `randomize()` (return value ignored) | `if (!x.randomize()) `` `uvm_fatal `` | error |
| unchecked mandatory `config_db::get` | check return; `` `uvm_fatal `` on miss | error |
| plusarg reads scattered in components | parse plusargs in the test/config layer only | warn |
| check `` `uvm_error `` without a stable unique ID | one `SCBD_*`/`CHK_*` ID per distinct check | warn |
| scoreboard `` `include `` or handle of a sequence / stimulus class | feed the scoreboard from monitors + an independent reference only | error |
| driver analysis port connected to the scoreboard | connect the scoreboard to input **monitors**, not the driver | error |
| scoreboard `config_db::get` used as golden / expected | derive expected from observed input + spec, not stimulus knobs | warn |

## Review output
Report each finding as: `{rule_id: "deprec.<n>", severity, file, line, message,
fix}`. The gate fails on any `error`.

## Deterministic lint (LLM-free)
`scripts/lint.py` implements the check-independence subset of this ruleset as a
regex scanner: forbidden sequence/stimulus `` `include ``s and handles in
scoreboard files, and driver->scoreboard connections in env files. It emits the
same JSON schema and returns a non-zero exit code on any `error`, so the Jenkins
gate can run it without the model in the loop:

    python3 scripts/lint.py <rtl_or_tb_path> [--fail-on-warning]

Point it at the testbench source, not at this skill's own `scripts/tests/`
fixtures. The full ruleset above still needs the `verif-env-review` pass; the
script covers the part that must be mechanical and is easiest to regress.
