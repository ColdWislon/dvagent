---
name: uvm-tb-top
description: >-
  Create the top-level testbench module that boots a UVM environment on the
  Xcelium stack. Use whenever the user wants to write, add, create, or scaffold
  a tb_top, testbench top, the HDL top module, clock/reset generation, DUT +
  interface instantiation, virtual-interface publishing, or the `run_test()`
  bootstrap -- even if the word "skill" is never used. Covers the static HDL
  world where the class-based UVM world is launched from.
---

# Write the testbench top

`tb_top` is the one static SystemVerilog module the simulator elaborates. It
generates clock and reset, instantiates the interfaces and the DUT and wires
them together, publishes each virtual interface into the config_db for the test,
and calls `run_test()`. It is the boundary between the HDL world and the UVM
class world.

## Inputs to confirm
1. IP/env name -> module `<proj>_tb_top`.
2. Test package to import (`<proj>_test_pkg`).
3. Agents present -> one interface instance each, and the config_db key each
   test expects (e.g. `<proto>_vif`).
4. DUT module name and clock period / reset length.

## Procedure
1. Create `<proj>_tb_top.sv` from `assets/templates/tb_top.sv.tmpl`.
2. Import `uvm_pkg`, `` `include "uvm_macros.svh" ``, and import
   `<proj>_test_pkg` (which transitively pulls the env and agent packages).
3. Generate `clk` (a `forever` toggle) and `rst_n` (asserted then released after
   N clocks) in `initial` blocks.
4. Instantiate one `<proto>_if` per agent, connecting `.clk`/`.rst_n`; leave a
   VIP-interface TODO where a Cadence VIP is used.
5. Instantiate the DUT; leave port connections as an explicit
   `// TODO(connect-dut)` block — `tb_top` does not parse RTL, so DUT wiring is
   the DUT-integration step, not env generation.
6. In a final `initial` block: `uvm_config_db#(virtual <proto>_if)::set(null,
   "uvm_test_top", "<proto>_vif", <proto>_if_i)` for every agent, then
   `run_test()` (no default test — the plusarg `+UVM_TESTNAME` / `make run
   TEST=...` selects it).

## Hard rules (never violate)
- The ONLY place virtual interfaces enter the config_db — set on scope
  `"uvm_test_top"` so the test forwards them into the env config; components
  never `config_db::get` a raw interface by hierarchical path.
- No UVM components, no scoreboarding, no stimulus in `tb_top` — it is static HDL
  plus the `run_test()` call.
- `run_test()` is called exactly once, with no hard-coded default test name.
- Clock and reset are generated here and nowhere else; every interface takes them
  as ports.
- DUT ports are wired in the DUT-integration step, not invented here — leave the
  `TODO(connect-dut)` block and let it fail loud until connected.

## Definition of Done
- [ ] Compile/elaborate clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Clock toggles and reset asserts-then-releases before stimulus.
- [ ] One interface per agent instantiated and clk/rst_n connected.
- [ ] Every agent's virtual interface published to `uvm_test_top` in the config_db.
- [ ] `run_test()` present once; test chosen by `+UVM_TESTNAME` (no default baked in).

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` audits `tb_top`
directly (its TB-top axis). DUT port wiring is owned by the `dut-integration`
skill / `dv-dut-integrator` agent.
