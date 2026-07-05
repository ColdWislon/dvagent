# <IP_NAME> — Verification Context

[TEMPLATE — copy to <ip>/docs/CLAUDE.md and fill every bracket. Keep under
~100 lines; link out instead of inlining. Agents read this before any work
on the IP — an empty or stale file produces confidently wrong agents.]

## What this block does
[2–4 sentences: function, key interfaces, clock/reset domains. Link the
spec: docs/spec/<file> §relevant. If the spec is not agent-readable
in-repo, say where humans find it — agents must then ask instead of
guessing.]

## Testbench architecture (10 lines max)
- Env: `<ip>_env` — agents: [<bus>_agent (ACTIVE), ...], scoreboard:
  `<ip>_scbd` (reference model: [inline / <ip>_model class]), RAL: [yes/no]
- Virtual sequencer: `<ip>_vsequencer` — handles: [...]
- Top harness: `tb_top` in `dv/tb/<ip>_tb_top.sv`
- Base test: `<ip>_base_test`; smoke test: `<ip>_smoke_test`
- chkq base: `<ip>_chkq_base_test` (reparented chkq_base_test): [yes/not yet]

## Clock / reset / CDC inventory
[The Phase-3 vplan sweep and CDC items depend on this being accurate:
- Clock domains: [name: range/ratio constraints, ...]
- Reset domains: [name: async/sync, soft-reset behavior, ...]
- Crossings: [src→dst: scheme (2FF / gray / handshake / async FIFO), ...]
- CDC report location: [path / tool run reference]]

## Current verification focus
[What phase is this block in? Which vplan sections are open? What should
an agent NOT touch right now (e.g., area under active human rework)?]

## Known quirks and traps
[The list that saves hours: protocol deviations from standard, known
waived warnings, flaky areas, sequences with non-obvious preconditions,
signals with misleading names. One line each.]

## Check ID inventory
[Stable uvm_error IDs this env's checkers emit, one line each:
`SCBD_DATA_CMP` — read-data compare against model
`CHK_PROT_HSK`  — interface handshake protocol
Keep in sync with chkq negative tests.]

## Commands
- Compile: `dv compile <ip>`   Smoke: `dv sim <ip> <ip>_smoke_test`
- Sanity list: `dv/lists/sanity.list`   chkq list: `dv/lists/chkq.list`
- [Any IP-specific plusargs/configs an agent must know]

## Ownership
Block owner: [name]. Checker sign-off: [name]. Escalate RTL-suspect
reports to: [name/channel].
