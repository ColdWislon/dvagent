---
name: uvm-test
description: >-
  Author a new UVM test class that conforms to house verification methodology
  on the Cadence Xcelium / vManager / IMC stack. Use this whenever the user
  wants to write, add, create, or scaffold a UVM test, a new test scenario, a
  directed or constrained-random test, wants to extend the project base test,
  or add a test to the vsif / regression -- even if the word "skill" is never
  used. Covers class structure, factory registration, phasing, objections,
  virtual-sequence launch, config_db and factory-override conventions, vPlan
  traceability tagging, vsif and filelist registration, and the test
  Definition of Done.
---

# Write a UVM test

This skill produces one methodology-compliant UVM **test** class and wires it
into the build and regression flow. A test has exactly two jobs: (1) select and
configure the environment via `config_db` and factory overrides, and (2) launch
one virtual sequence under objection. Everything structural -- env, agents,
scoreboard, reporting, drain time -- belongs to the **base test** and is
inherited. The test never rebuilds it.

## Inputs to confirm before writing

Gather these from the conversation, or ask. Do not invent them.

1. **Feature / scenario name** -> drives the class name `<feat>_test`.
2. **Base test** to extend (default: the project base test, e.g. `<proj>_base_test`).
3. **Virtual sequence** to launch (an existing `<feat>_vseq`, or flag that it
   must be created first -- that is the `uvm-vseq` skill, not this one).
4. **Knobs**: the `config_db` values or factory overrides this test needs
   (error injection, mode selects, agent active/passive, alternate sequence).
5. **vPlan feature ID** for the traceability tag.

If the virtual sequence does not exist yet, stop and say so. A test with no
sequence to run is not useful -- create the vseq first.

## Procedure

1. Create `<feat>_test.svh` under `tb/tests/` from
   `assets/templates/test.svh.tmpl`, substituting the names above.
2. Fill `build_phase`: call `super.build_phase(phase)` **first**, then only the
   `config_db::set` calls and the `type_id::set_type_override` /
   `set_inst_override` this test requires. Do **not** construct the env here.
3. Fill `run_phase`: create the vseq via the factory (`::type_id::create`),
   raise one objection, configure and `randomize()` the vseq (fatal on
   failure), `start()` it on the base env's virtual-sequencer handle, drop the
   objection. Nothing else.
4. Add a `// VP-xxx` tag on the class so the vPlan / coverage
   tooling can resolve the link.
5. Register the file: add it to the compile filelist (`tb/compile.f` or the
   tests `.f`) and add a test entry to the vsif so it appears in vManager.
6. Verify against the **Definition of Done** below before declaring done.

The house rules, the deprecations to avoid, and the exact config_db / override
conventions live in `references/patterns.md`. Read it before writing if
anything above is ambiguous.

## Hard rules (never violate)

- Extend the project **base test**, never `uvm_test` directly.
- `` `uvm_component_utils(<feat>_test) `` registration is mandatory.
- `super.build_phase(phase)` is the first statement in `build_phase`.
- Exactly one `raise_objection` / `drop_objection` pair, symmetric, around the
  scenario.
- Launch the sequence with `vseq.start(<vsequencer>)`; create it with the
  factory, never `new()`.
- No `#` delays anywhere in a test -- timing lives in the driver / interface.
- No `run_test()` call inside a test; selection is via `+UVM_TESTNAME` / vsif.
- Drain time is set in the base test, not per-test.

## Definition of Done

- [ ] Compile clean (`make compile`; wrapper: `dv compile <ip>`); zero new warnings vs baseline — never invoke xrun ad hoc.
- [ ] Lints clean against the house ruleset.
- [ ] Registered in the vsif and visible in a vManager session.
- [ ] `// VP-xxx` tag present and resolves to a real vPlan feature.
- [ ] Passing sim verdicts on >=3 listed seeds (`make run TEST=<t> SEED=<n>`;
      wrapper: `dv sim`): 0 `UVM_ERROR`/`UVM_FATAL`, `** UVM TEST PASSED **`
      marker present, zero new `UVM_WARNING`s vs. baseline.
- [ ] Factory `create` used for the vseq and any overridable component
      (no direct `new`).
- [ ] No `#` delays; exactly one symmetric objection pair.

## Dev loop (single test)

All tool access goes through the environment's `sim/Makefile` (or the
team `dv` wrapper where one exists — see the `dv-wrapper` skill):

```bash
cd <ip>_verif/sim
make compile
make run TEST=<feat>_test SEED=<N>     # exit status + record_result PASS/FAIL
                                       # + verif_matrix.yaml record = the verdict
python3 ../../.github/skills/log-triage/scripts/triage_log.py results/<config>/<log>
# wrapper equivalents: dv compile <ip> / dv sim ... --seed N / dv log first-error
```

A pass means `uvm_fatal == 0 && uvm_error == 0`, end-of-test marker present,
and zero new `UVM_WARNING`s vs. baseline. Regression entry (vsif file edit)
and coverage merge are handled by CI once the test is registered -- see
`references/patterns.md` for the vsif snippet (the vsif is a repo file the
flow consumes; agents edit the file, never drive vManager).
