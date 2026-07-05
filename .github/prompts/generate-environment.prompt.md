---
description: Architect and generate a new UVM environment from a spec (dv-env-architect)
agent: dv-env-architect
---
Architect a new UVM verification environment for ${input:ip} from its spec and
interface list. Follow the three-gate protocol: architecture plan first (STOP
for approval), then generate from the authoring skills, then smoke proof on 2
seeds. Mark every stubbed compare as PLACEHOLDER-CHECK and end with the
dv-checker-writer handoff.
