---
agent: dv-checker-writer
description: 'Write negative tests qualifying existing checkers (Mode B)'
argument-hint: '<checker scope, e.g. axi scoreboard> [ip]'
---
Mode B session: qualify the existing checkers in scope ${input:scope} on
IP ${input:ip:ip name}. Inventory the check IDs, present the qualification
matrix plan (check ID -> proposed injection) and STOP for my approval,
then implement negative tests per Gate 4 rules and report the matrix with
CHKQ_OK verdicts.
