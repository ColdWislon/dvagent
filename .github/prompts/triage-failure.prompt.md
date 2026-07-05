---
agent: dv-debug
description: 'Root-cause one failing test with same-seed discipline'
argument-hint: '<test> --seed <N> [ip]'
---
Triage the failure: test ${input:test}, seed ${input:seed}, IP ${input:ip}.
Reproduce the exact seed first, then follow the triage decision tree with
one hypothesis per iteration and the 6-sim budget. Outcome must be either
a verified TB fix or an RTL-suspect report — never a weakened check.
