---
name: uvm-driver
description: >-
  Create a UVM driver conforming to house methodology on the Xcelium stack. Use
  whenever the user wants to write, add, create, or scaffold a driver, pin-level
  BFM behaviour, or the component that pulls items from a sequencer and drives
  the DUT interface -- even if the word "skill" is never used. Covers the
  get_next_item/item_done handshake, virtual-interface drive, and reset handling.
---

# Write a UVM driver

A driver pulls transactions from its sequencer and drives them onto pins through
a virtual interface. It contains no checking and no coverage.

## Inputs to confirm
1. Protocol name -> class `<proto>_driver`.
2. Item type it drives (`<proto>_item`) and whether a response is returned.
3. Virtual interface type and the config object it comes from.
4. Reset semantics (active level, mid-transaction abort behaviour).

## Procedure
1. Create `<proto>_driver.svh` from `assets/templates/driver.svh.tmpl`.
2. Get the virtual interface from the config object in `build_phase` (fatal if
   absent). Never `config_db::get` the raw interface if it is carried in config.
3. In `run_phase`, run the drive loop under a reset guard: `get_next_item(req)`
   -> `drive(req)` -> `item_done()` (or `item_done(rsp)` for a response).
4. On reset, drop drive to the idle/inactive state and resynchronise.

## Hard rules (never violate)
- Extends `uvm_driver#(<proto>_item[, <proto>_rsp])`.
- Every `get_next_item` is matched by exactly one `item_done`.
- Drive only through the virtual interface; no DUT hierarchy references.
- No `` `uvm_error ``-style checking, no covergroups -- that is the monitor /
  scoreboard / coverage collector's job.
- Handle reset explicitly; do not drive X onto controlled signals off reset.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Handshake balanced (no sequencer stalls, no double `item_done`).
- [ ] Reset-clean: idles on reset, resumes correctly after.
- [ ] Pins driven to defined values out of reset.

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks this.
