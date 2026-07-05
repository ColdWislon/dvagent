---
name: dv-wrapper
description: Live reference for the team's dv wrapper CLI — commands, verdict schemas, exit codes, run directories. Consult BEFORE any dv invocation you are not certain about; append learned answers per the ask-don't-guess protocol.
---

# `dv` Wrapper — Live Reference

This file is a LIVING document with a special status: it is the only
`.github/` file agents may edit, and only to append FACTS about wrapper
behavior (marked `[learned <date>]` or `[confirmed <date>]`). Rules and
policy never live here. Sections marked **UNKNOWN — ASK** are unresolved:
follow the protocol in copilot-instructions.md (skill → `--help` → ask
the engineer via #tool:vscode/askQuestions → append the answer here).

## Contract basics (assumed until contradicted by --help or the engineer)
- Every subcommand prints one JSON verdict on stdout; full artifacts go
  to a run directory. Exit code 0 ⇔ `status == "pass"`.
- Raw logs are never read wholesale; access via `dv log first-error` /
  `dv log grep`.

## Subcommand inventory
**UNKNOWN — ASK / PROBE**: run `dv --help` in your first session on a new
setup and record the actual list here. Expected baseline:
`compile`, `sim`, `regress`, `cov merge|report|delta`, `lint`,
`log first-error|grep`. Record any team-specific extras (e.g. clean,
snapshot management) and any expected subcommand that does NOT exist yet
— agents must degrade gracefully (say what's missing) when a subcommand
is absent.

## `dv compile`
- Invocation: `dv compile <ip>` — **UNKNOWN — ASK**: `--clean` semantics?
  incremental by default?
- Verdict fields: `status, errors[{file,line,id,msg}], warning_count, log`
  — **UNKNOWN — CONFIRM** against a real run before first reliance.

## `dv sim`
- Invocation: `dv sim <ip> <test> [--seed N] [--waves] [--verbosity L]`
- **UNKNOWN — ASK**: how do plusargs pass through (`--plusargs "+X +Y"`,
  positional passthrough after `--`, or per-flag)? This matters for
  `+CHKQ_ENABLE` and `+uvm_set_verbosity`.
- **UNKNOWN — ASK**: seed behavior when `--seed` omitted (random? fixed
  default?) and where the used seed appears in the verdict.
- Verdict fields: `status, seed, uvm_fatal, uvm_error, first_error{...},
  sim_time_ns, log` — **UNKNOWN — CONFIRM**: is there a warning count /
  baseline-warning mechanism? Is the end-of-test marker checked by the
  wrapper or must the agent check it?

## `dv regress`
- **UNKNOWN — ASK**: list file format accepted (matches
  `dv/lists/*.list`?), local vs LSF vs vManager launch, how per-test
  results come back (single verdict? per-test array? path to summary?).

## `dv cov`
- **UNKNOWN — ASK**: does `report --holes` exist yet, its verdict shape,
  and whether holes carry `vplan_ref`. Until confirmed, coverage-closure
  sessions are NOT deployable — state this instead of improvising IMC
  calls.

## `dv log`
- `first-error <log> [--context N]` — **UNKNOWN — CONFIRM** output shape
  (inline excerpt + context-file path?).

## RTL revision handling
- **UNKNOWN — ASK**: do verdicts stamp the RTL/dv git revisions (they
  should — agents need them for baselines, coverage scoping, and
  regression triage)? Is there a `dv status`-style command? How are RTL
  drops delivered (continuous trunk vs tagged releases) and how does a
  worktree pin to a previous drop for bisect/confirm runs?

## Environment and run directories
- **UNKNOWN — ASK**: run dir layout and naming (`runs/<cmd>_<ts>/`?),
  whether run dirs are per-worktree, and what must never be deleted.
- **UNKNOWN — ASK**: is `env.setup` sourcing handled by the wrapper
  (assumed yes — agents never source tool environments themselves)?

## chkq specifics
- **UNKNOWN — ASK**: how to request the `-access +rwc` build config for
  negative tests (dedicated flag? separate compile target?), and how the
  wrapper/CI marks chkq runs as coverage-excluded.

## Learned facts log
[append below, newest first]
- (none yet)

## `dv cockpit` (proposed subcommand)
- Intended: `dv cockpit <ip> [--all]` wraps
  `python3 .github/skills/verif-cockpit/scripts/cockpit.py` (config:
  `cockpit.ini` at repo root). Human-facing; produces `cockpit.html`, no JSON
  verdict, exit 0 on generation.
- **UNKNOWN — ASK**: is the subcommand wired in this team's wrapper yet? If
  absent, invoke the backend script directly and record the answer here.
