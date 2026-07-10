---
agent: 'agent'
tools: ['search', 'execute/runInTerminal', 'execute/getTerminalOutput', 'read/terminalLastCommand', 'read/terminalSelection', 'vscode/askQuestions']
description: 'Read-only briefing on the current work: done, in flight, risks, ranked next actions'
---
Brief me on the CURRENT work in this worktree — do not ask me which IP,
infer it from context. Resolve the IP from: the working directory path
(which <ip>/ subtree am I in), the repo layout (`git rev-parse
--show-toplevel`, then locate the rtl/ and dv/ dirs), or the branch name
(agent/<workflow>/... often carries it). If exactly one IP is present,
use it silently. Only if the worktree genuinely spans multiple IPs or
none can be identified, ask ONE disambiguation question — otherwise
never block on input.

STRICTLY READ-ONLY: you have no edit tool by design; run only inspection
commands (git log/status/diff --stat, ls, file reads, `dv log`). Do not
launch compiles or sims; if a coverage snapshot would help, ASK before
running `dv cov report`.

## Gather (skip gracefully and say so if an artifact is missing)
1. Branch state: current branch vs integration branch — commits ahead
   (one line each), uncommitted changes (`git status -s`,
   `git diff --stat`), current RTL revision (the RTL dir is referenced by
   sim/dut.f; "stub DUT" if dut.f still selects the generated stub).
2. Recent evidence: verif_matrix.yaml records (newest first; or
   `make -C sim matrix` for the summary), session sidecars in dv/status/,
   and wrapper verdict JSONs under runs/ where a dv wrapper exists; note
   pass/fail, seeds, configs, and whether evidence exists for the
   uncommitted work.
3. Vplan (docs/vplan.md): item counts by status; items marked
   `[design-intent — spec silent]` still open; completeness-matrix rows
   that are empty or unjustified-N/A; revision anchors vs the actual
   RTL revision (stale = flag it).
4. Governance queues: pending entries in dv/cov/exclusion_requests.md;
   check-ID inventory in docs/CLAUDE.md vs dv/lists/chkq.list (checks
   with no negative test = unqualified).
5. Health signals: does the sanity list exist and when did it last pass
   (from verif_matrix.yaml / run artifacts, do not re-run); any
   CHKQ_PATH/CHKQ_BLIND in recent verdicts/logs.

## Report (one screen, evidence-cited, no inflation)
**Done** — merged/committed on this branch, each with its verdict
reference. Work without verdicts is listed as UNVERIFIED, not done.
**In flight** — uncommitted diffs, drafted-not-reviewed items,
unanswered designer questions.
**Risks / blocked** — pre-existing failures, stale vplan anchors,
pending exclusions, unqualified checks, matrix holes.
**Next actions** — ranked list, each as a concrete command with a
one-line why. Priority heuristic (adapt with judgment, say so when you
deviate): 1) pre-existing failures → `/triage-failure ...` (nothing
built on a broken baseline is trustworthy); 2) design-intent
confirmations blocking closable items (human task: chase the designer);
3) unqualified checkers → `/qualify-checkers ...` (unproven checks
undermine every green result); 4) completeness-matrix holes →
extend vplan; 5) open vplan items in milestone order →
`/close-vplan-item ...`; 6) coverage closure → `/close-coverage-holes`
(only if cov data is current for this RTL revision).

Rules: every claim cites the file/verdict it came from; unknowns are
stated as unknowns; if the picture is too incomplete to advise (no
vplan, no runs), say exactly what to create first instead of guessing.
This briefing never substitutes for the CI gate or human review — say
so if asked to "confirm we're done".
