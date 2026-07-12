---
name: dut-integration
description: >-
  Wire an existing uvm-gen environment's tb_top to the real DUT RTL: read the
  DUT module's port list, connect each port to a generated interface signal
  (extending interfaces where the RTL has signals not yet modeled) or to
  clk/rst_n, and tie off anything left over with a justification comment. Use
  whenever the user wants to connect, wire, hook up, instantiate, or bind the
  DUT, fill tb_top TODO(connect-dut) markers, or make `make compile` pass
  against real RTL instead of the generated stub -- even if the word "skill"
  is never used. Not for creating new environments, agents, or interfaces
  from scratch (that's uvm-env / uvm-agent / dv-env-architect).
---

# Connect tb_top to the real DUT

uvm-gen deliberately does not parse RTL: every generated `tb_top.sv`
instantiates the DUT by module name only, with port connections left as
`// TODO(connect-dut)`, compiling against a generated stub in the meantime.
This skill is the deterministic follow-up: given an environment that already
exists, make its ports real.

## Inputs to confirm

1. The env root (`<ip>_verif/`) and its active config: `dut.module` and
   `dut.rtl_filelist` from `cfg/<config>.yaml` (relative paths resolve
   against that YAML's directory; the value may itself use `-f` includes).
2. `tb/<ip>_tb_top.sv` — the `dut` instantiation and its
   `// TODO(connect-dut)` block.
3. Every `agents/<name>_agent/<ip>_<name>_if.sv` — the interfaces already
   instantiated in tb_top, each currently carrying only the generic
   valid/data stub signals uvm-gen seeds them with.

## Procedure

1. **Read the RTL directly** to get the exact port list of `dut.module` —
   open the file(s) named by `dut.rtl_filelist` (following any `-f`
   includes) and read the module declaration. No separate parser: this is a
   one-shot read per session, and heuristic port-list scripts misparse
   `generate` blocks, macros, and multi-line ANSI ports often enough not to
   be worth maintaining for a task an agent can just read correctly.
2. **Match each port to an owner**:
   - `clk`/reset-like ports → tb_top's `clk`/`rst_n`.
   - A port that clearly belongs to one of the custom interfaces (name/width
     matches, or matches the protocol the interface's agent was written
     for) → extend that interface's signal list (and its `drv_cb`/`mon_cb`
     clocking blocks) to carry the real signal, replacing the generic
     `valid`/`data` stand-ins as they're subsumed. Keep driver/monitor
     signal names in sync in the same pass — a port connected to a signal
     the driver/monitor don't yet reference is only half done.
   - A port belonging to a Cadence VIP (`vip/<name>_vip/`) → leave it to the
     VIP wrapper's own TODO(vip) markers; do not model it as a custom
     interface.
   - A port that matches no agent/VIP (test modes, DFT, tie-offs, unused
     straps) → tie it off directly in the instantiation with a one-line
     comment stating why (e.g. `.scan_en(1'b0), // DFT, unused in functional sim`).
3. **Ambiguous mapping → stop and ask.** If a port's owner isn't reasonably
   inferable from its name/width against the existing interfaces, do not
   guess a mapping into existence — surface the port list and ask which
   interface (or "new interface", which is out of this skill's scope and
   routes to `uvm-agent`/dv-env-architect instead).
4. **Confirm the real RTL is what compiles.** Once `dut.rtl_filelist`
   resolves, `sim/Makefile` switches off the generated stub automatically
   (no edits needed there) — the compile log's "generated DUT stub" note
   disappearing is the signal that real RTL was actually used, not a name
   collision with a from-nowhere module.
5. **Prove it**: `make compile` (from `<ip>_verif/sim/`).

## Hard rules (never violate)

- RTL is read-only, same as everywhere in this repo — this skill only ever
  reads `dut.rtl_filelist`, never edits a file under it.
- Never invent a DUT port, and never comment out or drop a real one to make
  elaboration pass.
- Every DUT port ends up in exactly one of: connected to an interface
  signal, connected to `clk`/`rst_n`, or explicitly tied off with a
  justification comment. Zero unaccounted ports, zero leftover
  `// TODO(connect-dut)` markers when done.
- Extending an interface stays inside the vertical-reuse contract the
  generated agent already follows: signals live in the interface file, the
  virtual interface handle stays inside `<ip>_<name>_agent_cfg` — never add
  a hierarchical `uvm_config_db` vif lookup or a `tb_top`-hierarchy
  reference while doing this.
- This skill does not create new interfaces, agents, or VIP wrappers for
  ports that need one — that is `uvm-agent` / `uvm-config` / dv-env-architect
  territory; flag the gap instead of quietly inventing structure.

## Definition of Done

- [ ] `make compile` (wrapper: `dv compile <ip>`) is clean — zero errors —
      and its log carries no "generated DUT stub" note.
- [ ] Zero `// TODO(connect-dut)` markers remain in `tb_top.sv`.
- [ ] Every DUT port is connected or explicitly tied off with a reason;
      the port-mapping table in the session report accounts for all of them.
- [ ] Interfaces that gained real signals still expose only `drv_cb`/`mon_cb`
      clocking blocks and a plain signal list — no config_db/hierarchy leaks
      introduced.

Naming, phasing and deprecation rules are enforced by the
`naming-conventions`, `phasing-check` and `deprecation-lint` skills; the
`xcelium-flow` skill covers reading the resulting compile/elab errors.
