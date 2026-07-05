---
name: xcelium-flow
description: Cadence Xcelium/IMC flow specifics — dv command usage, common compile/elab error patterns, and environment rules. Use when interpreting tool errors or running the flow.
---

# Xcelium Flow Notes

## Flow rules
- All tool access goes through the `dv` wrapper — never invoke `xrun`,
  `imc`, or vManager directly. Verdicts are JSON; raw logs only via
  `dv log first-error` / `dv log grep`.
- Precompiled libraries: UVM and VIP libs are released prebuilt; only the
  IP under work recompiles. If elaboration reports snapshot/lib mismatch,
  the fix is `dv compile <ip> --clean`, not editing library paths.
- chkq negative tests need write access: their build config carries
  `-access +rwc`; do not add global access flags to functional configs.

## Reading common error patterns
- `xmvlog: *E,...` = compile (syntax/type) — fix at file:line in verdict.
- `xmelab: *E,CUVUNF/CUVMUR` (unresolved/undriven) = missing file in the
  compile list or wrong package import order — check the IP's file list
  before editing code.
- `xmelab: *E,ICDCBA` and friends on bind/interface = port/param mismatch
  between TB harness and DUT — read the DUT port list, don't guess.
- `TYCMPAT` = SystemVerilog type check — fix the type, never cast around
  it without understanding why.
- Elab succeeds but time-0 `UVM_FATAL` (config/factory/null vif) = TB
  wiring, see debug playbook — not a compile problem, don't recompile in
  a loop.

## Simulation behavior
- Seeds come from the `dv sim --seed` argument and appear in the verdict;
  reproduction REQUIRES the same seed and same snapshot.
- Waves (`--waves`) cost wall-time and disk: use only when the triage
  step needs them, and on the shortest reproducing test.
- A truncated log (no end-of-test marker) is a FAIL regardless of error
  counts — typically a tool crash, license loss, or `$finish` from
  non-UVM code; check the tail via `dv log grep --pattern "xmsim|License"`.

## Coverage
- Functional coverage merges via `dv cov merge`; never hand-edit
  `cov_work`. chkq runs are excluded from merges by policy.
- IMC refinement files are human-owned (see coverage-closure skill).
