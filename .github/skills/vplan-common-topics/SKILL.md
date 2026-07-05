---
name: vplan-common-topics
description: Cross-cutting verification topics every vplan must resolve — reset, clocks, CDC/resynchronizers, interrupts, registers, errors, capacity, backpressure, low power, concurrency, configuration. Use during vplan generation/review; every category ends as items or a justified N/A.
---

# Cross-Cutting Vplan Topics (mandatory sweep)

Specs describe function; these topics live in implementation and
integration, so a spec-section sweep misses them. Every vplan carries a
completeness matrix resolving EVERY category below as either item IDs or
`N/A — <justification>`. Items the spec is silent on are drafted anyway,
marked `[design-intent — spec silent]`, and raised as designer questions:
verifying against undocumented intent requires making the intent
documented.

## 1. Reset
- Assertion mid-traffic: transactions in flight when reset asserts —
  interface protocol state cleanly reinitialized (e.g. AXI VALID low
  rule), no residual transactions/credits/pointers after deassert.
- Output values during reset and at first cycle after deassert.
- Minimum reset duration; behavior on too-short pulse if spec'd.
- Multiple reset domains: ordering/skew between domain resets; partial
  reset (one domain reset while the other runs).
- Soft/functional reset vs hard reset differences; state surviving each.
- Post-reset first transaction of each type (classic corner).
Typical checks: `CHK_RST_IF_STATE`, scoreboard flush semantics.
Coverage: reset asserted in {idle, mid-burst, error-pending, full-FIFO}.

## 2. Clocks
- Domain inventory with legal frequency ranges and ratios; verify at
  ratio extremes BOTH directions (fast→slow, slow→fast), equal, and
  non-integer ratios if legal.
- Clock gating: traffic across gate/ungate events; no protocol loss.
- Dynamic frequency change during operation (if supported).
- Clock-absent behavior for optional domains.
Coverage: configuration bins per verified ratio (usually directed
configs, not random).

## 3. CDC / resynchronizers
Structural CDC (synchronizer presence/schemes) belongs to static CDC
tools — the vplan covers FUNCTIONAL behavior of each crossing:
- Crossing inventory matching the CDC report; one item group per
  crossing type.
- Single-bit sync: pulse width vs destination clock (no missed events
  at worst ratio); no double-sampling of intended-single events.
- Multi-bit: gray-coded counters/pointers only change one bit per edge
  (SVA candidate); handshake crossings complete under stall and reset.
- Async FIFOs: full/empty flag correctness at ratio extremes, no
  overflow/underflow, pointer behavior across reset of one side only.
- Back-to-back events across a crossing at maximum rate.
- Data stability where qualifier-based schemes require it.
Typical checks: `CHK_CDC_GRAY`, `CHK_FIFO_OVFL`, event-count
conservation across the crossing (scoreboard-level).

## 4. Interrupts / events
- Assertion condition per source; level vs pulse semantics.
- Clear mechanisms (W1C, read-to-clear) including race: clear
  concurrent with new event — no lost, no phantom interrupt.
- Mask/enable: masked events pend or drop per spec; unmask with pending.
- Aggregation/coalescing behavior.

## 5. Registers (RAL)
- Reset values (all registers, post-both-reset-types).
- Access policy per field (RO/RW/W1C/RC/...); reserved fields
  write-ignored/read-zero per map.
- Side-effect registers modeled and excluded from naive bit-bash.
- Protected access (PPROT/secure) allowed × denied × error response.
- Frontdoor/backdoor consistency where backdoor is used.

## 6. Error handling and illegal stimulus
- Every spec'd error response: generation condition, propagation,
  logging/status capture, and RECOVERY (traffic sane after error).
- Illegal/unsupported opcodes, addresses, lengths: defined behavior,
  no lockup.
- Timeouts: trigger, report, recovery.

## 7. Capacity and boundaries
- FIFO full/empty/almost-* flags; behavior AT and ACROSS thresholds;
  overflow/underflow protection.
- Counter wrap (including long-run wrap of wide counters — directed).
- Max outstanding/in-flight; zero-length/min/max sizes of everything.

## 8. Backpressure, flow control, performance
- Sustained stall on each output interface; source starvation on each
  input; no data loss/duplication under either.
- Arbitration: policy conformance, fairness/starvation, priority
  inversion; QoS if present.
- Throughput/latency targets IF spec'd (else N/A with ref).
- Head-of-line blocking where architecture claims independence.

## 9. Low power (if applicable)
- Functional transparency across clock-gate entry/exit.
- Power domains: isolation/retention behavior, wake events (UPF-aware
  sim if the flow includes it — else N/A citing flow scope).

## 10. Concurrency and stress
- All interfaces active simultaneously; randomized cross-feature mixes.
- Soak/long-run stability item (also flushes TB leaks).

## 11. Configuration space
- Parameter/generic combinations (widths, depths, feature enables):
  which configurations are verified, which excluded — the exclusion
  list is itself a vplan decision.
- Mode/strap pins sampled correctly and only when spec'd.

## 12. Security / protection (if applicable)
- Access filtering, secure/non-secure separation, side-channel of
  status registers (information leakage through readable state).

## 13. Debug / DFT hooks (if in scope)
- Observability features, bypass modes — frequently out of DV scope by
  program decision: record the N/A with the decision reference.
