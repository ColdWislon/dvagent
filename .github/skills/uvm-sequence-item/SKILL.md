---
name: uvm-sequence-item
description: >-
  Create a UVM sequence item (transaction) conforming to house methodology. Use
  whenever the user wants to write, add, create, or scaffold a transaction, a
  sequence item, a bus/packet data class, or the payload a driver drives and a
  monitor reconstructs -- even if the word "skill" is never used. Covers object
  registration, rand fields, constraints, and copy/compare/print behaviour.
---

# Write a UVM sequence item

A transaction is data only: randomizable fields, legality constraints, and
convenience printers. No components, no logic, no interface access.

## Inputs to confirm
1. Protocol / packet name -> class `<proto>_item` (or `<proto>_seq_item`).
2. Fields and their widths/types; which are `rand`.
3. Legality constraints (encodings, alignment, ranges, inter-field relations).

## Procedure
1. Create `<proto>_item.svh` from `assets/templates/seq_item.svh.tmpl`.
2. Register with `` `uvm_object_utils `` (or `` `uvm_object_utils_begin/end `` with
   `` `uvm_field_* `` if using field automation).
3. Declare `rand` fields; add named `constraint` blocks for legality.
4. Provide `convert2string`; for hot-path items prefer explicit `do_copy` /
   `do_compare` over field macros (faster, no reflection).

## Hard rules (never violate)
- Extends `uvm_sequence_item`, never `uvm_transaction` directly.
- `` `uvm_object_utils(<proto>_item) `` registration is mandatory.
- No virtual interface, no `#` delay, no protocol logic inside the item.
- Every legality rule is a named `constraint`, not hidden in a sequence.

## Definition of Done
- [ ] Compile clean: `make compile` (wrapper: `dv compile <ip>`) — never invoke xrun ad hoc.
- [ ] `randomize()` succeeds and only produces legal values.
- [ ] `convert2string` prints all fields; `copy`/`compare` behave correctly.
- [ ] No interface / timing / logic beyond data + constraints + helpers.

Naming and deprecation rules are enforced by the `naming-conventions`
and `deprecation-lint` skills; `verif-env-review` checks this against them.
