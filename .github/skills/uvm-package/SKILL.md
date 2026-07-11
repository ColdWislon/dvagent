---
name: uvm-package
description: >-
  Create the SystemVerilog packages that hold a UVM environment together on the
  Xcelium stack. Use whenever the user wants to write, add, create, or scaffold
  a package, a `_pkg.sv`, the agent/env/seq_lib/test package, the include order,
  or fix a compile-order / "type not found" / double-compile error -- even if
  the word "skill" is never used. Covers package boundaries, import vs include,
  and the layered compile order.
---

# Write the environment packages

Every class-based layer of the environment compiles inside a package: one per
agent, one for the env, one for the virtual-sequence library, one for the tests.
Packages give clean namespacing (everything `<proj>_`-prefixed) and vertical
reuse (an agent package drops into an SoC compile unchanged). The interface and
`tb_top` are the only compile-unit-scope items — they live outside packages.

## Inputs to confirm
1. Which package -> `<proto>_agent_pkg`, `<proj>_env_pkg`, `<proj>_seq_lib_pkg`,
   or `<proj>_test_pkg`.
2. The peer packages it imports and the files it `` `include``s.
3. The intended compile order (agent -> env -> seq_lib -> test -> tb).

## Procedure
1. Create `<name>_pkg.sv` from `assets/templates/pkg.sv.tmpl` (a package is a
   compile-unit item -> `.sv`, listed in the compile filelist, not
   `` `include``d elsewhere).
2. First line inside: `import uvm_pkg::*;` then `` `include "uvm_macros.svh" ``.
3. `import` peer packages by `::*` (agent packages into env; env + agent + seq_lib
   into test) — never `` `include`` another package's source files.
4. `` `include`` this package's OWN class files, in dependency order: item ->
   cfg -> sequencer -> driver -> monitor -> agent -> base_seq (agent pkg);
   reg_block -> reg_adapter -> env_cfg -> scoreboard -> coverage -> vsequencer ->
   env (env pkg).
5. Wrap the whole file in an `` `ifndef <NAME>_PKG_SV `` include guard.

## Package boundaries (house layering)
- `<proto>_agent_pkg` — self-contained: item, cfg, sequencer, driver, monitor,
  agent, base sequence. NO reference to any testbench hierarchy (reuse-ready).
- `<proj>_env_pkg` — imports every agent pkg (+ VIP pkgs); includes reg model,
  env cfg, scoreboard, coverage, vsequencer, env.
- `<proj>_seq_lib_pkg` — imports agent pkgs + env pkg; includes the virtual
  sequences.
- `<proj>_test_pkg` — imports agent pkgs + env pkg + seq_lib pkg; includes the
  tests. This is what `tb_top` imports.

## Hard rules (never violate)
- Cross-package sharing is by `import`, never by `` `include``ing another
  package's `.sv` (double-compile / duplicate-type errors otherwise).
- A file is `` `include``d in exactly one package — no source file compiled twice.
- Include order respects dependencies (a type is defined before it is used).
- Agent packages have zero testbench-hierarchy references (vertical reuse).
- The interface and `tb_top` are NOT inside any package; they are compile-unit
  scope and listed directly in the filelist.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] No "type not found" / forward-reference errors (include order correct).
- [ ] No duplicate-definition errors (each file included once; peers imported).
- [ ] Agent package imports nothing from env/test (reuse boundary intact).
- [ ] Package listed in the compile filelist in dependency order (agent->env->seq->test).

Naming, phasing and deprecation rules are enforced by the `naming-conventions`,
`phasing-check` and `deprecation-lint` skills; `verif-env-review` checks the
build/compile-order axis. Vertical-reuse boundaries are detailed in
`vertical-reuse`.
