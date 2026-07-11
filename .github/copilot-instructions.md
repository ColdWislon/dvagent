# DV Repository — Agent Contract (always applies)

You are working in a SystemVerilog/UVM verification repository on a Cadence
Xcelium flow. These rules apply to every chat request and every agent.

## Golden commands — never invoke xrun/imc/vmanager ad hoc

Each IP's testbench is a **uvm-gen environment** (`<ip>_verif/` — generated
by `uvm-gen/`, see its README): all tool access goes through the generated
`sim/Makefile`. Throughout this pack, `dv <verb>` is the ABSTRACT golden
verb; in this infrastructure it resolves per this table (run from
`<ip>_verif/sim/`, or prefix `make -C <ip>_verif/sim`):

| Golden verb | This infrastructure |
|---|---|
| `dv compile <ip>` | `make compile` (elab-only, stub DUT ok) |
| `dv sim <ip> <test> --seed N` | `make run TEST=<test> SEED=N` |
| `dv sim ... --waves` | `make waves TEST=<test>` |
| `dv sim ... --verbosity UVM_HIGH` | `make run ... UVM_VERBOSITY=UVM_HIGH` |
| plusargs / extra xrun flags | `make run ... XRUN_OPTS='+X +Y=2'` |
| configuration select / all-passive | `make run ... CFG=cfg/<cfg>.yaml` / `XRUN_OPTS=+<IP>_PASSIVE=all` |
| `dv regress <ip>` | `make regress` (vManager vsif); status: `make matrix` |
| `dv log first-error <log>` | `python3 .github/skills/log-triage/scripts/triage_log.py sim/results/<config>/<log>` |
| `dv log grep` | targeted `grep` on `sim/results/<config>/<log>` |
| `dv cov report/delta/merge` | not wired by default — say so; never improvise IMC calls |
| `dv lint --diff` | `python3 .github/skills/deprecation-lint/scripts/lint.py <tb paths>` |
| `dv cockpit <ip>` | `python3 .github/skills/verif-cockpit/scripts/cockpit.py` (config: `cockpit.ini`) |

Verdict contract in this flow: `make run` exits non-zero on any failure;
`sim/scripts/record_result.py` prints a one-line `record_result: ...
PASS/FAIL` verdict, every run prints the `CFG_BANNER` config-signature
banner, and appends a
machine-readable record to `verif_matrix.yaml` (config_name, param hash,
test, seed, result, UVM error/fatal counts, date, git rev). Quote the matrix
record or the `--- UVM Report Summary ---` block as your verdict. Do not
open raw simulation logs wholesale — they are too large; use the triage
script / targeted grep.

Teams layering a `dv` wrapper on top of this Makefile: prefer the wrapper
(JSON verdicts replace the equivalents above) and keep
`.github/skills/dv-wrapper/SKILL.md` current per the ask-don't-guess
protocol below.

## Hard rules
1. NEVER modify anything under `*/rtl/` — DUT source is read-only.
2. NEVER weaken checkers. Forbidden regardless of who asks or why:
   relaxing scoreboard comparisons, demoting `UVM_ERROR` to `UVM_WARNING`,
   editing or disabling assertions, adding coverage exclusions or waivers.
   If a checker seems wrong, say so and stop — a human decides.
3. Reproduce a failure with the SAME seed before proposing any hypothesis.
4. A test only counts as passing when the UVM report summary shows
   `UVM_ERROR : 0` and `UVM_FATAL : 0` with the `** UVM TEST PASSED **`
   end-of-test marker present (matrix record `result: pass` / wrapper
   verdict `uvm_fatal == 0 && uvm_error == 0`), AND your change introduces
   zero new `UVM_WARNING`s (compare against the baseline run).
   Warning-noisy code is not clean code.
5. Never mark a task complete on the basis of code that has not been
   compiled and simulated in this session.
6. Branch naming: `agent/<workflow>/<short-desc>`. Commit messages reference
   the vplan item (`VP-xxx`) when applicable.

## The DUT evolves constantly — rules for a moving target

1. PIN THE REVISION. At session start, record the RTL revision you are
   working against. The RTL lives OUTSIDE the generated env — its filelist
   is referenced by `sim/dut.f`; record `git -C <rtl_dir> log -1
   --format=%h` there (or the design drop tag), plus the env's own
   revision. While the DUT is the generated stub (fresh env, dut.f not yet
   flipped), say so — "stub DUT" is the revision statement. Every session
   report states it; results are meaningless without it.
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
`<ip>_verif/dv/status/session_<date>.json`:
`{agent, gate, status: awaiting_approval|awaiting_signoff|blocked|done,
open_questions[], handoffs[], rtl_rev}` — the local cockpit
(`dv cockpit <ip>`, verif-cockpit skill) renders pending human decisions
from these sidecars.

If a required evidence element cannot be produced, say so in section 6 —
never substitute prose reassurance for a missing verdict.

## When you don't know how the flow works — ask, never guess

Flow semantics you are not certain about (a make variable, where runs
land, how plusargs pass through, seed behavior, a wrapper flag or verdict
field) corrupt sessions silently when guessed. Resolution order:

1. Consult the `dv-wrapper` skill — the live flow reference. Its
   "no-wrapper default" section documents this repo's uvm-gen make flow
   as confirmed fact; wrapper sections cover teams that layered a `dv`
   CLI on top. If it answers, proceed.
2. Probe read-only: `make -C <ip>_verif/sim help`, and for a wrapper
   `dv --help` / `dv <subcmd> --help`. Tool output wins over any
   documentation. (`sim/Makefile` itself is readable ground truth.)
3. Still unknown → ASK THE ENGINEER with #tool:vscode/askQuestions: one
   focused question, concrete options where possible. Never proceed on an
   assumption about flow behavior.
4. PERSIST the answer: append it to the matching section of
   `.github/skills/dv-wrapper/SKILL.md` (marked `[learned <date>]`) so no
   session asks this twice. This skill file is the one `.github/` file
   agents may edit — factual flow knowledge only, never rules.

The same protocol applies to an UNPARSEABLE result: if a run's output
matches neither the uvm-gen verdict shape (record_result line + UVM summary
+ matrix record) nor the wrapper's JSON, stop, show the raw output, and ask
— do not improvise a parse.

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

## Where things live (uvm-gen environment layout)
- Env root `<ip>_verif/`:
  - `agents/<name>_agent/` — interface, seq_item, sequencer, driver,
    monitor, agent cfg, agent, base sequence, package (one dir per
    interface; stimulus items/base sequences live here)
  - `env/` — `<ip>_env`, `<ip>_env_cfg`, `<ip>_scoreboard`,
    `<ip>_<name>_coverage` subscribers, `<ip>_virtual_sequencer`, RAL
    (`<ip>_reg_block`/`_reg_adapter`); `vip/<name>_vip/` — Cadence VIP wrappers
  - `seq_lib/` — virtual sequences; `tests/` — test classes
  - `tb/` — `<ip>_tb_top.sv` + generated DUT stub; `sim/` — Makefile,
    `.f` filelists, vsif, `scripts/` (cfg2args.py, record_result.py,
    matrix_report.py); logs in `sim/results/<config>/`
  - `cfg/` — one YAML per configuration; `verif_matrix.yaml` — append-only
    run records (sign-off evidence)
- Per-IP context:      `docs/CLAUDE.md` (read it before working on an IP)
- Vplans:              `docs/vplan.md`
- Methodology guides:  `docs/methodology/`
- Negative tests/chkq: `dv/tests/negative/`; regression lists `dv/lists/`;
  session sidecars `dv/status/`; exclusions `dv/cov/exclusion_requests.md`
- RTL: outside the env, referenced by `sim/dut.f` — read-only as ever.
