---
name: vertical-reuse
description: Rules making UVM environments and stimulus reusable from block to subsystem level. Use when creating or modifying env/agent structure, config objects, sequences, or RAL integration.
---

# Vertical Reuse Rules (block → subsystem)

Everything written at block level must run unchanged when the environment
is instantiated inside a subsystem env. [TEAM: merge the full vertical
reuse guide here — this file is the enforceable distillation.]

## Agents
- Every agent supports `UVM_ACTIVE`/`UVM_PASSIVE` via its config object;
  passive mode instantiates monitor(+coverage) only. Code MUST NOT assume
  the driver/sequencer exists (guard with `is_active`).
- Monitors and coverage collectors work identically in both modes — they
  observe the interface, never internal TB state.

## Configuration objects
- One config class per agent; the env config CONTAINS agent configs
  (composition, not parallel `uvm_config_db` entries per field).
- The env exposes a single `*_env_cfg` handle; a subsystem env sets block
  envs passive by flipping fields in the nested cfg, nothing else.
- Interface (virtual if) handles travel inside config objects, set at the
  test/harness boundary — components never `get` vifs directly by string
  path.

## Environments
- Block env has no absolute hierarchy assumptions: no `uvm_top` lookups,
  no `$root`/`tb_top` paths, no hardcoded `env.` prefixes in messages
  used for parsing.
- Scoreboards subscribe via analysis ports/exports only; connecting a
  block scoreboard to subsystem-level monitors MUST require no scoreboard
  code change.
- End-of-test checks (`check_phase`) must be valid when the block is a
  passive observer of subsystem traffic (no assumptions that this env's
  stimulus produced the transactions).

## Sequences
- Sequences target a sequencer handle obtained from the virtual sequencer
  or passed in — never a hardcoded path.
- Virtual sequences at block level compose into subsystem virtual
  sequences; design them as callable building blocks (no objection
  handling inside reusable sequences — the caller owns objections).

## RAL
- Block RAL models are complete and self-contained; the subsystem model
  COMPOSES block models with address offsets — never re-describes
  registers.
- Adapters/predictors instantiated per bus agent in the env, wired via
  config; frontdoor/backdoor selection is a config field, not code edits.

## Litmus tests (agents: verify before claiming reuse-clean)
1. grep the diff for `tb_top`, `uvm_top`, absolute hierarchical paths in
   class code ⇒ any hit is a finding.
2. Passive-mode compile check: does the code guard every
   driver/sequencer access with `is_active`?
3. Could this sequence run on a subsystem virtual sequencer without
   modification? If not, what config field is missing?
