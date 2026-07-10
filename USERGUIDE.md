# DV Agents — Engineer Quick Start

For verification engineers using the Copilot agent pack. Ten minutes to
read; the rest you learn by doing.

## What this is, in 30 seconds

Seven specialized Copilot agents built around our UVM environments —
uvm-gen-generated testbenches (`<ip>_verif/`) driven through their
`sim/Makefile`: one (`dv-env-architect`) bootstraps NEW environments from
the uvm-gen generator; the other six work inside existing ones — they
write tests, stimulus, and checkers, close coverage, and triage failures —
always closing the loop with real compile/sim verdicts, never by claiming
success. You drive them from VS Code chat; you
review and merge everything. The no-shortcut rules (RTL read-only, no
checker weakening, no exclusions) are enforced by the CI gate on every
MR — agent-authored or not.

The flow in one line: `make compile`, `make run TEST=<test> SEED=<n>`,
`make waves`, `make regress`, `make matrix` — from `<ip>_verif/sim/`.
A run's verdict is its exit status, the `cfg_tool: PASS/FAIL` line, and
the record it appends to `verif_matrix.yaml`.

## One-time setup

1. VS Code with **Remote-SSH into your farm/interactive node** (where
   `xrun` resolves). Agent mode runs commands on that machine — a
   local-laptop window cannot simulate anything.
2. Copilot extension signed in, agent mode available. Check out a repo
   branch containing the `.github/` pack; reload the window
   (`Developer: Reload Window`). The agents appear in the Chat view's
   agent picker (dropdown, not `@`).
3. Terminal approval: allow-list `make ` (and `git diff`/`git log`) in
   `chat.tools.terminal.autoApprove` — workspace settings ship this.
   Do NOT blanket-approve terminal commands on farm hosts.
4. Work in your own **git worktree** per agent session — parallel agents
   sharing a snapshot directory will corrupt each other's builds.
5. Brand new to the repo (or inheriting a block)? Read the environment's
   `GETTING_STARTED.md` (no Copilot required), then type `/start-here`
   in Copilot chat: a read-only guided session that tours the
   environment, runs the smoke test with you, and hands you ranked
   first tasks.

The flow's facts (seeds, plusargs, run artifacts, what is and isn't
wired) live in `.github/skills/dv-wrapper/SKILL.md` — its "no-wrapper
default" section documents this make flow and is already filled in.
Site option: teams that layer a `dv` wrapper CLI on top of the Makefile
run `/learn-dv-wrapper` once to capture its specifics there; everything
in this guide otherwise stays the same.

## Which agent for what

| You want to... | Use | Entry point |
|---|---|---|
| First day on the repo / guided onboarding | (read-only guide) | `/start-here` |
| Start a NEW IP environment (YAML → uvm-gen skeleton) | dv-env-architect | `/generate-environment <ip>` |
| Close a vplan item (test + covergroup) | dv-test-writer | `/close-vplan-item VP-xxx <ip>` |
| Build reusable sequences / constraints | dv-stim-writer | `/build-stimulus <scenario> <ip>` |
| Add new checks (scoreboard/model/SVA) | dv-checker-writer | `/write-checkers <spec §> <ip>` |
| Qualify existing checkers (negative tests) | dv-checker-writer Mode B | `/qualify-checkers <scope> <ip>` |
| Close coverage holes | dv-coverage-closer | `/close-coverage-holes <ip>` |
| Debug a failing test | dv-debug | `/triage-failure <test> --seed N <ip>` |
| Self-review before opening an MR | dv-reviewer | `/pre-mr-review` |
| Draft a vplan from a PDF spec | see note below | `/generate-vplan` or external kit |
| Know where you stand + what to do next | (read-only briefing) | `/status` |

Vplan drafting note: Copilot cannot SEE PDFs. `/generate-vplan` works
on text-dominant specs (pdftotext extraction); for register-map/
timing-diagram-heavy specs, use `external-vplan-kit/` with an approved
PDF-vision LLM and commit the reviewed result — agents consume the
vplan identically either way.

Rule of thumb for the test/stim boundary: combining existing sequences to
close an item = test-writer; creating a new sequence class others will
reuse = stim-writer. The agents know this rule and will hand off to each
other — let them.

Start of day, back from vacation, or inheriting a block: `/status`
gives a read-only briefing — done (with verdict evidence), in flight,
risks, and ranked next actions as ready-to-run commands.

## A typical session (closing VP-MY_IP-041)

1. Fresh worktree, fresh chat, pick dv-test-writer:
   `/close-vplan-item VP-MY_IP-041 my_ip`
2. The agent reads the vplan item and spec ref, surveys the existing
   sequences (`seq_lib/`, `agents/*/`), states its plan. Sanity-check the
   plan — 30 seconds now saves an hour later.
3. It implements, then loops: `make compile` → `make run TEST=... SEED=...`
   for 3 seeds → coverage-bin check. You'll see every verdict (the
   `cfg_tool: PASS/FAIL` lines and matrix records); it may ask you a
   question if it hits an unknown (answer it — answers persist).
4. It produces the session report (files, verbatim verdicts, seeds,
   what was NOT verified) and offers the reviewer handoff. Take it.
5. Read the diff yourself. You are the author of record: the agent
   proposed, you merge. Attach the session report to the MR — the DoD
   requires it and the CI gate checks the rest.

## The rules that will stop you (by design)

- **RTL and existing checkers are read-only.** The agent will refuse to
  "just relax the compare" or "demote that error" — and so does the CI
  gate, for humans too. If a checker looks wrong, the agent documents
  the argument; a human owns that change.
- **Exclusions are proposals.** Agents append to
  `dv/cov/exclusion_requests.md`; a human applies them.
- **No claim without a verdict.** If an agent tells you something passes
  without showing the evidence — the UVM report summary /
  `** UVM TEST PASSED **` marker, or the `verif_matrix.yaml` record —
  that's a defect: call it out (and the reviewer flags it).
- **Forces exist only in chkq negative tests**, via the injector, with
  coverage off. A `force` anywhere else fails review and the gate.
- **New checkers need your sign-off** — the checker-writer stops at its
  plan gate and waits for you, and its MRs are flagged for explicit
  approval. A `CHKQ_BLIND` regression failure means a checker went
  blind: treat it like a failing test, not noise.

## When it goes wrong

- **Thrashing** (repeated similar failed attempts): stop the session.
  Agents have budgets (6 sims for debug, 8 for env bring-up, 10–15
  elsewhere) and must
  summarize-and-stop at budget — if one circumvents that, that's
  feedback we want.
- **Unparseable or surprising flow output** (no UVM summary, no matrix
  record, a make error the agent can't explain): the agent should stop
  and ask, not improvise. If the site's flow itself changed, update the
  flow reference (`.github/skills/dv-wrapper/SKILL.md`, or re-run
  `/learn-dv-wrapper` where a wrapper is involved).
- **The agent refuses something you think is legitimate**: it will cite
  the rule. If you disagree with the rule, raise it with the methodology
  owners — don't prompt-wrestle the agent into compliance; the CI gate
  catches it anyway.
- **Wrong or low-quality output**: just discard the worktree. Cheap
  disposal is the point of worktrees.
- **"It worked yesterday" / sudden failures without TB changes**: the
  DUT moved. Use `/triage-failure` — its first step is what-changed
  (RTL git log since the last pass in `verif_matrix.yaml`, optional
  bisect). Never let an agent "fix" the TB to match changed RTL ports
  without the change note; if it asks you for one, that's the process
  working.

## Habits that get good results

- One item per session; fresh chat per task. Long mixed sessions degrade.
- Give context the files can't: "this block has a known quirk on X",
  "reuse the pattern from <test>". The per-IP `docs/CLAUDE.md` should
  hold durable context — if you repeated something twice, put it there.
- Review plans before code, diffs before merge. The agent is a fast,
  knowledgeable, occasionally overconfident junior engineer: treat its
  MRs with exactly the scrutiny that description deserves.
- Never paste raw sim logs into chat; point the agent at the log path
  (`sim/logs/<test>_<config>_s<seed>.log`) — it has the log-triage
  script for that.

## Your responsibilities (the short version)

You review every diff, you own every merge, you sign off checker changes,
you answer the agents' flow questions honestly, and you attach session
reports to MRs. Periodic human audits of merged MRs are part of the
methodology — clean reports are trusted because we verify they deserve it.

Questions, false refusals, gate false-positives, ideas:
[TEAM: feedback channel / owner here].
