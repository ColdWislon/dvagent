---
name: uvm-vsequence
description: >-
  Create a UVM virtual sequence conforming to house methodology. Use whenever
  the user wants to write, add, create, or scaffold a virtual sequence, a
  multi-agent scenario, or the orchestration layer that starts sub-sequences on
  several sequencers through a virtual sequencer -- even if the word "skill" is
  never used. Covers p_sequencer declaration, sub-sequence launch, and reuse.
---

# Write a UVM virtual sequence

A virtual sequence coordinates several agents' sequences through the virtual
sequencer. It starts sub-sequences on sub-sequencer handles; it never touches
pins and never generates items directly.

## Inputs to confirm
1. Scenario name -> class `<feat>_vseq`.
2. Virtual sequencer type and the sub-sequencer handles it exposes.
3. Sub-sequences to run and their ordering / concurrency.

## Procedure
1. Create `<feat>_vseq.svh` from `assets/templates/vsequence.svh.tmpl`.
2. Declare the typed virtual sequencer with `` `uvm_declare_p_sequencer ``.
3. In `body()`, create each sub-sequence via the factory and `start` it on the
   matching `p_sequencer.m_<role>_seqr`. Use `fork/join` for concurrent traffic.

## Hard rules (never violate)
- Extends the vseq base; declares `p_sequencer` via
  `` `uvm_declare_p_sequencer(<vseqr_type>) ``.
- Starts sub-sequences on sub-sequencer handles only; no direct item generation.
- No virtual interface access and no `#` delays.
- Objections may be held by the test or by this virtual sequence (team
  standard), never by drivers/monitors; if the vseq raises, it drops
  symmetrically and the test does not double-hold.

## Definition of Done
- [ ] `dv compile <ip>` verdict clean (never call xrun directly).
- [ ] Starts each sub-sequence on the correct sub-sequencer.
- [ ] Concurrency/ordering matches the intended scenario.
- [ ] Reusable at subsystem/SoC level (no block-specific hard-coding).

Naming and deprecation rules are enforced by the `naming-conventions` and
`deprecation-lint` skills; `verif-env-review` checks this.
