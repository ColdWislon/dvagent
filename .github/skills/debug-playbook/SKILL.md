---
name: debug-playbook
description: Xcelium/UVM failure triage tactics beyond the dv-debug decision tree — verbosity strategy, objection hangs, transaction tracing. Use during simulation failure debug.
---

# Debug Playbook (tactics layer)

The dv-debug agent owns the discipline (same seed, one hypothesis,
6-sim budget); this skill holds the tactics.

## Verbosity strategy
- Never rerun blind at UVM_HIGH globally on long tests: scope it —
  `+uvm_set_verbosity=<comp_path>,_ALL_,UVM_HIGH,time,<start_ns>` around
  the first-error time from the verdict.
- One rerun should answer one question: decide what evidence the current
  hypothesis needs BEFORE launching.

## Scoreboard mismatch tracing
- Key on the transaction identifier from the error message; grep both
  expected-push and actual-push messages for that id
  (`grep <txn_id> sim/results/<config>/<log>`; wrapper: `dv log grep`).
- Divergence questions in order: (1) same transaction observed on both
  sides? (missing/extra = monitor or ordering issue) (2) same fields
  compared? (3) model computed per SPEC? Justify any model fix against
  the spec §, never against the DUT's output.

## Hangs and timeouts
- `+UVM_OBJECTION_TRACE` first: which component holds the last objection.
- Drain/settle hangs: check `phase_ready_to_end` overrides and forever
  loops in monitors without `disable` on reset.
- Interface deadlock: read handshake state at hang time via waves on the
  shortest repro; check ready/valid stuck patterns against the protocol
  skill before suspecting RTL.

## Race/instability suspicion (same seed, different outcomes)
- Rerun same seed 3×; if unstable: suspect uninitialized TB state,
  time-0 races, or wildcard `uvm_config_db` collisions — not the DUT,
  until TB is exonerated.

## When waves are worth it
Only after log-level hypotheses are exhausted, on the shortest
reproducing test, with the time window known from the first-error
verdict. Record the probe scope used so the run is reproducible.
