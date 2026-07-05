---
agent: dv-test-writer
description: 'Implement and verify a vplan item end-to-end'
argument-hint: 'VP-xxx [ip]'
---
Implement vplan item ${input:item:VP-xxx} for IP ${input:ip:ip name}.
Follow your full workflow: intent summary, pattern survey, implementation,
compile + 3-seed sim loop, coverage-bin confirmation, final report with the
vplan item marked closable.
