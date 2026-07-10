---
name: debug-strategy
description: >-
  Drive the debug of a single failing simulation to root cause. Use whenever the
  user is debugging one failing test, asks why a scoreboard mismatch / hang /
  X-propagation / assertion failure happens, wants a waveform strategy, wants to
  know what to probe or trace next, or is stuck mid-debug -- even if the word
  "skill" is never used. Picks up where `log-triage` left a `needs_waveform` or
  `dut_suspect` verdict.
---

# Debug a failing simulation

Hypothesis-driven debug: reproduce, localise in time, localise in space, then
bisect layers until the root cause is a specific line of RTL or TB code. Never
watch waveforms without a written hypothesis of what should be seen.

**Division of labour (team pack).** The `dv-debug` agent owns the DISCIPLINE:
same-seed reproduction first, one hypothesis per iteration, 6-sim budget,
step-zero "what changed" on a moving DUT, and the never-weaken-checkers rule.
The team `debug-playbook` skill owns the base tactics. This skill's
`references/playbooks.md` is the EXTENSION layer: per-failure-mode probe
recipes (X-prop, randomize failure, RAL, SVA vacuity) beyond the base
playbook. All commands go through the env's make flow (`make run
TEST=<t> SEED=<s>`, `triage_log.py`) or the team's `dv` wrapper -- never
raw xrun ad hoc.

## Procedure
1. **Reproduce** — same test + seed (`make run TEST=<test> SEED=<s>`;
   wrapper: `dv sim ... --seed <s>`); confirm
   the same failure. If it does not reproduce, rerun the same seed 3x and treat
   as race/instability, not the reported error (dv-debug rule).
2. **Localise in time** — from `log-triage`: first-error time T. The bug is at
   or before T; start at T and walk backwards.
3. **Localise in space** — from the failure kind, per `references/playbooks.md`:
   scoreboard mismatch -> the transaction's path; hang -> the stalled handshake;
   X-prop -> the first X source; SVA -> the sampled signals of the property.
4. **Bisect layers** — decide TB vs DUT with one question at a time: did the
   driver drive what the item said? did the DUT see it on pins? did the monitor
   reconstruct what the pins showed? did the reference predict correctly? Each
   answer eliminates a layer; the playbooks give the probes for each.
5. **Instrument** — smallest addition that answers the current question:
   scoped verbosity (`+uvm_set_verbosity=<path>,_ALL_,UVM_HIGH,time,<T>`),
   a probe on the suspect signals, one `uvm_info` at the suspect boundary.
   Not "record everything"; each rerun answers one question and counts
   against the sim budget.
6. **Conclude** — root cause = file:line + mechanism + why it escaped (missing
   assertion? coverage hole? check gap?). Feed that back: add the assertion or
   coverage that would have caught it earlier.

## Rules
- One hypothesis at a time; write it before opening the waveform.
- Trust order for a mismatch: pins > monitor > scoreboard > reference model --
  check what physically happened before what the TB believes.
- A TB bug found while chasing a "DUT bug" is the common case; keep the
  layer-bisect honest (check-independence violations show up exactly here).
- Root cause is not "it passes now": rerun the original seed AND 2 fresh seeds
  before closing (dv-debug verification rule).
- A reference-model fix is justified against the SPEC, never against the DUT's
  observed output; a checker is never weakened to make a test pass.
- Close the loop: every escaped bug gets a guard (SVA, check, or coverage) --
  and its `VP-xxx` entry if it revealed a plan hole.

Failure-mode playbooks (mismatch / hang / X-prop / SVA / randomize failure /
register bug) with concrete probe lists live in `references/playbooks.md`.
