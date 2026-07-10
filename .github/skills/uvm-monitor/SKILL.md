---
name: uvm-monitor
description: >-
  Create a UVM monitor conforming to house methodology. Use whenever the user
  wants to write, add, create, or scaffold a monitor, a passive observer, or the
  component that samples DUT pins and reconstructs transactions to broadcast on
  an analysis port -- even if the word "skill" is never used. Covers passive
  sampling, transaction reconstruction, analysis_port publishing, and reset.
---

# Write a UVM monitor

A monitor is passive: it observes the interface, reconstructs transactions, and
publishes them on an analysis port. It never drives and never checks.

## Inputs to confirm
1. Protocol name -> class `<proto>_monitor`.
2. Item type it reconstructs (`<proto>_item`).
3. Virtual interface type and the config object carrying it.
4. Sampling points (clock edge, valid/ready handshake, transaction boundaries).

## Procedure
1. Create `<proto>_monitor.sv` (`.sv` in this infra) from `assets/templates/monitor.svh.tmpl`.
2. Declare `uvm_analysis_port#(<proto>_item) ap` and construct it.
3. Get the virtual interface from the config object in `build_phase`.
4. In `run_phase`, sample under a reset guard, reconstruct each transaction, and
   `ap.write(tr)`.

## Hard rules (never violate)
- Extends `uvm_monitor`; declares one `uvm_analysis_port`.
- Never drives any signal; observation only.
- No checking / scoreboard logic and no covergroups inside the monitor.
- Reset-aware: discards partial transactions on reset.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Reconstructs correct transactions from pin activity.
- [ ] Publishes every completed transaction on `ap`.
- [ ] Passive under reset (no partial/spurious transactions emitted).

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks this.
