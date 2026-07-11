---
description: Architect and generate a new UVM environment from a spec (dv-env-architect)
agent: dv-env-architect
---
Architect a new UVM verification environment for ${input:ip} from its spec and
interface list. Follow the three-gate protocol: architecture plan first (STOP
for approval), then generate from the authoring skills, then smoke proof on 2
seeds. At Gate 2, if the `uvm-gen` CLI is available (template/uvm-gen/uvm_gen.py — see
your agent definition's bootstrap option), generate the approved skeleton
with it and customize, instead of hand-writing every file. Mark every stubbed
compare as PLACEHOLDER-CHECK and end with the dv-checker-writer handoff.
