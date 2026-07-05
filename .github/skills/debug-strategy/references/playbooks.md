# Debug playbooks by failure mode

Loaded on demand from `debug-strategy/SKILL.md`. Each playbook: what to probe,
in what order, and the question each probe answers. Stop at the first probe
whose answer contradicts the hypothesis -- that boundary hides the bug.

---

## 1. Scoreboard mismatch (`UVM_ERROR ... mismatch exp=... got=...`)

Hypothesis template: "transaction <T> was corrupted / mispredicted at layer <L>".

Probe order (trust order: pins before beliefs):
1. **Pins at time T** — waves on the bus interface around the failing
   transaction. Did the DUT *output* what `got` says? If not, the monitor is
   misreconstructing (TB bug).
2. **Input pins** — did the DUT *receive* what the stimulus intended? If not,
   driver bug (TB).
3. **Reference model** — feed the observed input manually through the reference:
   does it produce `exp`? If not, prediction bug (TB) -- includes the
   check-independence failure (expected derived from stimulus, not observation).
4. **Only now DUT** — input correct, output wrong, prediction correct => DUT.
   Trace the datapath between the two points; bisect on internal registers.

Fast checks first: off-by-one (previous/next transaction compared), ordering
(out-of-order legal on this bus? scoreboard assumes in-order?), reset (was the
transaction issued before reset released?).

---

## 2. Hang / timeout (objection never drops, watchdog fires)

Hypothesis template: "handshake <H> is stalled because <side> never asserts <sig>".

1. **Last heartbeat** — last `uvm_info` before the freeze names the component
   that was alive; the stall is at its boundary.
2. **Objection trace** — `+UVM_OBJECTION_TRACE`: which component holds the
   objection that never drops?
3. **Handshake pins** — at freeze time: valid without ready (consumer stalled),
   ready without valid (producer stalled), neither (upstream dead).
4. **Sequencer state** — `get_next_item` never returning = sequence exhausted
   without `item_done`, or an arbitration lock (`lock`/`grab` leak).
5. Common TB causes before blaming the DUT: missing `item_done`, sequence
   waiting on an event nobody fires, drain time too short is the *opposite*
   symptom (early exit), forgotten `disable fork` leaving a stuck thread.

---

## 3. X-propagation (`got=x`, assertion on X, X in waves)

Hypothesis template: "X originates at <source> at time <T0> and reaches the
failure point through <path>".

1. **Walk back to first X** — the failing signal's X is fallout; trace drivers
   backwards in the waveform until the *first* signal to go X. That is T0.
2. **Classify the source** — uninitialised register (no reset term),
   multi-driver conflict, un-driven input (TB forgot to connect / drive),
   crossing before reset released.
3. If T0 is at time 0 and the source is a TB interface signal: driver `idle()`
   incomplete (drives X out of reset) -- TB bug, not DUT.
4. RTL fix classes: reset term, default assignment, enable gating. TB fix
   classes: drive idle values, connect the interface, hold off traffic in reset.

---

## 4. SVA assertion failure

Hypothesis template: "property <P> fired because antecedent occurred and
consequent was violated at <T> due to <signal>".

1. **Read the property**, not just its name: what exact temporal sequence
   failed? Which attempt (start time) vs failure time?
2. **Sample the property's signals** at the failing attempt in the waves --
   including the clock and `disable iff` reset term.
3. False-failure checks (assertion bug, not DUT bug): missing/wrong reset
   guard, wrong clock, off-by-one in `|->` vs `|=>`, unconstrained antecedent
   firing during configuration.
4. If the property is right and the trace violates the spec: DUT bug; the
   assertion already localises the signal and cycle -- no further search needed.

---

## 5. Randomization failure (`randomize() failed`)

1. Rerun with the solver debug switch to dump the contradiction
   (Xcelium: `-solver_debug` / consult the failure dump).
2. Bisect constraints: disable half (`constraint_mode(0)`), re-randomize,
   narrow to the contradicting pair.
3. Usual suspects: `dist` vs hard equality on the same field, config knob
   forcing a range the constraint excludes, `solve...before` cycle, a state
   variable (not `rand`) left at a stale value by a previous transaction.
4. TB rule from `uvm-sequence`: the fix is in the constraint set or the knob,
   never a `std::randomize` bypass.

---

## 6. Register / RAL bug (read-back mismatch, mirror divergence)

1. Frontdoor read vs backdoor `peek` at the same time: agree => model vs DUT
   spec issue; disagree => access path bug.
2. Check the adapter first (`reg2bus`/`bus2reg`): byte enables, address
   translation, kind (read/write) mapping.
3. Mirror divergence with a passing bus: predictor not connected to the bus
   monitor, or auto-predict left on together with an explicit predictor
   (double update) -- both are `uvm-ral` hard-rule violations.
4. W1C / RC / special-access fields: verify the field access policy in the
   model matches the spec before suspecting RTL.

---

## Instrumentation cheat-sheet (smallest first)

| Question | Tool |
|---|---|
| one component, more detail | `+uvm_set_verbosity=<path>,_ALL_,UVM_HIGH,run` |
| who holds the objection | `+UVM_OBJECTION_TRACE` |
| config_db resolution | `+UVM_CONFIG_DB_TRACE` |
| factory overrides applied? | `print_topology()` + factory `print()` in `end_of_elaboration` |
| what the sequencer runs | `+UVM_PHASE_TRACE`, sequencer `print()` |
| waves for one window | probe the suspect scope for [T-margin, T]; not "everything from 0" |
