---
name: uvm-env
description: >-
  Create or assemble a UVM environment conforming to house methodology. Use
  whenever the user wants to write, add, create, scaffold, or build a UVM env,
  a verification environment, the top-level testbench container, or wire agents
  to a scoreboard/coverage/virtual sequencer -- even if the word "skill" is
  never used. Covers component construction from config, TLM connectivity, and
  vertical reuse readiness.
---

# Assemble a UVM environment

The env instantiates agents, scoreboard, coverage and the virtual sequencer,
and wires the analysis paths. It contains no stimulus and no test-specific
logic so it can be reused block -> subsystem -> SoC.

## Inputs to confirm
1. Env name -> class `<proj>_env`.
2. Agents to include and their default active/passive.
3. Scoreboard and coverage collectors present.
4. Virtual sequencer type and its sub-sequencer handles.

## Procedure
1. Create `<proj>_env.sv` (env/ directory, `` `include``d by
   `<proj>_env_pkg.sv`) from `assets/templates/env.svh.tmpl`.
2. In `build_phase`: build every agent, the scoreboard, coverage, and the
   virtual sequencer from the env config object.
3. In `connect_phase`: connect each `agent.ap` to the scoreboard and coverage
   exports, and assign each `vsequencer.<name>_sqr` from
   `<name>_agent.m_sequencer` — null when that agent is passive (the
   generated `<proj>_env.sv` shows the exact pattern).
4. Keep the env free of sequences, delays, and DUT references.

## Hard rules (never violate)
- Extends `uvm_env`; all sub-components built via the factory from config.
- Every monitor analysis port is connected -- no dangling producers/consumers.
- Virtual sequencer holds a handle to every active agent's sequencer.
- No stimulus, no `#` delay, no test-specific behaviour in the env.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] TLM fully connected (every `ap` -> at least one export; no dangling).
- [ ] Virtual sequencer wired to all active agent sequencers.
- [ ] Config-driven and reuse-ready (instantiable at a higher level unchanged).

Structure, phasing, connectivity and deprecation are checked by
`verif-env-review` using the `naming-conventions`, `phasing-check` and
`deprecation-lint` skills.
