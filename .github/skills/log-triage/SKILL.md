---
name: log-triage
description: >-
  Parse, classify and summarise Xcelium / UVM simulation logs. Use whenever the
  user pastes or points at a simulation log, asks why a test failed, wants the
  first real error extracted from a noisy log, wants UVM_ERROR / UVM_FATAL /
  assertion failures classified, or wants a log turned into a structured failure
  signature -- even if the word "skill" is never used. Produces the failure
  signature consumed by `regression-triage`.
---

# Triage a simulation log

Turn a UVM simulation log into a verdict: the **first causal error**, its
classification, and a normalized **failure signature** for clustering. The first
error is almost always the cause; later errors are usually fallout.

**Where this runs.** In an agent session, raw logs are not opened wholesale:
use `scripts/triage_log.py <log>` (or `dv log first-error` / `dv log grep`
with a wrapper — team contract) and interpret
its verdict with the reading rules below. `scripts/triage_log.py` is the
CI/wrapper-side implementation of the same triage -- run it in Jenkins
post-regression (or wire it behind `dv log first-error`) to batch-produce
signatures; it is not an excuse for an agent to bypass the wrapper.

## Procedure
1. Get the first error: `python3 .github/skills/log-triage/scripts/triage_log.py sim/logs/<log>`
   in a session (wrapper: `dv log first-error <log>`), or
   `scripts/triage_log.py <logfile ...>` CI-side (parses, classifies,
   extracts first error + signature, emits JSON).
2. Read the JSON. Interpret only where the script cannot: read the log lines
   *around* the first error (the script reports its line number) to state the
   likely cause in one sentence.
3. Classify along two axes:
   - **Layer**: compile/elab (`*E,` before time 0) | testbench (UVM_FATAL from
     env/config: null vif, config_db miss, randomize failure) | DUT-suspect
     (scoreboard mismatch, SVA failure) | infra (license, disk, timeout, Jenkins)
   - **Verdict**: `tb_bug` | `dut_suspect` | `infra` | `needs_waveform`
4. Recommend the single next action: fix TB code, open a waveform at time T,
   rerun with `+UVM_VERBOSITY=UVM_HIGH`, or escalate as a DUT bug with the
   signature attached.

## Reading rules
- First `*E,` / `UVM_FATAL` / `UVM_ERROR` / assertion failure wins; everything
  after is fallout unless at a distant sim time.
- `UVM_ERROR` count > 0 with test PASS in banner = broken pass/fail logic --
  flag it (report catcher / severity demotion to inspect).
- A timeout with zero errors usually means a hung handshake or a lost objection
  -- point at the last `uvm_info` heartbeat before the freeze.
- Never conclude "DUT bug" from the log alone -- the strongest log-only verdict
  is `dut_suspect` with a waveform time to inspect.

## Output
Human: one-line verdict + cause + next action. Machine (from the script):
```json
{ "file": "run.log", "verdict": "dut_suspect", "layer": "scoreboard",
  "first_error": { "line": 1234, "time_ns": 84210, "severity": "UVM_ERROR",
    "id": "axi_scoreboard", "message": "mismatch exp=... got=..." },
  "signature": "UVM_ERROR:axi_scoreboard:mismatch exp=<X> got=<X>",
  "counts": { "uvm_error": 3, "uvm_fatal": 0, "sva_fail": 0 },
  "next_action": "open waveform at 84210ns on the write channel" }
```
The `signature` is normalized (numbers/addresses masked to `<X>`) so identical
bugs from different seeds produce the same string -- that is what
`regression-triage` clusters on.
