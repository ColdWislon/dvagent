---
agent: 'agent'
tools: ['search', 'execute/runInTerminal', 'execute/getTerminalOutput', 'read/terminalLastCommand', 'read/terminalSelection', 'edit', 'vscode/askQuestions']
description: 'Interview session: resolve the UNKNOWNs in the dv-wrapper skill'
---
Onboarding session for the flow knowledge base
(.github/skills/dv-wrapper/SKILL.md).

0. First check whether a team `dv` wrapper exists (`command -v dv`). If
   NOT: this repo runs on the uvm-gen make flow, whose facts are already
   recorded in the skill's "No-wrapper default" section — there is
   nothing to interview. Say so, and offer instead to record any
   site-specific facts the engineer wants persisted (coverage flow,
   regression farm, module loads) in the Learned facts log. Continue
   below only if the wrapper exists.
1. Read the skill file and list every section marked UNKNOWN.
2. Resolve as many as possible READ-ONLY: `dv --help`, `dv <subcmd>
   --help` for each subcommand. Do not run compiles or sims unless I
   approve it explicitly.
3. For each remaining UNKNOWN, ask me via #tool:vscode/askQuestions —
   batch related questions, offer concrete options, one topic at a time
   (plusarg passing, seed behavior, run dirs, chkq access config,
   coverage subcommand status).
4. For any answer that can be cheaply verified (e.g. run one `dv sim` of
   the smoke test and inspect the verdict shape), propose the
   verification run and execute it on my approval; verified facts are
   marked [confirmed <date>], engineer-stated ones [learned <date>].
5. Update the skill file: replace resolved UNKNOWN blocks with the facts,
   append entries to the learned-facts log, and finish with a summary of
   what remains unresolved and what that blocks (e.g. "cov verdicts
   unconfirmed -> coverage-closer not deployable").
