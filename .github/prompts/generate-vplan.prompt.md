---
agent: 'agent'
tools: ['search', 'edit', 'execute/runInTerminal', 'execute/getTerminalOutput', 'read/terminalLastCommand', 'read/terminalSelection', 'vscode/askQuestions']
description: 'Draft a vplan from a PDF spec in the team format (human approves before use)'
argument-hint: '<ip> <spec.pdf path> [section/page range]'
---
Draft the verification plan for IP ${input:ip} from the PDF spec at
${input:spec:path/to/spec.pdf}, scope ${input:scope:all sections}.
Output: the env root's docs/vplan.md in the exact team format
(table columns: ID | Spec ref |
Requirement | Coverage mapping | Check mapping | Status).

## Phase 0 — Suitability check
This flow relies on TEXT extraction and degrades on table/diagram-heavy
specs. Skim the extraction first (Phase 1.3): if register maps, timing
diagrams, or dense tables dominate the in-scope sections, STOP and tell
the engineer to use external-vplan-kit/ (a PDF-vision LLM) instead of
producing a low-confidence draft here.

## Phase 1 — PDF ingestion (you cannot read PDF binaries directly)
1. Check for an existing extraction next to the PDF
   (<spec>.txt / <spec>_extracted/). If present and newer than the PDF,
   reuse it.
2. Otherwise extract with page markers preserved:
   `pdftotext -layout ${input:spec} <workdir>/spec.txt`
   (if pdftotext is unavailable, ask me before installing anything or
   trying another tool). For specs over ~80 pages, extract and process
   in chunks: `pdftotext -layout -f <first> -l <last> ...`.
3. Sanity-check the extraction: read the table of contents and one known
   section. If the text is garbled (columns interleaved, tables
   destroyed), STOP and show me a sample — a vplan drafted from corrupt
   extraction is worse than none.
4. TABLES AND FIGURES DEGRADE in text extraction. Any item whose source
   is a table, timing diagram, or figure gets the marker
   `[verify vs fig/table x.y]` in its Requirement cell — I must check
   those against the real PDF.

## Phase 2 — Drafting rules (non-negotiable)
1. SPEC-DERIVED ONLY. Every item cites section AND page from the
   extraction you actually read (e.g. `§4.3.2 p.87`). Never draft items
   from general protocol knowledge dressed with invented refs.
2. ONE VERIFIABLE REQUIREMENT PER ITEM: intent (behavior + corners),
   phrased so a test either exercises it or doesn't. No implementation
   language. Split compound requirements — an "and/or" usually means two
   items.
3. ID scheme: VP-${input:ip}-nnn, numbered in spec order, never reused.
   If docs/vplan.md already exists, EXTEND it (continue numbering,
   touch no existing rows) — never regenerate over human-reviewed items.
4. MAPPINGS ARE PROPOSALS: propose covergroup/bin and check-ID names per
   the naming standard, prefixed "(proposed)" when the artifact does not
   exist yet. An item with no plausible check mapping is flagged
   UNVERIFIABLE-AS-WRITTEN in the open-questions list.
5. Status = open for everything. You do not close items.
6. AMBIGUITY GOES TO HUMANS: every spec ambiguity, contradiction, or
   unstated corner becomes an "Open questions" entry (with §/page). Ask
   blocking ones via #tool:vscode/askQuestions; list the rest.

## Phase 3 — Cross-cutting sweep (spec sections are NOT enough)
Specs describe function; reset, clocking, CDC, and their siblings live
in implementation and are routinely spec-silent. After the spec sweep,
walk EVERY category of the vplan-common-topics skill:
- Applicable + spec covers it → normal items (rules above apply).
- Applicable + spec SILENT → draft the items anyway from the checklist's
  intent patterns, mark each `[design-intent — spec silent]`, and add a
  designer question to Open questions. These items exist to force the
  intent to be documented — they are not closable until it is.
- Not applicable → an explicit `N/A — <justification>` (architecture
  fact, flow scope, or program decision; cite it).
Use the block's CLAUDE.md (clock/reset domains) and, if available, the
CDC report to instantiate categories 1–3 concretely; if neither exists,
ask me for the clock/reset/CDC inventory via #tool:vscode/askQuestions
before drafting those sections.
Fill the "Cross-cutting completeness matrix" in the vplan — every
category resolved, no empty rows.

## Phase 4 — Workflow and gates
Show me the section inventory with expected item counts and WAIT for my
go. Draft spec sections first, then the Phase 3 sweep. Finish with: a
self-check pass against rules 1–6, the completeness matrix (flag any
category you could not resolve), the count of `[verify vs fig/table]`
and `[design-intent]` markers, and the open questions. State explicitly
that this vplan is a DRAFT requiring engineer review before any agent
closes work against it — an agent-drafted vplan judged only by agents
is circular.
