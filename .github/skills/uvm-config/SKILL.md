---
name: uvm-config
description: >-
  Create UVM configuration objects and apply config_db discipline per house
  methodology. Use whenever the user wants to write, add, create, or scaffold a
  config object, agent/env configuration, carry a virtual interface into the
  testbench, or set/get values through config_db -- even if the word "skill" is
  never used. Covers config-object structure, virtual-interface delivery, and
  scoped set/get conventions.
---

# Write a UVM config object

Config objects carry knobs and the virtual interface handle into components.
Team model: configuration is NESTED -- the env config contains the agent
configs -- and is assembled and set ONCE at test level. The interface enters
the testbench once (at the top) and reaches driver/monitor through the agent
config -- not via ad-hoc `config_db` interface lookups. `config_db` reads
happen in `build_phase` and are cached in fields, never in run-time hot paths.
Plusargs are parsed in the test/config layer only, never scattered in
components.

## Inputs to confirm
1. Scope -> class `<x>_agent_cfg` or `<proj>_env_cfg`.
2. Knobs to expose (active/passive, modes, injection rates).
3. Virtual interface type carried by the (agent) config.

## Procedure
1. Create `<x>_cfg.svh` from `assets/templates/config.svh.tmpl`.
2. Extend `uvm_object`, register with `` `uvm_object_utils ``, expose knobs (some
   `rand`) and the `virtual <proto>_if vif` handle.
3. Nest: the env config holds the agent configs; the test builds the env
   config once, sets interfaces into the nested agent configs, and does one
   scoped `config_db::set`; the env distributes sub-configs to its agents.
4. In the agent (and its driver/monitor) `get` the config in `build_phase`.

## Hard rules (never violate)
- Config is a `uvm_object` with `` `uvm_object_utils ``; data only, no components.
- The virtual interface travels inside the config object, retrieved once.
- Nested model: env cfg contains agent cfgs; assembled and set once at test
  level (team standard); every mandatory `get` checked with `uvm_fatal`.
- `config_db` keys are scoped to the target subtree, never global `"*"`.
- No logic in the config beyond defaults and simple helpers.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Interface set at top and reaches driver/monitor via the config.
- [ ] Values typed and scoped; no unscoped `"*"` sets.
- [ ] Consumers `get` the config in `build_phase` with a fatal on absence.

Naming and deprecation rules (including legacy `set/get_config_*`) are enforced
by the `naming-conventions` and `deprecation-lint` skills.
