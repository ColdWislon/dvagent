# DV Copilot Agent Pack

Custom agents for GitHub Copilot agent mode in VS Code, scoped to the
agreed target: authoring throughput inside existing UVM environments, with
structural no-shortcut guarantees. Drop the `.github/` tree into the DV
repository root and merge to the default branch.

**Engineers start with [USERGUIDE.md](USERGUIDE.md)** — setup, agent
selection table, a worked session, and the rules. This README is the
methodology-owner view. `/generate-vplan <ip> <spec.pdf>` drafts vplans
from text-dominant PDF specs (pdftotext extraction, page-cited items,
human-approved draft); `external-vplan-kit/` is the path for
table/diagram-heavy specs via a PDF-vision LLM outside VS Code (same
format contract, data-policy approval required for the second vendor).

## The agent set

| Agent | Purpose | Entry prompt |
|---|---|---|
| `dv-test-writer` | vplan item → test + covergroup + stimulus GLUE (thin subclasses of existing sequences), closed-loop | `/close-vplan-item` |
| `dv-stim-writer` | shared stimulus LIBRARY (new sequence classes, items, constraint layers), with distribution evidence | `/build-stimulus` |
| `dv-checker-writer` | NEW checks only (scoreboard/model/SVA), plan-approval + fault-injection protocol, human sign-off | `/write-checkers` |
| `dv-coverage-closer` | rank holes, close A/B via stimulus, propose C/D | `/close-coverage-holes` |
| `dv-debug` | same-seed triage, TB fix or RTL-suspect report | `/triage-failure` |
| `dv-reviewer` | read-only advisory pre-MR shortcut review | `/pre-mr-review` |
| (briefing) | read-only status: done / in flight / risks / ranked next actions | `/status` |

Agents appear in the Chat view agent picker after the files are on the
branch (reload window if needed). `dv-test-writer` and `dv-coverage-closer`
hand off to `dv-reviewer` at the end of a session.

## Moving-target DUT (RTL in constant evolution)

The pack assumes the DUT moves and encodes: revision pinning + baseline
run at every session start, no silent TB adaptation to RTL interface
changes (change-note confirmation required — silent adaptation masks
design errors), revision-scoped coverage, dv-debug's what-changed /
bisect step, and the chkq central path registry
(dv/tests/negative/chkq_paths.svh) so RTL refactors have one audit
point (CHKQ_PATH = maintenance; CHKQ_BLIND = checker erosion). Two
process recommendations to adopt alongside: deliver RTL as TAGGED DROPS
with change notes rather than continuous trunk (agents and nightly
baselines pin to a drop; TB adaptation tasks take the change note as
their spec), and have the dv wrapper stamp rtl/dv revisions into every
verdict — add it to the wrapper requirements.

## Wrapper knowledge protocol (ask, never guess)

Agents treat `dv` semantics as unknown-until-confirmed: consult the
`dv-wrapper` skill, probe `--help`, and only then ask the engineer via
the built-in askQuestions tool — persisting every answer back into the
skill so each question is asked once per team, not once per session.
Run `/learn-dv-wrapper` once per setup (and after wrapper changes) to
resolve the questionnaire in bulk; it verifies cheaply-checkable answers
with real runs on approval. Governance note: the dv-wrapper skill is the
single `.github/` file agents may edit (facts only) — exempt it from the
CODEOWNERS lock on `.github/`, or route its updates through quick-review
MRs if you prefer zero agent writes there.

## Knowledge layer (skills + templates)

`.github/skills/` ships the skills agents auto-discover:
methodology (uvm-coding-standard, vertical-reuse, coverage-closure,
xcelium-flow, debug-playbook, dv-wrapper, vplan-common-topics — the
mandatory reset/clocks/CDC/etc. sweep with a per-vplan completeness
matrix) and protocol knowledge
(amba-axi, amba-ahb, amba-apb — verification-oriented: traps, check-ID
candidates, coverage crosses, chkq injection ideas). All written as
checkable rules. WHERE A TEAM GUIDE EXISTS,
MERGE IT IN: these files are expert baselines, your guides are the
authority. The check-ID rule in uvm-coding-standard is load-bearing for
chkq — adopt it even if you adopt nothing else.

`repo-templates/` holds the per-IP files the agent contracts reference:
`docs/CLAUDE.md` (block context — agents are only as good as this file),
`docs/vplan.md` (agent-readable vplan; if vplans live in vManager, make
this a CI-regenerated export), `dv/cov/exclusion_requests.md`,
`dv/lists/sanity.list`, `dv/lists/chkq.list`, and
`docs/methodology/definition-of-done.md` (repo-level, the reviewer's
checklist). Seeding CLAUDE.md + vplan.md on the pilot IP is a
prerequisite for the pilot, not a nice-to-have — the test-writer refuses
untraceable work by design.

## Checker qualification (negative tests)

`chkq-kit/` ships a small SV package (expectation catcher, guarded
injector, base negative test) enabling tests where checkers are EXPECTED
to fire. dv-checker-writer Gate 4 now commits persistent negative tests
under `dv/tests/negative/` instead of throwaway injections, and its Mode B
(`/qualify-checkers`) retrofits qualification onto existing checkers.
Operational notes:
- `uvm_hdl_force` needs `xrun ... -access +rwc` (scope it to the chkq
  build config if access is a concern elsewhere).
- Run the `dv/lists/chkq.*` list in every regression with `+CHKQ_ENABLE`
  and coverage OFF; exclude those runs from IMC merges (forced-corrupt
  runs produce fake coverage).
- Treat `CHKQ_BLIND` regression failures as high severity: a checker went
  blind, meaning some prior "clean report" may already be unsound.
- Reparent `chkq_base_test` to your team base test; forced HDL paths are
  refactoring-brittle, so re-run the chkq list after RTL restructures.

## Agent boundaries

Test-writer vs. stim-writer is an artifact-type split, not an intent
split: new reusable classes under `dv/seq/` (sequences, items, constraint
layers) belong to the stim-writer and its distribution oracle; test
classes, covergroups, and thin single-test subclasses of existing
sequences belong to the test-writer. Reciprocal handoffs cover the cases
where an item needs new library stimulus or new stimulus is ready for a
test.

## Prerequisites (in order of importance)

1. **The `dv` wrapper CLI on PATH of the Remote-SSH host.** The agents are
   written against its JSON verdicts and are explicitly forbidden from
   calling `xrun`/`imc` directly. Minimum viable subset for day one:
   `dv compile`, `dv sim`, `dv log first-error`. Coverage subcommands can
   follow; until then `dv-coverage-closer` should not be deployed.
2. **Per-IP `CLAUDE.md`/context docs and vplans** where the agent contract
   says they are (`<ip>/docs/`). The test-writer refuses work it cannot
   trace to a vplan item — that is intentional; seed the vplans first.
3. **Terminal auto-approval.** For a smooth loop, allow-list only the
   wrapper in workspace settings, e.g. `chat.tools.terminal.autoApprove`
   with an entry for `dv ` (plus `git diff`/`git log` for the reviewer).
   Do NOT blanket-approve terminal commands on farm hosts.
4. **Tool identifiers.** The `tools:` lists use namespaced VS Code
   names (terminal access = `execute/runInTerminal`,
   `execute/getTerminalOutput`, `read/terminalLastCommand`,
   `read/terminalSelection`, diagnostics = `read/problems`,
   code references = `search/usages`; plus `edit`, `search`,
   `vscode/askQuestions`). The old `changes` tool was removed with no
   1:1 replacement — agents read the working-tree diff via `git diff`
   through the terminal tools instead. Names drift across
   Copilot versions — when VS Code reports a renamed tool, update every
   agent/prompt frontmatter in one pass and treat it as a pack version
   bump, since half-migrated tool lists produce agents that silently
   lose capabilities.
5. **Model pinning (optional).** Add a `model:` field per agent if you
   want to standardize; leaving it unset uses each engineer's selection.

## What this pack deliberately does NOT do

- No full-testbench generation agent — excluded by decision until the
  reviewer layer has a proven catch rate. dv-checker-writer is the one
  sanctioned incursion into high-trust code: NEW checks only, additive
  diffs, engineer-approved plan before code, fault-injection firing
  evidence per check, human sign-off on the MR. Modification of existing
  check semantics remains locked for every agent. Update the Jenkins gate
  accordingly: checker-file diffs from agent branches are not auto-rejected
  but routed to a mandatory sign-off state, with an additive-only diff
  check where feasible.
- No autonomous/cloud agent (`target: github-copilot`) — everything here
  runs interactively in the engineer's Remote-SSH session.
- No enforcement. The in-IDE reviewer is advisory by design. The binding
  no-shortcut gate is the deterministic Jenkins check on every MR
  (path-based high-trust-zone detection, severity-demotion grep, exclusion
  file diffs, vplan-ref presence) plus the periodic human audit of merged
  MRs. Agent instructions are guidance, not guarantees — never treat the
  lockdown instructions file as a security boundary.

## Rollout suggestion

Week 1–2: `dv-debug` + `dv-test-writer` with 2–3 volunteer engineers on one
pilot IP, `dv` wrapper minimum subset. Collect the Q5 metrics (cycle time
per vplan item; reviewer findings). Then widen seats and add the coverage
closer once `dv cov` verdicts exist.


## Merged skill pack — two pillars

This repo now carries two pillars on one methodology core:

**Pillar 1 — Generate environments** (`dv-env-architect` agent, new):
architecture plan -> generation from the 12 authoring skills (`uvm-sequence-item`
... `uvm-test`) -> compile + smoke proof. Scoreboards are generated with
connectivity + PLACEHOLDER-CHECK stubs; real check semantics stay with
`dv-checker-writer` (five gates). Entry: `/generate-environment`.

**Pillar 2 — Review code and environments**: `dv-reviewer` (pre-MR diff,
shortcut taxonomy) now backed by the `verif-env-review` skill for full
environment audits (9 axes, JSON scorecard, M0-M3 milestone verdict) and by
two deterministic CI-side scripts: `deprecation-lint/scripts/lint.py`
(coding-standard + check-independence subset, non-zero exit on error) and
`log-triage/scripts/triage_log.py` (first-error + failure signatures feeding
`regression-triage`). Entry: `/review-environment`, `/pre-mr-review`.

**Local visibility — the cockpit**: `dv cockpit <ip>` (verif-cockpit skill;
backend `cockpit.py`, stdlib, static HTML) renders, per IP: pending human
decisions (Gate-1 approvals, sign-offs, exclusion proposals, open questions,
unresolved PLACEHOLDER-CHECKs), the review scorecard (M0-M3 + 9 axes), vplan
traceability, regression clusters and the agent-session timeline — from
`dv/status/` verdicts plus direct tag scans. `--all` adds a multi-IP index.
Tool specifics are abstracted in `cockpit.ini` `[tool]` (xcelium profile by
default). Sessions feed it via the session_*.json sidecar (evidence contract).

Shared core: `uvm-coding-standard` (authoritative; detailed by
`naming-conventions` / `phasing-check` / `deprecation-lint`), the `dv` wrapper
contract, chkq, the DoD, and `vertical-reuse`. See
`.github/skills/SKILLS-README.md` for the full skill map.

## Standalone tooling — uvm-gen

[`uvm-gen/`](uvm-gen/README.md) is a self-contained CLI (Python + Jinja2, no
Copilot/agent dependency) that generates complete UVM IP verification
environments for Xcelium from a YAML spec: agents, env (scoreboard/coverage/
vsequencer/RAL hook), Cadence VIP hookups (APB/AHB/I3C), smoke test, tb_top,
Makefile/xrun flow, vManager vsif, and multi-configuration tracking via
`verif_matrix.yaml`. Generated envs are SoC-reuse ready (single env_cfg via
config_db, per-agent passive switch). See `uvm-gen/README.md`.
