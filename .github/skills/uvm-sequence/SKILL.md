---
name: uvm-sequence
description: >-
  Create a UVM sequence conforming to house methodology. Use whenever the user
  wants to write, add, create, or scaffold a sequence, stimulus, a traffic
  generator, or the body that produces transactions on a sequencer -- even if
  the word "skill" is never used. Covers registration, body(), item generation
  via create + start_item/finish_item, and randomization.
---

# Write a UVM sequence

A sequence generates transactions on a sequencer. It owns stimulus intent; it
does not own objections (the test does) and does not touch pins.

## Inputs to confirm
1. Sequence name -> class `<feat>_seq`.
2. Item type (`<proto>_item`) and target sequencer type.
3. Scenario: field patterns, ordering, count, and any randomization knobs.

## Procedure
1. Create `<feat>_seq.sv` (`.sv` in this infra) from `assets/templates/sequence.svh.tmpl`.
2. Register with `` `uvm_object_utils ``; parameterize on the item type.
3. In `body()`, generate items with `create` + `start_item` +
   `randomize() with {...}` + `finish_item`. Expose knobs as `rand` class
   members so the sequence composes under a virtual sequence.

## Hard rules (never violate)
- Extends `uvm_sequence#(<proto>_item)`; registered with `` `uvm_object_utils ``.
- Items created via the factory (`::type_id::create`), never `new()`.
- Plain (non-virtual) sequences hold no objections; objections live in tests
  and virtual sequences only (team standard).
- No virtual interface access and no `#` delays inside the sequence.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] Produces only legal stimulus; `randomize()` succeeds.
- [ ] Knobs exposed as `rand` members; reusable under a virtual sequence.
- [ ] No pin access, no `#` delay, no self-owned objection when nested.

Naming and deprecation rules are enforced by the `naming-conventions` and
`deprecation-lint` skills; `verif-env-review` checks this.
