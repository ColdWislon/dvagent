#!/usr/bin/env python3
"""
triage_log.py -- deterministic (LLM-free) Xcelium/UVM log triage.

Part of the `log-triage` skill. Parses one or more simulation logs, extracts the
first causal error, classifies it, and emits a normalized failure signature for
clustering by `regression-triage`. Python stdlib only.

Output: JSON on stdout -- one report object for a single file, or
{"logs":[...], "signature_histogram": {...}} for several. Human one-liners on
stderr. Exit 0 (triage always succeeds; the verdict is in the JSON).

Usage:
  python3 triage_log.py run.log
  python3 triage_log.py regr/*/run.log            # multi-log + histogram
"""
import argparse
import json
import os
import re
import sys

# --- patterns ---------------------------------------------------------------
RE_UVM = re.compile(
    r'^(UVM_(?:FATAL|ERROR|WARNING))\s+(?:\S+\s+)?@\s*([\d.]+)\s*(?:ns|ps|us)?'
    r'\s*:?\s*(?:\S+\s+)?(?:\[([^\]]+)\])?\s*(.*)$')
RE_UVM_ALT = re.compile(r'^(UVM_(?:FATAL|ERROR|WARNING))\s*(?:@ ([\d.]+))?.*?\[([^\]]+)\]\s*(.*)$')
RE_XRUN_E = re.compile(r'^(?:xmelab|xmvlog|xmsim|xrun|ncelab|ncvlog|ncsim)\s*:\s*\*([EF])\W*,?\s*(\w+)?\s*(.*)$')
RE_STAR_E = re.compile(r'^\s*\*([EF]),(\w+)\s*(?:\(([^)]+)\))?\s*:?\s*(.*)$')
RE_SVA    = re.compile(r'Assertion\s+(\S+)\s+.*?(?:failed|FAILED)|^\s*\*E,ASRTST.*', re.I)
RE_TIMEOUT= re.compile(r'(watchdog|timeout reached|TIMEOUT|phase timeout|Simulation.*time.*limit)', re.I)
RE_LICENSE= re.compile(r'(license|Licence).*?(unavailable|denied|checkout fail|queued)', re.I)
RE_DISK   = re.compile(r'(No space left on device|disk quota exceeded)', re.I)
RE_BANNER_PASS = re.compile(r'(TEST\s+PASS\w*|\*\*\s*PASSED|\[RESULT\].*PASS)', re.I)
RE_REPORT_ERR  = re.compile(r'UVM_ERROR\s*:\s*(\d+)')
RE_REPORT_FTL  = re.compile(r'UVM_FATAL\s*:\s*(\d+)')

# signature normalisation: mask volatile values so identical bugs cluster
MASKS = [
    (re.compile(r'0x[0-9a-fA-F]+'), '<X>'),
    (re.compile(r"\b\d+'[hbd][0-9a-fA-FxXzZ_]+"), '<X>'),
    (re.compile(r'\b\d{2,}\b'), '<X>'),
    (re.compile(r'@\s*<X>'), ''),
    (re.compile(r'\s+'), ' '),
]

# TB-ish UVM message IDs / texts -> layer hints
TB_HINTS  = re.compile(r'(null virtual interface|no agent cfg|no env cfg|config_?db|'
                       r'randomi[sz]ation failed|randomize failed|cannot find|factory)', re.I)
SB_HINTS  = re.compile(r'(scoreboard|mismatch|unexpected|unmatched|_sb\b)', re.I)


def norm_signature(sev, uid, msg):
    s = "%s:%s:%s" % (sev, uid or "-", (msg or "").strip())
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s.strip()[:200]


def triage(path):
    first = None            # first causal error dict
    counts = {"uvm_error": 0, "uvm_fatal": 0, "uvm_warning": 0, "compile_e": 0, "sva_fail": 0}
    infra = None
    banner_pass = False
    reported = {}
    last_info_line = 0

    try:
        fh = open(path, 'r', errors='replace')
    except OSError as e:
        return {"file": path, "verdict": "infra", "layer": "io",
                "error": str(e), "signature": "infra:io:unreadable log"}

    with fh:
        for n, line in enumerate(fh, 1):
            line = line.rstrip('\n')
            if 'UVM_INFO' in line:
                last_info_line = n

            m = RE_STAR_E.match(line) or RE_XRUN_E.match(line)
            if m:
                counts["compile_e"] += 1
                if first is None:
                    first = {"line": n, "time_ns": None, "severity": "*E",
                             "id": m.group(2) or "compile", "message": m.group(3) if m.lastindex >= 3 else line}

            if RE_SVA.search(line):
                counts["sva_fail"] += 1
                if first is None:
                    first = {"line": n, "time_ns": None, "severity": "SVA",
                             "id": "assertion", "message": line.strip()}

            if line.startswith('UVM_'):
                m = RE_UVM.match(line) or RE_UVM_ALT.match(line)
                if m:
                    sev = m.group(1)
                    if sev == 'UVM_ERROR':   counts["uvm_error"] += 1
                    elif sev == 'UVM_FATAL': counts["uvm_fatal"] += 1
                    else:                    counts["uvm_warning"] += 1
                    if sev in ('UVM_ERROR', 'UVM_FATAL') and first is None:
                        groups = m.groups()
                        t   = groups[2] if len(groups) >= 5 else groups[1]
                        uid = groups[3] if len(groups) >= 5 else groups[2]
                        msg = groups[4] if len(groups) >= 5 else groups[3]
                        first = {"line": n, "time_ns": float(t) if t else None,
                                 "severity": sev, "id": uid, "message": (msg or "").strip()}

            if infra is None:
                if RE_LICENSE.search(line): infra = ("license", n, line.strip())
                elif RE_DISK.search(line):  infra = ("disk", n, line.strip())
                elif RE_TIMEOUT.search(line):
                    infra = ("timeout", n, line.strip())

            if RE_BANNER_PASS.search(line):
                banner_pass = True
            m = RE_REPORT_ERR.search(line)
            if m: reported["uvm_error"] = int(m.group(1))
            m = RE_REPORT_FTL.search(line)
            if m: reported["uvm_fatal"] = int(m.group(1))

    # ---- verdict -------------------------------------------------------------
    flags = []
    if infra and infra[0] in ("license", "disk"):
        verdict, layer = "infra", infra[0]
        sig = "infra:%s" % infra[0]
        first = first or {"line": infra[1], "time_ns": None, "severity": "INFRA",
                          "id": infra[0], "message": infra[2]}
        next_action = "clear the %s issue and rerun; not a design/TB failure" % infra[0]
    elif first is None and infra and infra[0] == "timeout":
        verdict, layer = "needs_waveform", "hang"
        sig = "hang:timeout:no-error"
        first = {"line": infra[1], "time_ns": None, "severity": "TIMEOUT",
                 "id": "watchdog", "message": infra[2]}
        next_action = ("hang with zero errors: inspect the last UVM_INFO heartbeat "
                       "(line %d) and the stalled handshake; check objection holders "
                       "with +UVM_OBJECTION_TRACE" % last_info_line)
    elif first is None:
        verdict, layer, sig = "pass", "-", "pass"
        next_action = "no error found in this log"
    else:
        blob = "%s %s" % (first.get("id") or "", first.get("message") or "")
        if first["severity"] == "*E":
            verdict, layer = "tb_bug", "compile_elab"
            next_action = "fix the compile/elab error first; everything after is fallout"
        elif first["severity"] == "SVA":
            verdict, layer = "dut_suspect", "assertion"
            next_action = "read the property; sample its signals at the failing attempt in waves"
        elif TB_HINTS.search(blob):
            verdict, layer = "tb_bug", "config" if "interface" in blob.lower() or "cfg" in blob.lower() else "testbench"
            next_action = "testbench-side failure: fix env/config/stimulus code"
        elif SB_HINTS.search(blob):
            verdict, layer = "dut_suspect", "scoreboard"
            t = first.get("time_ns")
            next_action = ("scoreboard mismatch: open waveform at %sns; follow the "
                           "mismatch playbook (pins -> monitor -> reference -> DUT)"
                           % (("%g" % t) if t else "the failure time"))
        else:
            verdict, layer = "needs_waveform", "unclassified"
            next_action = "unclassified first error: inspect the log context around line %d" % first["line"]
        sig = norm_signature(first["severity"], first.get("id"), first.get("message"))

    if banner_pass and counts["uvm_error"] > 0:
        flags.append("banner says PASS but UVM_ERROR>0: pass/fail logic broken "
                     "(check report catcher / severity demotion)")
    if reported.get("uvm_error") is not None and reported["uvm_error"] != counts["uvm_error"]:
        flags.append("report summary count (%d) != counted UVM_ERROR lines (%d)"
                     % (reported["uvm_error"], counts["uvm_error"]))

    return {"file": path, "verdict": verdict, "layer": layer, "first_error": first,
            "signature": sig, "counts": counts, "flags": flags, "next_action": next_action}


def main():
    ap = argparse.ArgumentParser(description="Xcelium/UVM log triage (log-triage skill)")
    ap.add_argument("logs", nargs="+", help="log file(s)")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    reports = [triage(p) for p in args.logs]

    if len(reports) == 1:
        print(json.dumps(reports[0], indent=2))
    else:
        hist = {}
        for r in reports:
            hist[r["signature"]] = hist.get(r["signature"], 0) + 1
        hist = dict(sorted(hist.items(), key=lambda kv: -kv[1]))
        print(json.dumps({"logs": reports, "signature_histogram": hist}, indent=2))

    if not args.json_only:
        for r in reports:
            fe = r.get("first_error") or {}
            print("[log-triage] %-40s %-14s %-12s %s" %
                  (os.path.basename(r["file"]), r["verdict"], r["layer"],
                   (fe.get("message") or "")[:70]), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
