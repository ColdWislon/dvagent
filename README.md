# SV/UVM IP Verification Template — Copilot-ready

Use this repository as the **starter template for an IP verification
workspace**: describe your IP in one YAML, generate a complete UVM
environment with `uvm-gen`, and work it from day one with the GitHub
Copilot DV agent pack that ships in `.github/` — agents that write tests,
stimulus and checkers, close coverage and triage failures, under
no-shortcut guarantees (RTL read-only, no checker weakening, no claim
without a verdict).

Everything is aligned to one testbench infrastructure: uvm-gen
environments on a Cadence Xcelium make/xrun flow. One flow contract
(`.github/copilot-instructions.md`), one set of naming/structure
conventions, one verification record (`verif_matrix.yaml` per env).

## Start a new IP (ten minutes)

```bash
# 0. Create your repo from this template (or clone it), then on a machine
#    where xrun resolves:
pip install -r template/uvm-gen/requirements.txt

# 1. Describe the IP (copy an example, edit agents/VIPs/params)
cp template/uvm-gen/examples/my_ip.yaml uart.yaml && $EDITOR uart.yaml   # ip_name: uart

# 2. Generate the environment INTO this workspace
python3 template/uvm-gen/uvm_gen.py uart.yaml -o .

# 3. Prove it (stub DUT - green before you write a line of SV)
cd uart_verif/sim
make compile
make run TEST=uart_smoke_test        # UVM_ERROR : 0 + signature banner
make matrix                          # the run is on record

# 4. Open the workspace in VS Code (Remote-SSH) -> Copilot chat -> /start-here
```

Each IP lands in its own `<ip>_verif/` (agents, env, sequences, tests, tb,
sim flow, `verif_matrix.yaml`), with a `README.md` inside as the newcomer
walkthrough and its own `.github/` Copilot kit (env-specific instructions +
six chained phase prompts: connect-dut → implement-agents → write-tests →
triage-regression → coverage-closure → verif-closure). Re-running the
generator never overwrites your edits; adding an agent/VIP to the YAML adds
just the new files (stale files needing manual wiring are listed).

## What's in the template

Everything that makes up the template lives under `template/`, with exactly
one exception: `.github/` stays at the true repository root, because GitHub
Copilot only discovers `copilot-instructions.md`/`prompts/`/`agents/` at the
root of whatever's actually open — nesting it under `template/` would make
the whole agent pack invisible to Copilot on this repo itself. Generated IP
environments (`<ip>_verif/`, from running uvm-gen) also land at the true
root, as siblings of `template/` — that sibling split IS the "is this
template machinery or a generated instance" view at a glance.

| Where | What |
|---|---|
| `.github/` | the Copilot DV agent pack: 8 `dv-*` agents, 14 prompts (incl. `/start-here` onboarding), 35 skills, agent contract (`copilot-instructions.md` with the golden-verb → make-flow table), high-trust lockdown — **stays at repo root**, see above |
| `template/uvm-gen/` | the environment generator CLI (Python + Jinja2; own README, examples, 30-test suite). Also usable standalone — every generated env carries its own `.github/` Copilot kit |
| `template/chkq-kit/` | checker-qualification SV kit (negative tests: expectation catcher, guarded injector, base test) — source for staging into an env's negative-test tree (see note below; current uvm-gen does not automate this yet) |
| `template/external-vplan-kit/` | out-of-VS-Code vplan drafting for table/diagram-heavy PDF specs |
| `template/docs/methodology/` | the Definition of Done the reviewer audits against |
| `template/dashboard.ini` | verif-dashboard configuration (scans `dv,agents,env,seq_lib,tests,tb`) |
| `template/USERGUIDE.md` | **engineers start here** — agent workflow quick start |

Single source of truth: each env's Copilot collateral
(`.github/copilot-instructions.md` + the six phase prompts) is rendered by
uvm-gen from `template/uvm-gen/uvmgen/templates/copilot/` with the IP's real
names, paths and commands — there is no second copy to drift.

## The agent set

| Agent | Purpose | Entry prompt |
|---|---|---|
| `dv-env-architect` | architect/generate NEW env structure (bootstraps from uvm-gen, customizes via the 16 authoring skills) | `/generate-environment` |
| `dv-dut-integrator` | wire an EXISTING env's tb_top to the real DUT RTL (port mapping, tie-offs); focused and re-runnable, no new structure | `/connect-dut` |
| `dv-test-writer` | vplan item → test + covergroup + stimulus GLUE (thin subclasses of existing sequences), closed-loop | `/close-vplan-item` |
| `dv-stim-writer` | shared stimulus LIBRARY (new sequence classes, items, constraint layers), with distribution evidence | `/build-stimulus` |
| `dv-checker-writer` | NEW checks only (scoreboard/model/SVA), plan-approval + fault-injection protocol, human sign-off | `/write-checkers` |
| `dv-coverage-closer` | rank holes, close A/B via stimulus, propose C/D | `/close-coverage-holes` |
| `dv-debug` | same-seed triage, TB fix or RTL-suspect report | `/triage-failure` |
| `dv-reviewer` | read-only advisory pre-MR shortcut review | `/pre-mr-review` |
| (briefing) | read-only status: done / in flight / risks / ranked next actions | `/status` |
| (onboarding) | read-only guided first session for a new engineer: flow detection, env tour, smoke run, ranked first tasks | `/start-here` |

Agents appear in the Chat view agent picker after the files are on the
branch (reload window if needed). `dv-test-writer` and `dv-coverage-closer`
hand off to `dv-reviewer` at the end of a session. Newcomers: the generated
env's `README.md`, then `/start-here`.

Vplan drafting: `/generate-vplan <ip> <spec.pdf>` for text-dominant PDFs
(pdftotext extraction, page-cited items, human-approved draft);
`template/external-vplan-kit/` for table/diagram-heavy specs via a PDF-vision LLM
outside VS Code (same format contract; data-policy approval required for
the second vendor).

## How quality holds (the methodology core)

**One flow, evidenced.** All tool access goes through the generated
`sim/Makefile` (`make compile/run/waves/regress/matrix`; the contract maps
every abstract `dv <verb>` onto it — teams may layer a `dv` wrapper CLI on
top, recorded in the `dv-wrapper` flow-reference skill). A run's verdict is
its exit status, the `record_result: ... PASS/FAIL` line, the `CFG_BANNER`
config signature banner, and the record appended to `verif_matrix.yaml` — no claim
without that evidence, per the session report contract (machine-readable
sidecars in `dv/status/` feed the dashboard).

**Moving-target DUT.** The pack assumes RTL moves and encodes: revision
pinning (via each env's `dut.rtl_filelist` in `cfg/*.yaml`) + baseline run at
session start, no silent TB adaptation to RTL interface changes (change-note
confirmation required), revision-scoped coverage, dv-debug's what-changed/bisect step,
and the chkq central path registry (`dv/tests/negative/chkq_paths.svh`) so
RTL refactors have one audit point (CHKQ_PATH = maintenance; CHKQ_BLIND =
checker erosion). Recommended alongside: deliver RTL as tagged drops with
change notes, and stamp rtl/dv revisions into every verdict.

**Checker qualification (chkq).** `template/chkq-kit/` enables tests where checkers
are EXPECTED to fire: dv-checker-writer's Gate 4 commits persistent
negative tests under `dv/tests/negative/` (injection only via
`chkq_injector`, `+CHKQ_ENABLE`, `XRUN_OPTS='-access +rwc'`, coverage off
and excluded from merges). Treat `CHKQ_BLIND` failures as high severity — a
checker went blind, so some prior "clean report" may be unsound. Reparent
`chkq_base_test` onto `<ip>_base_test`; activation checklist ships in each
env's `dv/lists/chkq.list`.

**Review and visibility.** `dv-reviewer` (pre-MR diff, shortcut taxonomy)
is backed by `verif-env-review` (9-axis environment audit, JSON scorecard,
M0–M3 milestone verdict) and two deterministic CI-side scripts:
`deprecation-lint/scripts/lint.py` and `log-triage/scripts/triage_log.py`
(first-error + failure signatures feeding `regression-triage`). The local
dashboard (`verif-dashboard` skill; backend `dashboard.py`, config
`template/dashboard.ini`) renders pending human decisions, the review scorecard, vplan traceability,
PLACEHOLDER-CHECK inventory and session timeline per IP; `--all` adds a
multi-IP index.

**Shared conventions.** `uvm-coding-standard` (authoritative; detailed by
`naming-conventions`/`phasing-check`/`deprecation-lint`) and
`vertical-reuse` codify the generated shape — the code uvm-gen emits IS the
living reference (env children plain-named, agent internals `m_*`,
vsequencer handles `<name>_sqr` null when passive, stable `SCBD_*`/`CHK_*`
check IDs, `// VP-xxx` coverage tags, `// PLACEHOLDER-CHECK` stubs). See
`.github/skills/SKILLS-README.md` for the full skill map.

## Flow knowledge protocol (ask, never guess)

Agents treat flow semantics as unknown-until-confirmed: consult the
`dv-wrapper` skill (whose no-wrapper section records the uvm-gen make flow
as confirmed fact), probe `make help`/`--help`, and only then ask the
engineer via the built-in askQuestions tool — persisting every answer back
into the skill so each question is asked once per team, not once per
session. Sites layering a `dv` wrapper run `/learn-dv-wrapper` once per
setup to capture its specifics. Governance note: the dv-wrapper skill is
the single `.github/` file agents may edit (facts only) — exempt it from
the CODEOWNERS lock on `.github/`, or route its updates through
quick-review MRs if you prefer zero agent writes there.

## Using the pack outside this template

Generating an environment somewhere that is NOT a pack-rooted workspace?
Each generated env is self-contained for its own flow: its narrow `.github/`
(instructions + the six phase prompts) plus, by default, the per-IP
methodology tree — `docs/CLAUDE.md` + `docs/vplan.md`, and the `dv/` tree
with the chkq kit staged into `dv/tests/negative/`, regression lists,
exclusion file, and status sidecars (`dv_scaffold: false` opts out). What it
does NOT carry is the CROSS-IP agent pack — the `dv-*` agents, the 35 skills,
the dashboard, and the vplan-drafting kit live once at the workspace root. To
get those working on a hand-written or externally-generated DV repo, copy
`.github/`, `template/dashboard.ini`, `template/chkq-kit/`,
`template/docs/methodology/` and `template/USERGUIDE.md` to its root
(flattening `template/` back out — `.github/` needs no move, it was already
root-relative) and adapt the layout references.

## Prerequisites (in order of importance)

1. **A working simulation flow on the Remote-SSH host.** Default: the
   uvm-gen environment's `sim/Makefile` with `xrun` on PATH — the agent
   contract's golden-verb table maps every `dv <verb>` onto it, and the
   dv-wrapper skill records its facts as confirmed. Either way agents are
   forbidden from calling `xrun`/`imc` ad hoc. A coverage flow (IMC/`dv
   cov`) can follow; until then `dv-coverage-closer` should not be
   deployed.
2. **Per-IP `CLAUDE.md`/context docs and vplans** in each env's `docs/`
   (uvm-gen pre-fills CLAUDE.md and the vplan skeleton at generation; keep
   them current). The test-writer refuses work it cannot trace to a vplan
   item — that is intentional; seed the vplans first.
3. **Terminal auto-approval.** Allow-list only the flow entry points in
   workspace settings (`chat.tools.terminal.autoApprove`: `make `, plus
   `git diff`/`git log` for the reviewer). Do NOT blanket-approve terminal
   commands on farm hosts.
4. **Tool identifiers.** The `tools:` lists use namespaced VS Code names
   (terminal access = `execute/runInTerminal`, `execute/getTerminalOutput`,
   `read/terminalLastCommand`, `read/terminalSelection`, diagnostics =
   `read/problems`, code references = `search/usages`; plus `edit`,
   `search`, `vscode/askQuestions`). Names drift across Copilot versions —
   when VS Code reports a renamed tool, update every agent/prompt
   frontmatter in one pass and treat it as a pack version bump; a
   half-migrated tool list produces agents that silently lose capabilities.
5. **Model pinning (optional).** Add a `model:` field per agent to
   standardize; unset uses each engineer's selection.

## What this template deliberately does NOT do

- No fully-autonomous testbench generation: `dv-env-architect` bootstraps
  the skeleton deterministically from uvm-gen, but architecture is
  plan-approved (Gate 1) and real check semantics stay with
  `dv-checker-writer` (five gates, human sign-off). Modification of
  existing check semantics remains locked for every agent — update your CI
  gate accordingly (checker-file diffs from agent branches route to a
  mandatory sign-off state).
- No autonomous/cloud agent (`target: github-copilot`) — everything runs
  interactively in the engineer's Remote-SSH session.
- No enforcement in the IDE. The in-IDE reviewer is advisory; the binding
  no-shortcut gate is the deterministic CI check on every MR (path-based
  high-trust-zone detection, severity-demotion grep, exclusion file diffs,
  vplan-ref presence) plus periodic human audit of merged MRs. Agent
  instructions are guidance, not guarantees — never treat the lockdown
  instructions file as a security boundary.

## Rollout suggestion

Week 1–2: one pilot IP generated from this template, 2–3 volunteer
engineers, `dv-debug` + `dv-test-writer` only. Collect cycle time per vplan
item and reviewer findings. Then widen seats, add `dv-checker-writer`
(sign-off protocol), and add the coverage closer once a coverage flow
(IMC/`dv cov`) is wired.
