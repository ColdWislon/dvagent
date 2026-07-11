---
name: verif-cockpit
description: Generate the local DV cockpit — a static HTML page giving one IP's pending human decisions, review scorecard, PLACEHOLDER-CHECK inventory, vplan traceability, regression clusters and agent-session timeline. Use when the user asks for a status view, "where are we", what is blocked, or the cockpit. HUMAN tool — agents never generate it in a session.
---

# Verification cockpit (local, static)

One command, one self-contained HTML page per IP:

    python3 .github/skills/verif-cockpit/scripts/cockpit.py <ip> --config template/cockpit.ini
    dv cockpit <ip>                # wrapper subcommand, where wired
    # backend (works today, no wrapper change needed):
    python3 .github/skills/verif-cockpit/scripts/cockpit.py <ip> --config template/cockpit.ini
    python3 .github/skills/verif-cockpit/scripts/cockpit.py --all   # + index.html

Open `cockpit.html` in a browser (file:// works, farm/SSH friendly). Zero
dependencies (stdlib), zero JS libs, dark instrument-panel styling.

## What it shows (top to bottom)
1. **Pending human decisions** (hero, open by default): Gate-1 plans awaiting
   approval, checker sign-offs, class-C exclusion proposals, sessions' open
   questions, unresolved `PLACEHOLDER-CHECK` stubs. This is the daily read.
2. **Verdict row**: milestone badge (M0-M3 from review.json), the 9 review
   axes as LEDs, lint E/W, placeholder / cluster / flaky / vplan-orphan counts.
3. Collapsible panels: placeholder inventory, vplan traceability (plan ids vs
   `VP-xxx` refs in code: orphans / unknown), regression clusters, lint
   findings, agent-session timeline (with pinned RTL revision).

Every panel carries its source timestamp; older than `stale_hours` is marked
STALE; absent data renders as "no data" — never an error.

## Data contract (hybrid)
Primary: `<ip>/dv/status/` — tools drop their latest verdicts there:
`review.json` (verif-env-review), `lint.json` (deprecation-lint lint.py),
`triage.json` (regression-triage), `session_*.json` (session sidecars — see
copilot-instructions evidence contract; schema: `{agent, gate, status:
awaiting_approval|awaiting_signoff|blocked|done, open_questions[], handoffs[],
rtl_rev}`).
Direct scans: `// PLACEHOLDER-CHECK` and `VP-xxx` tags in TB sources
(`template/cockpit.ini`'s `scan_dirs` — uvm-gen envs scan dv,agents,env,seq_lib,tests,tb),
`docs/vplan.md` (tolerant), `dv/cov/exclusion_requests.md`.

## Configuration — the tool abstraction
`template/cockpit.ini` (pass `--config template/cockpit.ini`; the script's
own built-in default only looks at `<root>/cockpit.ini`), section `[tool]`: everything
Xcelium/flow-specific (status dir, verdict filenames, vplan/exclusions paths,
scan dirs/extensions, tags, `--all` discovery glob) is config, not code.
Built-in defaults are the xcelium/dv profile — no file needed to start.
Optional `~/.dvcockpit.ini` overlay may override `[display]` only (title,
stale_hours); `[tool]` is team policy and stays versioned.

## How to use it

**Daily (engineer).** Run the cockpit each morning (or after a batch of
sim runs) and read the **Pending human** hero first — it is the list of
things that block the flow until *you* act: approve a Gate-1 plan, sign off a
checker, rule on an exclusion, answer a session's open question, or resolve a
`PLACEHOLDER-CHECK`. If that panel is empty, the flow is unblocked; skim the
verdict row and move on.

**Reading the verdict row.** Green/amber/red LEDs are the 9 review axes; the
milestone badge is the highest M-level whose required axes pass. A red axis
with `dod_pass:false` is what stops the next milestone — open the matching
panel for the file:line and fix.

**Chasing a red regression.** Open **Regression clusters**: one row per root
cause, biggest first. Debug the representative repro (`test` + `seed`) of the
top cluster, not the 200 failures — one fix usually clears the cluster.

**Before an MR.** Check that **placeholders = 0** and **lint errors = 0** for
your IP; both are merge blockers the reviewer will catch anyway.

**Lead / multi-IP.** `dv cockpit --all` writes one page per IP plus
`index.html` — scan the index for IPs with high pending counts or a slipped
milestone.

**Freshness.** Each panel shows its source timestamp; `STALE` (older than
`stale_hours`) means the underlying `dv/status/*.json` hasn't been refreshed —
re-run the relevant `dv` step, then regenerate. "no data" means that source was
never produced for this IP (e.g. no `triage.json` yet).

**If a panel is empty when you expect content.** The cockpit only renders what
the flow deposits: verdicts must land in `<ip>/dv/status/` (review/lint/triage
JSON) and sessions must write their `session_*.json` sidecar. Tags
(`VP-xxx`, `PLACEHOLDER-CHECK`) are scanned live from sources, so those always
reflect the checkout.

**Retarget or relocate.** Edit `template/cockpit.ini` `[tool]` (paths, filenames, tags,
discovery glob) — no code change. `python3 cockpit.py --help` lists flags.

## Boundaries
- Read-only over the checkout; writes only the html output.
- Human-invoked. Agents do not run it: it renders state, it is not evidence,
  and it must never substitute for verbatim `dv` verdicts in a session report.
- Wrapper wiring (`dv cockpit`) follows the ask-don't-guess protocol — see the
  dv-wrapper skill entry.
