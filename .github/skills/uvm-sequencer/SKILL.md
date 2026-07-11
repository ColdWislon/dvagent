---
name: uvm-sequencer
description: >-
  Create the UVM sequencer for an agent on the Xcelium stack. Use whenever the
  user wants to write, add, create, or scaffold a sequencer, the component that
  arbitrates sequences and feeds items to a driver, or a custom sequencer with
  config/reactive handles -- even if the word "skill" is never used. Covers the
  parameterized `uvm_sequencer` typedef and when a real subclass is warranted.
---

# Write a UVM sequencer

The sequencer arbitrates sequences and hands transactions to the driver over the
`seq_item_export`/`seq_item_port` TLM pair. For most agents it is a thin
parameterized `uvm_sequencer #(<proto>_item)` — a distinct class only so the
factory, config handle, and any reactive/response hooks have a home.

## Inputs to confirm
1. Agent/protocol name -> class `<proto>_sequencer`.
2. Item type it serves (`<proto>_item`).
3. Whether it needs a config handle or reactive-response plumbing (usually just
   the typedef).

## Procedure
1. Create `<proto>_sequencer.svh` from `assets/templates/sequencer.svh.tmpl`.
2. Extend `uvm_sequencer #(<proto>_item)`; register with `` `uvm_component_utils``.
3. Keep it minimal: hold a `cfg` handle if the agent config is useful here;
   otherwise the empty subclass is correct and complete.
4. The **agent** builds it only in the active path and connects
   `m_driver.seq_item_port` to `m_sequencer.seq_item_export` (see `uvm-agent`).
5. The **virtual sequencer** stores a handle to this sequencer (`<name>_sqr`),
   null when the agent is passive (see `uvm-vsequence`).

## Hard rules (never violate)
- Extends `uvm_sequencer #(<proto>_item)`; built via the factory.
- Exists only in the active build path of the agent (passive agents have none).
- No stimulus, no pin driving, no checking — it arbitrates, nothing more.
- Do not connect it to the driver here; that wiring lives in the agent's
  `connect_phase`.
- Do not add sequence bodies to the sequencer — sequences are separate classes.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Parameterized on the correct item type and factory-registered.
- [ ] Connected to the driver by the active agent; null on the vsequencer when passive.
- [ ] No stimulus or logic beyond arbitration (plus an optional cfg handle).

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks this.
The `uvm-agent` skill owns the driver-sequencer connection; `uvm-vsequence`
owns the vsequencer handle.
