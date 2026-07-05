# Testbench-code review (verif-env-review, axis 1)

The `testbench_code` axis of `verif-env-review`. Applies to the UVM class library
(components, sequences, config, RAL). Reuse the three law skills' rulesets
verbatim -- do not invent new severities. Emit findings in the shared schema;
they roll up as this axis.

## Passes
1. **Structural** — inventory components. The env must assemble agents,
   scoreboard, coverage and a virtual sequencer; agents follow the driver /
   monitor / sequencer / config shape; each component is factory-registered.
2. **Naming** — apply `naming-conventions`.
3. **Phasing & objections** — apply `phasing-check`.
4. **Deprecation & anti-patterns** — apply `deprecation-lint`; run
   `deprecation-lint/scripts/lint.py` for the mechanical subset.
5. **TLM connectivity** — every monitor `ap` connects to at least one export; no
   dangling producers or consumers; the virtual sequencer holds a handle to
   every active agent's sequencer.
6. **Factory & config** — overridable objects built with `create`, not `new`;
   `is_active` and the virtual interface delivered through config, not ad-hoc
   `config_db` interface lookups; `config_db` scopes are not global `"*"`.
7. **Reuse readiness** — no stimulus, delays, or DUT references in env/agents;
   parameterisation sane; instantiable at a higher level unchanged.
8. **Checking independence** — covergroups present and `VP-xxx`-referenced;
   scoreboard performs real compares with residual checks (no zero-traffic false
   pass); expected values originate from an input monitor (or an independent
   reference model), never from the sequence item, stimulus knobs, or
   `config_db` read as golden. Flag any driver->scoreboard connection or
   scoreboard dependency on a sequence / stimulus class.

## Finding schema (rolls up to the testbench_code axis)
```json
{ "axis": "testbench_code", "rule_id": "tlm.dangling_ap", "severity": "error",
  "file": "env/foo_env.svh", "line": 42,
  "message": "m_slave_agent.ap not connected",
  "fix": "connect ap to a scoreboard/coverage export in connect_phase" }
```
