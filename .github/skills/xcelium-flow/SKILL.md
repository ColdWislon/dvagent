---
name: xcelium-flow
description: Cadence Xcelium/IMC flow specifics — dv command usage, common compile/elab error patterns, and environment rules. Use when interpreting tool errors or running the flow.
---

# Xcelium Flow Notes

## Flow rules
- All tool access goes through the generated `sim/Makefile` (uvm-gen
  environments: single-step `xrun -uvmhome CDNS-1.2`, one `-f` per
  filelist domain) — or the team's `dv` wrapper where one is layered on
  top. Never invoke `xrun`, `imc`, or vManager ad hoc; never read raw
  logs wholesale (use `log-triage/scripts/triage_log.py` / targeted grep,
  or `dv log first-error` with a wrapper).
- Work libraries are per configuration (`sim/xcelium.d_<config>`, from
  `-xmlibdirname`). On snapshot/library mismatch the fix is
  `make clean` (or `dv compile <ip> --clean`), not editing library paths.
  UVM comes bundled with Xcelium (`-uvmhome CDNS-1.2`); Cadence VIP
  compiles via `$CDN_VIP_ROOT` in `sim/vip_<protocol>.f` only.
- chkq negative tests need write access: run them with
  `XRUN_OPTS='-access +rwc'` (wrapper: dedicated chkq build config); do
  not add global access flags to functional runs — `make waves` already
  implies `-access +rwc` for debug.

## Reading common error patterns
- `xmvlog: *E,...` = compile (syntax/type) — fix at file:line in verdict.
- `xmelab: *E,CUVUNF/CUVMUR` (unresolved/undriven) = missing file in the
  compile list or wrong package import order — check `sim/tb.f` (compile
  order: interfaces -> agent pkgs -> env pkg -> seq pkg -> test pkg ->
  tb_top) and `sim/dut.f` before editing code.
- `xmelab: *E,ICDCBA` and friends on bind/interface = port/param mismatch
  between TB harness and DUT — read the DUT port list, don't guess.
- `TYCMPAT` = SystemVerilog type check — fix the type, never cast around
  it without understanding why.
- Elab succeeds but time-0 `UVM_FATAL` (config/factory/null vif) = TB
  wiring, see debug playbook — not a compile problem, don't recompile in
  a loop.

## Simulation behavior
- Seeds come from `make run SEED=<n>` (`xrun -svseed`) and are recorded in
  the `[UVM_GEN_CFG]` banner context / `verif_matrix.yaml` record (wrapper:
  `dv sim --seed`, verdict field); reproduction REQUIRES the same seed and
  same configuration (`CFG=`).
- Waves (`make waves` / `--waves`) cost wall-time and disk: use only when
  the triage step needs them, and on the shortest reproducing test.
- A truncated log (no UVM report summary / no `** UVM TEST PASSED **`
  marker) is a FAIL regardless of error counts — typically a tool crash,
  license loss, or `$finish` from non-UVM code; check the log tail
  (`grep -E "xmsim|License" sim/logs/<log> | tail`).

## Coverage
- A coverage flow (IMC merge/report) is not wired into the generated
  Makefile by default — when the site adds one (or `dv cov merge`
  exists), never hand-edit `cov_work`, and chkq runs stay excluded from
  merges by policy. Until then, state that coverage evidence is
  unavailable rather than improvising IMC calls.
- IMC refinement files are human-owned (see coverage-closure skill).
