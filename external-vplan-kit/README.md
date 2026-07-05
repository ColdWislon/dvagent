# External Vplan Drafting Kit

Why this exists: VS Code Copilot agent mode cannot SEE PDFs — text
extraction (pdftotext) works for prose but destroys register maps,
tables, and timing diagrams, which is where a hardware spec's hardest
content lives. Vplan drafting is a once-per-block, human-reviewed task
with no compile/sim loop, so it does not need to run inside VS Code:
the repo file <ip>/docs/vplan.md is the interface, and the agents
consume it identically whoever drafted it.

## Workflow (option A — external LLM with PDF vision)

1. PREREQUISITE — data policy: uploading specs to a second cloud vendor
   needs the same IT/legal approval your Copilot agreement got. Confirm
   before the first upload. [TEAM: record the approved vendor(s) here.]
2. Open a conversation/project in the approved PDF-capable LLM (e.g.
   Claude). Paste VPLAN_DRAFTING_PROMPT.md as the first message, attach
   the spec PDF, state IP name + scope + the clock/reset/CDC inventory
   (from the block's docs/CLAUDE.md).
3. The model stops after Phase 1 (section inventory) — review it, then
   let it draft. Answer its designer/ambiguity questions as they come.
4. Take the produced markdown, commit it as <ip>/docs/vplan.md on a
   branch, open an MR. The dv-reviewer and the human review audit it
   (format, completeness matrix, design-intent markers). Only after
   merge do agents close work against it.
5. Spec revision later? Re-run with the delta pages and EXTEND the
   vplan (new IDs, never renumber) — or use /generate-vplan in VS Code
   for text-only addenda.

## Fallbacks

- Option B (future): API pipeline regenerating drafts in CI — requires
  the LLM API procurement deferred at the tooling decision; revisit if
  vplan volume grows.
- Option C (no external vendor): /generate-vplan in VS Code on the
  pdftotext extraction, plus the engineer attaches SCREENSHOTS of every
  flagged table/figure page to Copilot chat (vision-capable model
  required). Slower, acceptable for text-dominant specs.

Keep VPLAN_DRAFTING_PROMPT.md in lockstep with the in-repo format
(repo-templates/ip/docs/vplan.md) and the vplan-common-topics skill —
they are the same contract in two packagings; drift between them will
surface as reviewer findings on externally-drafted vplans.
