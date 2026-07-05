---
name: amba-axi
description: AXI4/AXI3 protocol rules for verification — handshake/ordering/burst/exclusive traps, check candidates, coverage dimensions, chkq injections. Use when writing stimulus, checkers, coverage, or triaging failures on AXI interfaces.
---

# AXI Verification Knowledge (AXI4 baseline; AXI3 deltas noted)

[TEAM: merge the team AMBA guide here; align check IDs with the per-IP
inventory. Spec: ARM IHI 0022 — cite exact §ID from the project's spec
revision in vplans, not from this file.]

## Handshake rules (per channel: AW, W, B, AR, R)
- VALID must not wait for READY (deadlock trap: DUT or TB gating VALID
  on READY). READY may wait for VALID, may assert speculatively, may
  toggle freely before VALID.
- Once VALID asserts, VALID AND the payload MUST hold stable until the
  handshake cycle. Stimulus must randomize READY back-pressure patterns
  (always-ready / delayed / toggling) — many DUT bugs only show under
  toggling READY.
- Reset: ARESETn asynchronous assert, synchronous deassert; interfaces
  drive VALID low during reset and may first assert it only after the
  first rising ACLK after deassert.

## Bursts and addressing
- AXI4 INCR: 1–256 beats; FIXED: 1–16; WRAP: 2/4/8/16 beats with aligned
  start address. (AXI3: all types max 16.)
- No burst may cross a 4KB address boundary (classic generator and DUT
  bug; must be BOTH a constraint and a check).
- WLAST exactly on the final write beat, RLAST on the final read beat —
  count beats independently in the checker; never trust LAST alone.
- Narrow/unaligned transfers via WSTRB: model must compute expected
  strobes; all-zero-strobe beats are legal.
- AXI4 removed write-data interleaving (single outstanding write data
  stream order = AW order). AXI3 permitted it via WID — a reuse trap when
  moving VIP/checkers between protocol versions.

## Ordering and IDs
- Same ID, same direction: responses/data return in issue order. Read
  data beats of a given ARID must not interleave with... (they MAY
  interleave across different ARIDs, never within one). Different IDs:
  any order — scoreboards must be ID-indexed, not FIFO-global.
- Write: all write data (and AXI4: the address) accepted before B
  response. B before last W accepted = DUT violation worth a check.
- Read-after-write / write-after-write hazards to overlapping addresses
  with different IDs are NOT ordered by the protocol — the reference
  model must not assume memory ordering the spec doesn't give.

## Responses and exclusive access
- RRESP/BRESP: OKAY, EXOKAY, SLVERR, DECERR. Error responses do NOT
  terminate a burst early — remaining beats still transfer (checker must
  keep counting; stimulus should hit mid-burst SLVERR).
- Exclusive: exclusive read then exclusive write, same ID, matching
  address/size; size power-of-2, max 128 bytes, address aligned to total
  size. EXOKAY only on exclusive success; OKAY on an exclusive write =
  store failed (memory NOT updated — model trap). Non-exclusive access
  to the monitored address between the pair must clear the monitor.

## Check candidates (stable ID suggestions)
`CHK_AXI_STABLE` payload/VALID stability until handshake ·
`CHK_AXI_4KB` boundary · `CHK_AXI_WLAST`/`CHK_AXI_RLAST` beat count ·
`CHK_AXI_ORDER_ID` same-ID ordering · `CHK_AXI_B_AFTER_W` ·
`CHK_AXI_EXCL_RESP` EXOKAY/OKAY correctness · `SCBD_AXI_DATA` data vs
model (WSTRB-aware) · `CHK_AXI_RST_VALID` valid-low in reset.

## Coverage dimensions (cross candidates)
burst type × len bucket × size; unaligned × WSTRB patterns; outstanding
depth per direction (incl. max); ID concurrency (same-ID back-to-back,
N distinct IDs in flight); response type × mid/last beat; exclusive
pass/fail/cleared; READY back-pressure pattern × channel; 4KB-boundary
proximity (last-beat-at-boundary bin).

## chkq injection ideas
Force RLAST low on the true final beat (→ CHK_AXI_RLAST); corrupt one
RDATA beat inside the DUT read path (→ SCBD_AXI_DATA); force BRESP=OKAY
where the model expects SLVERR; swap RID on one beat (→ ordering check);
force EXOKAY on a non-exclusive read (→ CHK_AXI_EXCL_RESP).
