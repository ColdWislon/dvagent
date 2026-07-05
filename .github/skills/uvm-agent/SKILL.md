---
name: uvm-agent
description: >-
  Create a UVM agent conforming to house methodology. Use whenever the user
  wants to write, add, create, or scaffold an agent, a UVC, or the container
  that bundles a driver, monitor, sequencer and config for one interface -- even
  if the word "skill" is never used. Covers active/passive construction from
  config, sequencer-driver connection, and analysis-port exposure.
---

# Write a UVM agent

An agent encapsulates one interface: monitor (always), plus sequencer + driver
when active. Active/passive is decided by config, never hard-coded.

## Inputs to confirm
1. Protocol name -> class `<proto>_agent`.
2. Item type and the config object type (`<proto>_agent_cfg`).
3. Default active/passive.

## Procedure
1. Create `<proto>_agent.svh` from `assets/templates/agent.svh.tmpl`.
2. In `build_phase`: get the config object, always build the monitor; build the
   sequencer and driver only when `get_is_active() == UVM_ACTIVE`.
3. In `connect_phase`: when active, connect
   `m_driver.seq_item_port` to `m_sequencer.seq_item_export`; expose the
   monitor's analysis port through the agent's `ap`.

## Hard rules (never violate)
- Extends `uvm_agent`; active/passive read from config via `get_is_active()`.
- Sequencer and driver exist only in the active build path.
- Monitor is always built (passive agents still observe).
- No stimulus and no checking inside the agent.

## Definition of Done
- [ ] `dv compile <ip>` verdict clean (never call xrun directly).
- [ ] Active build creates driver + monitor + sequencer and connects them.
- [ ] Passive build creates the monitor only.
- [ ] Agent `ap` forwards the monitor's transactions; behaviour is config-driven.

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks this.
