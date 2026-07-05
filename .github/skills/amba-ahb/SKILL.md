---
name: amba-ahb
description: AHB-Lite/AHB5 protocol rules for verification — pipeline/HTRANS/burst/wait-state traps, check candidates, coverage dimensions, chkq injections. Use when writing stimulus, checkers, coverage, or triaging failures on AHB interfaces.
---

# AHB Verification Knowledge (AHB-Lite baseline)

[TEAM: merge the team AMBA guide here; align check IDs with the per-IP
inventory. Spec: ARM IHI 0033 — cite the project's spec revision in
vplans.]

## Pipeline model (the source of most AHB confusion)
- Two overlapped phases: address phase of transfer N+1 runs during data
  phase of transfer N. Monitors and checkers MUST be phase-aware: sample
  address/control when HREADY is high, associate them with the FOLLOWING
  data phase.
- HREADY low extends the CURRENT data phase AND stretches the address
  phase of the next transfer — address/control must stay stable through
  wait states (check candidate; also a classic TB driver bug).

## HTRANS semantics
- IDLE: no transfer; slave must zero-wait OKAY it.
- NONSEQ: single transfer or first beat of a burst.
- SEQ: burst continuation, address per burst progression.
- BUSY: master-inserted gap INSIDE a burst only; address/control of the
  next beat held; slave must zero-wait OKAY. BUSY as first transfer, or
  after the final beat, is a violation (check). AHB5: BUSY handling for
  undefined-length INCR at burst end — check spec revision.

## Bursts
- SINGLE, INCR (undefined length), INCR4/8/16, WRAP4/8/16.
- 1KB boundary rule: no burst crosses a 1KB address boundary (constraint
  AND check).
- Fixed-length bursts terminate exactly on their beat count; the master
  may early-terminate an INCR (and must after losing bus in multi-master
  AHB) by starting a new NONSEQ — checkers must accept legal early
  termination without flagging it.
- WRAP address progression wraps at (beats × size) aligned container —
  reference-model math worth a dedicated unit-style negative test.

## Responses
- OKAY and ERROR only (AHB-Lite). ERROR is a TWO-CYCLE response: HREADY
  low + HRESP=ERROR, then HREADY high + HRESP=ERROR. One-cycle ERROR is
  a violation (check).
- On ERROR the master MAY continue or cancel the remaining burst — the
  scoreboard must handle both without assuming either.
- Slave must never assert ERROR for IDLE/BUSY.

## Data and strobes
- Write data valid during the data phase, held through wait states.
- Byte lanes per HSIZE/address alignment (AHB is aligned-only; unaligned
  = illegal stimulus except when deliberately testing decoder behavior).
  AHB5 adds HWSTRB — sparse strobes only if the project enables it.

## Check candidates (stable ID suggestions)
`CHK_AHB_ADDR_STABLE` addr/ctrl stable through wait states ·
`CHK_AHB_TRANS_SEQ` legal HTRANS sequencing (BUSY placement, SEQ addr
progression) · `CHK_AHB_1KB` boundary · `CHK_AHB_ERR_2CYC` two-cycle
error · `CHK_AHB_BUSY_OKAY` zero-wait OKAY on IDLE/BUSY ·
`SCBD_AHB_DATA` data vs model.

## Coverage dimensions
burst type × wait-state count (0/1/N) per beat position; ERROR on
first/mid/last beat × master continue/cancel; BUSY insertion position ×
burst type; early termination of INCR at each beat bucket; back-to-back
NONSEQ with zero idle; 1KB-boundary proximity; HSIZE × address
alignment.

## chkq injection ideas
Force HRESP=ERROR for a single cycle (→ CHK_AHB_ERR_2CYC); corrupt
HRDATA during a wait-extended data phase (→ SCBD_AHB_DATA); force an
address change mid-wait-state (→ CHK_AHB_ADDR_STABLE); force HREADY high
during the first ERROR cycle.
