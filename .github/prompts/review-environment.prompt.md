---
description: Audit a delivered verification environment (9 axes, verif-env-review)
agent: dv-reviewer
---
Audit the ${input:ip} verification environment using the verif-env-review
skill: all nine axes over the project root (testbench code via its
references/testbench-code-review.md + deprecation-lint scripts/lint.py,
then TB top, build, regression, coverage, SVA, vplan traceability, CI gates,
reproducibility). Read-only. Output the human scorecard then the JSON verdict
with milestone_ready; findings carry file:line and a fix.
