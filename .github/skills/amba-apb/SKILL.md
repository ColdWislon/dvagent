---
name: amba-apb
description: APB3/APB4 protocol rules for verification — setup/access phase, PREADY/PSLVERR, PSTRB traps, check candidates, coverage dimensions, chkq injections. Use when writing stimulus, checkers, coverage, or triaging failures on APB interfaces.
---

# APB Verification Knowledge (APB4 baseline; APB3 = no PSTRB/PPROT)

[TEAM: merge the team AMBA guide here; align check IDs with the per-IP
inventory. Spec: ARM IHI 0024 — cite the project's spec revision in
vplans.]

## Transfer protocol
- Strictly two phases, no pipelining: SETUP (PSEL=1, PENABLE=0, exactly
  one cycle) then ACCESS (PSEL=1, PENABLE=1, extended by PREADY low).
- PENABLE high in the same cycle PSEL rises, PENABLE held past PREADY,
  or a SETUP phase longer than one cycle are all violations (check).
- PADDR, PWRITE, PWDATA, PSTRB, PPROT must be stable from SETUP through
  the end of ACCESS (check candidate; also the classic APB driver bug).
- Back-to-back transfers each get their own SETUP phase; PSEL may stay
  high between transfers but PENABLE must drop for the new SETUP cycle.
- Only one PSELx active at a time (decoder check at interconnect level).

## Wait states and errors
- PREADY sampled only during ACCESS; slave may hold it low indefinitely
  (stimulus: randomize 0..N wait states; include a long-stall bin).
- PSLVERR valid only in the last ACCESS cycle (PREADY high). PSLVERR
  outside that window is a violation (check).
- On an error write, whether state updated is slave-specific — the
  reference model must encode the block's documented behavior, not an
  assumption; read-after-error-write is a mandatory stimulus pattern.

## APB4 specifics
- PSTRB: write byte strobes. Reads MUST drive PSTRB all-zeros; writes
  may use any pattern. The model must apply strobes lane-wise —
  sparse-strobe writes are the classic register-model divergence.
- PPROT: privilege/security/data-instr attributes — if the block gates
  access by PPROT, that gating is a first-class vplan section (allowed ×
  denied × PSLVERR behavior).

## Register-block interaction (usual APB context)
- Volatile/side-effect registers (read-to-clear, write-1-to-clear) must
  be modeled explicitly and excluded from naive RAL bit-bash checks.
- Reserved fields: writes ignored / reads as zero per the block's map —
  mismatches here are usually vplan/model bugs, not DUT bugs; check the
  register map revision first when triaging.

## Check candidates (stable ID suggestions)
`CHK_APB_PHASE` setup/access sequencing (PENABLE discipline) ·
`CHK_APB_STABLE` addr/ctrl/data stable through transfer ·
`CHK_APB_SLVERR_WIN` PSLVERR only with PREADY in ACCESS ·
`CHK_APB_STRB_RD` PSTRB zero on reads · `SCBD_APB_REG` read data vs
register model (strobe- and side-effect-aware).

## Coverage dimensions
read/write × wait-state bucket (0/1/2+/long) × PSLVERR; PSTRB patterns
(full/sparse/single-lane) × register class; PPROT combinations × grant/
deny (if gated); back-to-back with PSEL held vs dropped; error write →
readback value.

## chkq injection ideas
Force PSLVERR high during SETUP (→ CHK_APB_SLVERR_WIN); corrupt PRDATA
in the DUT during a wait-extended ACCESS (→ SCBD_APB_REG); force PENABLE
low for one ACCESS cycle mid-transfer (→ CHK_APB_PHASE); flip one PWDATA
lane after SETUP (→ CHK_APB_STABLE).
