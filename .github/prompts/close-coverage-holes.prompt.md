---
agent: dv-coverage-closer
description: 'Rank and close the top functional coverage holes for an IP'
argument-hint: '[ip]'
---
Run a coverage-closure session on IP ${input:ip:ip name}.
Start from the current merged database, produce the classification table
(A/B/C/D) before touching any code, then work A/B holes by weight with a
per-hole delta ledger. C and D go to proposals only.
