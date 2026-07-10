---
name: regression-triage
description: >-
  Triage a failing regression: cluster failures, rank clusters, and produce a
  dispatch plan. Use whenever the user reports N failing tests, a red nightly or
  vManager session, asks "what broke", wants failures grouped by root cause,
  deduplicated, prioritised, or assigned -- even if the word "skill" is never
  used. Consumes per-log failure signatures from `log-triage`.
---

# Triage a regression

Turn "217 failures" into "4 distinct bugs, ranked, with an owner and a repro
each". Never debug failures one by one before clustering: one root cause
typically explains most of a red regression.

## Procedure
1. **Collect** — from the Jenkins artifacts / verdict archive (vManager session
   data surfaces there): per-run status, test name, seed, and log path.
2. **Signature** — CI-side, run `log-triage/scripts/triage_log.py` over all
   failing logs to get one normalized signature per failure (same script
   per log in a live session; wrapper: `dv log first-error`).
3. **Cluster** — group by identical signature first; then merge clusters whose
   signatures differ only in the UVM ID's instance path or in masked values.
   Stimulus metadata (test name, seed, key knobs) is a secondary axis: one
   signature appearing only under one sequence type is a strong root-cause hint.
4. **Rank** — order clusters by: infra first (cheap to clear, unblocks reruns),
   then cluster size x suspicion (compile/elab breakage > TB fatal > scoreboard
   mismatch > single-seed flake).
5. **Check the delta** — new signature vs. yesterday's session? Correlate with
   what merged (RTL vs TB commits) since the last green run; on a moving DUT
   this is dv-debug's step-zero question, and results are only meaningful
   against a stated RTL revision (pin it in the report).
6. **Dispatch** — per cluster: representative failing run (test + seed + log),
   verdict, suspected layer, owner, and the exact rerun command
   (`make -C <ip>_verif/sim run TEST=<t> SEED=<s> CFG=<cfg>`; wrapper:
   `dv sim <ip> <t> --seed <s>`).

## Rules
- One representative run per cluster is debugged, not every member.
- A cluster that spans many unrelated tests points at shared code (env, VIP,
  RTL top) -- prioritise over single-test clusters of the same size.
- Single-seed, non-reproducing failures are quarantined as `flaky` with the seed
  recorded -- not silently rerun until green.
- Zero-failure but coverage-dropped sessions are also a triage finding.

## Output
Human: ranked cluster table (size, signature, verdict, owner, repro). Machine:
```json
{ "session": "nightly_2026-07-04", "total_fail": 217,
  "clusters": [
    { "id": 1, "size": 190, "signature": "UVM_FATAL:axi_driver:null virtual interface",
      "verdict": "tb_bug", "layer": "config", "suspect_commit": "tb@a1b2c3",
      "repro": { "test": "burst_wr_test", "seed": 91231, "log": "..." },
      "owner": "env owner" },
    { "id": 2, "size": 3, "signature": "flaky:timeout", "verdict": "flaky",
      "quarantine": true }
  ] }
```
This JSON is dashboard-ready (probe/CI monitoring) and diff-able session to
session.
