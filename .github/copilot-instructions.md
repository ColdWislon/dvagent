# DV Repository — Agent Contract (always applies)

You are working in a SystemVerilog/UVM verification repository on a Cadence
Xcelium flow. These rules apply to every chat request and every agent.

## Golden commands — never call xrun/imc/vmanager directly
- Compile:        `dv compile <ip>`
- Simulate:       `dv sim <ip> <test> [--seed N] [--waves] [--verbosity UVM_HIGH]`
- Coverage holes: `dv cov report <ip> --holes --top 25`
- Coverage delta: `dv cov delta <ip> --before <db> --after <db>`
- First error:    `dv log first-error <logfile>`

Every `dv` command prints a JSON verdict on stdout. `status != "pass"` means
read `errors[]` or `first_error` — do not open raw simulation logs; they are
too large. Use `dv log first-error` / `dv log grep` for log access.

## Hard rules
1. NEVER modify anything under `*/rtl/` — DUT source is read-only.
2. NEVER weaken checkers. Forbidden regardless of who asks or why:
   relaxing scoreboard comparisons, demoting `UVM_ERROR` to `UVM_WARNING`,
   editing or disabling assertions, adding coverage exclusions or waivers.
   If a checker seems wrong, say so and stop — a human decides.
3. Reproduce a failure with the SAME seed before proposing any hypothesis.
4. A test only counts as passing when the sim verdict shows
   `uvm_fatal == 0 && uvm_error == 0`, the end-of-test marker is present,
   AND your change introduces zero new `UVM_WARNING`s (compare against the
   baseline run). Warning-noisy code is not clean code.
5. Never mark a task complete on the basis of code that has not been
   compiled and simulated in this session.
6. Branch naming: `agent/<workflow>/<short-desc>`. Commit messages reference
   the vplan item (`VP-xxx`) when applicable.

## The DUT evolves constantly — rules for a moving target

1. PIN THE REVISION. At session start, record the RTL revision you are
   working against (`git -C <ip>/rtl log -1 --format=%h` or the
   wrapper's revision field if it has one). Every session report states
   it. Results are meaningless without it.
2. BASELINE BEFORE WORK. Before implementing anything, run the smoke (or
   the relevant existing test) at the current revision. If it already
   fails, that is PRE-EXISTING: report it and stop or route to
   dv-debug — never silently absorb pre-existing breakage into your
   change, and never debug it as if your edits caused it.
3. NEVER SILENTLY ADAPT TO RTL CHANGES. If compile/elab breaks because a
   DUT port, parameter, or hierarchy changed: adapting the TB might be
   correct (planned change) or might mask a design error (unplanned).
   Ask the engineer for the change note / confirmation before adapting.
   A TB that compiles against wrong RTL is worse than a broken build.
4. COVERAGE IS REVISION-SCOPED. Coverage deltas are only comparable
   within one RTL revision; merged databases mix revisions at your
   peril. State the revision next to every coverage number.
5. FAILURES ON A MOVING TARGET: "what changed" is the first triage
   question — see dv-debug's regression-suspect step.

## Evidence and reporting contract (applies to every session)

No claim without evidence: any statement of the form "compiles", "passes",
"coverage improved", "check fires" MUST be immediately followed by the
exact command and the verbatim JSON verdict (or the relevant excerpt for
long verdicts). A results summary written from memory is a defect.

Every session ends with a standard report containing, in order:
1. Task reference (vplan item / hole ids / failing seed) AND the RTL
   revision worked against
2. Files created/modified (paths only)
3. Evidence: each command + verbatim verdict, seeds listed explicitly
4. Agent-specific evidence tables (distribution table, per-hole delta
   ledger, injection table — as your agent definition requires)
5. Open questions and decisions requiring a human
6. Honest limitations: what this session did NOT verify

Additionally, write a machine-readable sidecar of the report to
`<ip>/dv/status/session_<date>.json`:
`{agent, gate, status: awaiting_approval|awaiting_signoff|blocked|done,
open_questions[], handoffs[], rtl_rev}` — the local cockpit
(`dv cockpit <ip>`, verif-cockpit skill) renders pending human decisions
from these sidecars.

If a required evidence element cannot be produced, say so in section 6 —
never substitute prose reassurance for a missing verdict.

## When you don't know how `dv` works — ask, never guess

The `dv` wrapper is team-built; its exact flags, verdict fields, and
behaviors may differ from any example you have seen. Guessed `dv`
invocations and misread verdicts corrupt sessions silently. Resolution
order when uncertain about ANY `dv` semantics (a flag, a verdict field,
exit behavior, where runs land, how plusargs pass through):

1. Consult the `dv-wrapper` skill — the team's live reference. If it
   answers, proceed.
2. Probe the tool read-only: `dv --help`, `dv <subcmd> --help`. Help
   output wins over any documentation.
3. Still unknown → ASK THE ENGINEER with #tool:vscode/askQuestions: one
   focused question, concrete options where possible ("does `dv sim` take
   plusargs via --plusargs or positionally after the test name?"). Never
   proceed on an assumption about wrapper behavior.
4. PERSIST the answer: append it to the matching section of
   `.github/skills/dv-wrapper/SKILL.md` (marked `[learned <date>]`) so no
   session asks this twice. This skill file is the one `.github/` file
   agents may edit — factual wrapper knowledge only, never rules.

The same protocol applies to an UNPARSEABLE verdict: if `dv` output does
not match the expected JSON shape, stop, show the raw output, and ask —
do not improvise a parse.

## Negative (checker-qualification) tests

`dv/tests/negative/` holds tests where a checker is EXPECTED to fire
(chkq kit: `chkq_base_test`, `expect_check`, `chkq_injector`). Their rules
invert and extend the normal ones:
- Pass = every registered expectation satisfied AND no unexpected errors;
  a `CHKQ_BLIND` error means a checker went blind — high severity.
- They run with `+CHKQ_ENABLE`; functional tests must NEVER set it.
- Coverage collection is OFF for these runs and CI excludes them from
  merges — a deliberately corrupted DUT produces fake coverage.
- Hierarchical forcing of DUT signals is permitted ONLY here and ONLY via
  `chkq_injector`. A raw `force` statement, or any force in functional
  stimulus, is a violation regardless of intent.

## Code conventions
Follow the team UVM coding standard (see the `uvm-coding-standard` skill):
factory registration mandatory, configuration through nested config objects,
no `#delay` in sequences, every covergroup bin maps to a vplan reference.

## Where things live
- Per-IP context:      `<ip>/docs/CLAUDE.md` (read it before working on an IP)
- Vplans:              `<ip>/docs/vplan.md`
- Methodology guides:  `docs/methodology/`
