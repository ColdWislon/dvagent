# Vplan Drafting Prompt (external LLM, PDF-native)

[Usage: paste this entire file as the first message in a Claude (or other
PDF-capable LLM) conversation/project, attach the spec PDF, and state the
IP name and scope. Everything the model needs is embedded — it has no
access to the repository.]

---

You are drafting a hardware verification plan (vplan) from the attached
PDF specification, for a SystemVerilog/UVM verification team. Your output
is a DRAFT for engineer review — it will be committed to a repository
where automated agents close work against it, so format discipline and
honesty about uncertainty matter more than volume.

## Output format (exact)

One markdown file. Structure:

```
# <IP_NAME> Verification Plan

| ID | Spec ref | Requirement (verifiable statement) | Coverage mapping | Check mapping | Status |
|----|----------|-------------------------------------|------------------|---------------|--------|
| VP-<IP>-001 | §x.y p.NN | ... | (proposed) cg_<n>.cp_<n> bins [...] | (proposed) CHK_... | open |

## Cross-cutting completeness matrix

| Topic | Resolution |
|-------|------------|
| Reset | VP-<IP>-0xx..0yy |
| Clocks | N/A — <justification> |
| ...all 13 topics, no empty rows... |

## Open questions
1. [§ref] ...
```

## Drafting rules (non-negotiable)

1. SPEC-DERIVED with real references. Every item cites section AND page
   you actually read in the attached PDF. Read tables, register maps,
   and timing diagrams directly — they are first-class sources. Never
   pad with generic protocol knowledge dressed as spec content; if you
   use domain knowledge to INTERPRET the spec, the requirement must
   still be anchored to a real §/page.
2. ONE VERIFIABLE REQUIREMENT PER ITEM: intent (behavior + corners),
   phrased so a test either exercises it or doesn't. No implementation
   language ("write a sequence that..." is forbidden). Split compound
   requirements — an "and/or" usually means two items.
3. ID scheme: VP-<IP>-nnn, numbered in spec order, never reused.
4. MAPPINGS ARE PROPOSALS: propose covergroup/bin names
   (cg_<feature>.cp_<point>) and check IDs (CHK_<IP>_<CHECK> /
   SCBD_<IP>_<CHECK>), each prefixed "(proposed)". An item where no
   check could plausibly judge correctness is flagged
   UNVERIFIABLE-AS-WRITTEN and listed in Open questions.
5. Status = open for every item. You close nothing.
6. AMBIGUITY GOES TO HUMANS: every spec ambiguity, contradiction,
   TBD, or unstated corner becomes a numbered Open question with §/page.
   Ask the blocking ones before drafting the affected section; list the
   rest.

## Phase 1 — Inventory (stop for approval)

Read the table of contents and skim the document. Present: the section
inventory in scope, expected item count per section, the list of
register-map and timing-diagram pages (these need extra care), and any
sections you propose to exclude with reasons. WAIT for the engineer's
go before drafting.

## Phase 2 — Spec sweep

Draft section by section per the rules. For content sourced from a
table, register map, or timing diagram, add the marker
`[from table/fig x.y]` in the Requirement cell — reviewers give those
rows extra scrutiny.

## Phase 3 — Cross-cutting sweep (the spec is not enough)

Specs describe function; the following topics live in implementation
and are routinely spec-silent. Resolve EVERY category as items or an
explicit `N/A — <justification>` in the completeness matrix
("not thought about" is not N/A). Where the spec is silent but the
topic applies, DRAFT the items anyway from the patterns below, mark
each `[design-intent — spec silent]`, and add a designer question —
these items exist to force undocumented intent to become documented,
and are not closable until it is.

If the engineer has not provided the clock/reset/CDC inventory, ASK for
it before drafting categories 1–3.

1. **Reset**: mid-traffic reset (in-flight transactions, clean protocol
   reinit, no residual state); outputs during/after reset; minimum
   duration; multiple reset domains (ordering, partial reset); soft vs
   hard reset; post-reset first transaction of each type.
2. **Clocks**: domain inventory, ratio extremes both directions,
   non-integer ratios, clock gating transparency, dynamic frequency
   change, absent optional clocks.
3. **CDC/resynchronizers** (functional behavior; structural CDC is the
   static tool's job): crossing inventory; single-bit pulse width vs
   destination clock; gray-coded multi-bit counters (one bit per edge);
   handshake crossings under stall/reset; async FIFO flags at ratio
   extremes, overflow/underflow, one-side-only reset; max-rate
   back-to-back events per crossing.
4. **Interrupts/events**: assertion conditions, level vs pulse, clear
   mechanisms and clear-vs-new-event races, mask/enable with pending,
   coalescing.
5. **Registers**: reset values, per-field access policies, reserved
   fields, side-effect registers, protected access, backdoor/frontdoor
   consistency.
6. **Error handling & illegal stimulus**: every error response's
   generation/propagation/logging/RECOVERY; illegal opcodes/addresses/
   lengths; timeouts.
7. **Capacity/boundaries**: FIFO full/empty/almost flags at and across
   thresholds, overflow/underflow, counter wrap, max outstanding,
   zero/min/max sizes.
8. **Backpressure/flow/perf**: sustained stall per output, starvation
   per input, arbitration fairness, QoS, spec'd throughput/latency.
9. **Low power** (if applicable): gate entry/exit transparency, domain
   isolation/retention, wake events.
10. **Concurrency/stress**: all interfaces simultaneously active,
    cross-feature random mixes, soak.
11. **Configuration space**: verified parameter combinations and the
    explicit exclusion list.
12. **Security/protection** (if applicable): access filtering,
    secure/non-secure separation, information leakage via status.
13. **Debug/DFT** (if in scope): observability/bypass, or N/A with the
    program decision.

## Phase 4 — Close out

Self-check against rules 1–6, then report: item count per section, the
completeness matrix, counts of `[from table/fig]` and `[design-intent]`
markers, unverifiable items, open questions. End with, verbatim:
"This vplan is a DRAFT. It requires engineer review before any agent
closes work against it, and design-intent items require written intent
confirmation before closure."
