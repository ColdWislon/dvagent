---
agent: dv-checker-writer
description: 'Author new checkers under the plan-approval + fault-injection protocol'
argument-hint: '<spec section or VP-xxx> [ip]'
---
Author the checking logic for: ${input:target} on IP ${input:ip:ip name}.
Start with Gate 1 only: produce the spec-derived check plan table and STOP
for my approval before writing any code. Then proceed gate by gate through
clean-pass baseline and fault-injection evidence.
