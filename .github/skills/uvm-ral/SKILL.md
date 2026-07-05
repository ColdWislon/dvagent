---
name: uvm-ral
description: >-
  Create or integrate a UVM register model (RAL) per house methodology. Use
  whenever the user wants to write, add, create, scaffold, or wire a register
  model, uvm_reg_block, register abstraction layer, reg adapter, predictor, or
  run register tests -- even if the word "skill" is never used. Covers reg
  block/adapter/predictor structure, frontdoor/backdoor, and built-in reg tests.
---

# Build or integrate a UVM register model

RAL gives an abstract, reusable view of the register map: a `uvm_reg_block`, a
bus adapter, and a predictor that keeps the mirror in step with observed bus
traffic. Prefer generating the block from the register source (IP-XACT / RDL);
hand-write only small maps.

## Inputs to confirm
1. Register source: IP-XACT / SystemRDL / spec -> generator or manual.
2. Bus protocol for the adapter (`reg2bus` / `bus2reg`).
3. Backdoor availability (HDL paths) for `peek`/`poke` and backdoor tests.
4. Prediction mode: explicit predictor (preferred) vs auto-predict.

## Procedure
1. Generate/create the `uvm_reg_block` (registers, fields, map, offsets, access,
   reset). Use `assets/templates/ral_block.svh.tmpl` as the shape.
2. Create the adapter (`uvm_reg_adapter`: `reg2bus` / `bus2reg`) from
   `assets/templates/ral_adapter.svh.tmpl`.
3. In the env: `reg_map.set_sequencer(bus_sequencer, adapter)`, instantiate a
   `uvm_reg_predictor#(BUS_ITEM)`, set `predictor.map`/`predictor.adapter`, and
   connect `bus_monitor.ap` to `predictor.bus_in`. Disable auto-predict when
   using the predictor.
4. Set HDL paths for backdoor; run built-in reg sequences (`hw_reset`,
   `bit_bash`) to smoke-test the model.

## Hard rules (never violate)
- Model built from register source where possible; generated maps not
  hand-edited.
- Exactly one prediction mechanism: predictor **or** auto-predict, not both.
- Adapter is the only place that translates reg <-> bus.
- Backdoor via `hdl_path`, never string-poked ad hoc.

## Definition of Done
- [ ] `dv compile <ip>` verdict clean (never call xrun directly).
- [ ] Adapter round-trips (read-after-write via frontdoor matches).
- [ ] Predictor updates the mirror from observed bus traffic.
- [ ] Built-in `hw_reset` and `bit_bash` sequences pass.

Naming and deprecation rules are enforced by the `naming-conventions` and
`deprecation-lint` skills; `verif-env-review` checks predictor/adapter wiring.
