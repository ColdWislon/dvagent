---
name: naming-conventions
description: >-
  Apply and check house naming conventions for SystemVerilog/UVM code. Use
  whenever the user wants to name, rename, or review the names of classes,
  files, instances, interfaces, config objects, sequences, tests, or message
  IDs -- and whenever another UVM skill or a review needs the canonical naming
  ruleset. This is the single source of truth other skills point to.
---

# Naming conventions (house ruleset)

Subordinate to the team `uvm-coding-standard` skill: where the two differ,
`uvm-coding-standard` wins. This skill adds the naming detail layer.

Apply these when authoring; check them when reviewing. `<proj>`/`<proto>` are
the project and protocol prefixes; adapt to the house prefix.

## Ruleset

| Element | Convention | Example |
|---|---|---|
| Class | `<proto>_<role>` | `axi_master_agent` |
| File | snake_case = class name, one class per file | `axi_master_agent.svh` |
| Component instance | `m_<role>` | `m_master_agent`, `m_driver` |
| Sequencer handle | `m_<role>_seqr` | `m_master_seqr` |
| Virtual interface | `<proto>_if` | `axi_if` |
| Config object | `<x>_cfg` (`<proto>_agent_cfg`, `<proj>_env_cfg`) | `axi_agent_cfg` |
| Transaction | `<proto>_item` | `axi_item` |
| Sequence | `<feat>_seq` | `burst_wr_seq` |
| Virtual sequence | `<feat>_vseq` | `smoke_vseq` |
| Test | `<feat>_test` | `burst_wr_test` |
| Check message ID | STABLE unique ID per check, `SCBD_*`/`CHK_*` style | `` `uvm_error("SCBD_DATA_CMP", ...) `` |
| Info message ID | `get_type_name()` (or house ID scheme) | `` `uvm_info(get_type_name(), ...) `` |
| `define/macro guard | `<FILE>_SVH` upper-snake | `AXI_ITEM_SVH` |
| Package | `<proj>_<layer>_pkg` | `axi_agent_pkg` |

## Rules

- File name must equal the class name; one primary class per file (tightly
  coupled helpers may share a file).
- No abbreviations outside the approved protocol prefixes.
- Handles are prefixed `m_`; local variables are not.
- Check IDs are API: chkq negative tests and triage bucketing key on them.
  One stable, unique ID per distinct check (`SCBD_DATA_CMP`, `SCBD_ORDER`);
  renaming one is a breaking change (chkq list updated in the same MR).
- Info messages use `get_type_name()` so logs filter cleanly per component.
- Everything lives in a named package; no compilation-unit-scope classes.

## Review output
Report each violation as: `{rule_id: "naming.<element>", severity: "warn",
file, line, message, fix}`. Naming issues are `warn` unless they break
compilation (`error`).
