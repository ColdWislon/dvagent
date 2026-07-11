---
name: uvm-interface
description: >-
  Create the SystemVerilog interface for a UVM agent on the Xcelium stack. Use
  whenever the user wants to write, add, create, or scaffold an interface, an
  `if`, the signal/pin bundle for a protocol, clocking blocks, or modports that
  a driver and monitor sample and drive -- even if the word "skill" is never
  used. Covers clock/reset ports, driver/monitor clocking blocks, and where
  interface assertions live.
---

# Write a SystemVerilog interface

The interface is the signal-level contract between the DUT and one agent. The
driver drives it and the monitor samples it, both through a *virtual* interface
handle carried in the agent config object — never a hierarchical path. Timing is
expressed with clocking blocks so the TB is race-free against the DUT.

## Inputs to confirm
1. Agent/protocol name -> interface `<proto>_if`.
2. Clock and reset ports (names, active level) — passed in from `tb_top`.
3. The protocol signals (direction from the DUT's point of view).
4. Which signals the driver drives vs. only samples.

## Procedure
1. Create `<proto>_if.sv` from `assets/templates/if.sv.tmpl` (an interface is a
   compile-unit item, so it is `.sv`, not `` `include``d into a package).
2. Declare `clk`/`rst_n` as `input` ports; declare the protocol signals as plain
   `logic` members inside the interface.
3. Add a **driver clocking block** (`drv_cb`) — `output` on signals the TB
   drives, `input` on signals it samples — and a **monitor clocking block**
   (`mon_cb`) with every signal as `input`.
4. Optionally add `modport`s (e.g. `drv_mp`, `mon_mp`) that expose the matching
   clocking block; keep raw asynchronous access out of the drive/sample paths.
5. Put protocol assertions / interface checkers here (or in a `bind`ed module)
   as the protocol matures — they belong with the signals, not in the driver.

## Hard rules (never violate)
- All driver access to signals goes through `drv_cb`; all monitor access through
  `mon_cb` — no bare combinational reads/writes of the protocol signals from the
  TB (prevents races with the DUT).
- The interface holds no stimulus and no scoreboarding — timing and assertions
  only.
- Clock and reset arrive as ports from `tb_top`; the interface never generates
  them.
- Signal widths/parameters are set once (parameter or `tb_top` binding), not
  duplicated across driver and monitor.
- Delivered to components as a `virtual <proto>_if` via the config object, set
  once in `tb_top`; never fetched by hierarchical name.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Driver and monitor clocking blocks present with correct directions.
- [ ] Every protocol signal appears in `mon_cb`; driven signals appear in `drv_cb`.
- [ ] Reset port present; no signal driven to X off reset by the interface.
- [ ] Instantiated in `tb_top` and published to the test as a `virtual <proto>_if`.

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks the
interface and its `tb_top` wiring (TB-top axis).
