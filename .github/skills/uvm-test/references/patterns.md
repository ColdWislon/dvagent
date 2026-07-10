# uvm-test — patterns, conventions, and anti-patterns

Loaded on demand from `SKILL.md`. Read the section you need; do not paste the
whole file into a test.

**Contents**
1. Canonical test (annotated)
2. `config_db` conventions
3. Factory-override conventions
4. Objections and phasing
5. Messaging
6. Anti-patterns and deprecations (deprecation-lint will flag these)
7. vsif / vManager registration
8. Traceability

> Handle names below (`env`, `vsequencer` — the uvm-gen shape) are the
> house convention. Match the
> actual handle names exposed by the project base env.

---

## 1. Canonical test (annotated)

```systemverilog
class <feat>_test extends <proj>_base_test;   // [1] base owns env/cfg/reporting
  `uvm_component_utils(<feat>_test)           // [2] factory registration

  function new(string name = "<feat>_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);                 // [3] first statement, always
    // config_db sets + factory overrides for THIS test only  [4]
  endfunction

  virtual task run_phase(uvm_phase phase);
    <feat>_vseq vseq;
    vseq = <feat>_vseq::type_id::create("vseq");        // [5] factory, not new()
    phase.raise_objection(this, "<feat>_test: start");  // [6] one raise ...
    if (!vseq.randomize())                              // [7] fatal on fail
      `uvm_fatal(get_type_name(), "vseq randomization failed")
    vseq.start(env.vsequencer);                         // [8] launch on vseqr
    phase.drop_objection(this, "<feat>_test: done");    // [6] ... one drop
  endtask
endclass
```

- **[1]** Extending the base test is what gives you the env, config object,
  drain time and report catcher for free. Extending `uvm_test` re-invents all
  of it and diverges from every other test.
- **[3]** Parent `build_phase` runs before children, so any `config_db::set`
  you place *after* `super.build_phase` still lands before the child components
  build. But the `super` call must come first so the env exists.
- **[8]** The virtual sequencer is owned by the env, not the test. The test only
  holds a handle to it through the base env.

---

## 2. `config_db` conventions

- Scope keys to the smallest subtree that needs the value:
  `uvm_config_db#(int)::set(this, "env.<name>_agent", "is_active", UVM_ACTIVE);`
  Prefer that over a global `"*"` scope, which leaks into unrelated components.
- Set in `build_phase`, after `super.build_phase`. Do not `get` in the test what
  the base already provides through the config object.
- Keep values typed. Avoid stringly-typed knobs that bypass compile checking.

---

## 3. Factory-override conventions

- Override the *type*, not a hand-built object, so higher-level (subsystem / SoC)
  envs can re-override on top of you:
  `<base_seq>::type_id::set_type_override(<feat>_seq::get_type());`
- Use `set_inst_override` when the swap must apply to one path only.
- Everything overridable is built with `::type_id::create`. A `new()` freezes
  the type and defeats the factory.

---

## 4. Objections and phasing

- Exactly one raise / drop pair per test, symmetric, in `run_phase`.
- Drain time belongs to the base test (`set_drain_time` in the base). Do not set
  it per-test.
- Do not spread objections across phases unless the base defines a run-time
  phase schedule; if it does, raise and drop inside the matching phase.
- No `#` delays in a test. Timing lives in the driver / interface; use sequence
  timing, events, or phase objections instead.

---

## 5. Messaging

- Info messages: `get_type_name()` as ID (or house scheme) so log filtering by
  component works. Check messages (in checkers): one STABLE unique ID per
  check (`SCBD_*`), never `get_type_name()` -- chkq and triage key on them.
- Test-level milestones at `UVM_LOW`; debug detail at `UVM_HIGH` / `UVM_DEBUG`.
- `` `uvm_fatal `` on `randomize()` failure. Functional mismatches are
  `` `uvm_error `` and normally live in the scoreboard, not the test.

---

## 6. Anti-patterns and deprecations (deprecation-lint will flag these)

| Anti-pattern | Fix |
|---|---|
| `extends uvm_test` | `extends <proj>_base_test` |
| `new()` for a seq / component | `::type_id::create` |
| `` `uvm_do `` / `` `uvm_do_with `` | explicit `create` + `start` (house style); reserve macros for legacy code only |
| `starting_phase = ...` | `get_starting_phase()` / `set_starting_phase()` |
| `#100ns` inside a test | move timing to driver / interface; use events / objections |
| `run_test()` inside a test | remove; select via `+UVM_TESTNAME` / vsif |
| rebuilding the env in the test | inherit from base; the test only configures |
| asymmetric objections | one raise, one drop, guaranteed reachable |
| global `config_db` `"*"` scope | scope to the target subtree |

---

## 7. vsif / vManager registration

Representative entry -- adapt to the house vsif structure:

```
test <feat>_test {
    sv_seed : gen_random;
    // top / compile handled by the enclosing session or group;
    // +UVM_TESTNAME=<feat>_test drives UVM test selection
}
```

Add the test to the appropriate group so it enters the nightly session. IMC
merges coverage across the session automatically once the test runs -- no
per-test merge step.

---

## 8. Traceability

- `// VP-xxx` on the class links the test to its vPlan feature.
- Keep one primary feature per test. If a test exercises several, tag the
  dominant one on the class and rely on covergroup-level `VP-xxx` references for the
  rest.
