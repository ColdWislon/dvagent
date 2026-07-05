#!/usr/bin/env python3
"""
lint.py -- deterministic (LLM-free) check-independence linter for UVM testbenches.

Part of the `deprecation-lint` skill. Implements the check-independence subset of
the house ruleset as a regex scanner (Python stdlib only), so a CI gate can
enforce it without a model in the loop.

Catches:
  indep.sb_include_seq   (error)  scoreboard file `include`s a sequence/stimulus file
  indep.sb_seq_handle    (error)  scoreboard file declares/uses a *_seq / *_vseq type
  indep.sb_config_golden (warn)   scoreboard file reads config_db (possible golden)
  indep.driver_to_sb     (error)  env file connects a *driver* analysis port to the scoreboard

Scope : .sv / .svh files under the given path(s), recursively.
Output: JSON on stdout ({summary, findings}); human summary on stderr.
Exit  : 1 if any error (or any warning with --fail-on-warning), else 0.

This is a lint, not a parser. It strips // and /* */ comments before matching and
is deliberately narrow and precise. Extend the scan_file() rules to grow coverage.
Point it at the testbench source, not at this skill's own scripts/tests/ fixtures.
"""
import argparse
import json
import os
import re
import sys

# --- patterns ---------------------------------------------------------------
RE_INCLUDE   = re.compile(r'`include\s+"([^"]+)"')
RE_SEQ_FILE  = re.compile(r'(_vseq|_seq)(_lib)?\.svh?$|_sequence\.svh?$', re.I)
RE_SEQ_DECL  = re.compile(r'^\s*([A-Za-z_]\w*_v?seq)\s+\w+\s*[;=,()]')
RE_SEQ_STAT  = re.compile(r'\b([A-Za-z_]\w*_v?seq)\s*::')
RE_SEQ_PARAM = re.compile(r'\b([A-Za-z_]\w*_v?seq)\s*#\s*\(')
RE_CFG_GET   = re.compile(r'uvm_config_db\s*#\s*\(.*?\)\s*::\s*get\b')
RE_DRV_SB    = re.compile(
    r'([A-Za-z_]\w*(?:driver|drv)\w*)\.\w+\.connect\s*\(\s*'
    r'([A-Za-z_]*(?:scoreboard|_sb)\w*)', re.I)


def strip_comments(text):
    """Remove /* */ (line-count preserving) then // comments, keeping line numbers."""
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'),
                  text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    return text


def classify(path, text):
    base = os.path.basename(path).lower()
    is_sb = ('scoreboard' in base
             or re.search(r'_sb\b', base) is not None
             or re.search(r'class\s+\w+\s+extends\s+uvm_scoreboard\b', text) is not None)
    is_env = (re.search(r'_env\b', base) is not None
              or re.search(r'class\s+\w+\s+extends\s+uvm_env\b', text) is not None)
    return is_sb, is_env


def _finding(rule_id, sev, file, line, msg, fix):
    return {"pass": "independence", "rule_id": rule_id, "severity": sev,
            "file": file, "line": line, "message": msg, "fix": fix}


def scan_file(path, rel):
    findings = []
    try:
        with open(path, 'r', errors='replace') as fh:
            raw = fh.read()
    except OSError:
        return findings
    text = strip_comments(raw)
    is_sb, is_env = classify(path, text)
    for i, line in enumerate(text.splitlines(), 1):
        if is_sb:
            m = RE_INCLUDE.search(line)
            if m and RE_SEQ_FILE.search(m.group(1)):
                findings.append(_finding(
                    "indep.sb_include_seq", "error", rel, i,
                    "scoreboard includes stimulus file '%s'" % m.group(1),
                    "feed the scoreboard from monitors + an independent reference only"))
            for rx in (RE_SEQ_DECL, RE_SEQ_STAT, RE_SEQ_PARAM):
                m = rx.search(line)
                if m:
                    findings.append(_finding(
                        "indep.sb_seq_handle", "error", rel, i,
                        "scoreboard references sequence/stimulus type '%s'" % m.group(1),
                        "derive expected from observed input + reference, not the stimulus class"))
                    break
            if RE_CFG_GET.search(line):
                findings.append(_finding(
                    "indep.sb_config_golden", "warn", rel, i,
                    "scoreboard reads config_db (possible stimulus-derived golden)",
                    "confirm expected comes from observed input + spec, not stimulus knobs"))
        if is_env:
            m = RE_DRV_SB.search(line)
            if m:
                findings.append(_finding(
                    "indep.driver_to_sb", "error", rel, i,
                    "driver '%s' analysis port connected to scoreboard '%s'" % (m.group(1), m.group(2)),
                    "connect the scoreboard to input monitors, not the driver"))
    return findings


def gather(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in names:
                    if n.endswith(('.sv', '.svh')):
                        files.append(os.path.join(root, n))
    return sorted(set(files))


def main():
    ap = argparse.ArgumentParser(
        description="check-independence linter (deprecation-lint skill)")
    ap.add_argument("paths", nargs="+", help="TB source file(s) or directory(ies)")
    ap.add_argument("--fail-on-warning", action="store_true",
                    help="treat warnings as gate failures too")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress the human summary on stderr")
    args = ap.parse_args()

    files = gather(args.paths)
    findings = []
    for path in files:
        findings.extend(scan_file(path, os.path.relpath(path)))

    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warn")
    gate_fail = errors > 0 or (args.fail_on_warning and warnings > 0)

    report = {
        "summary": {"errors": errors, "warnings": warnings, "dod_pass": not gate_fail},
        "findings": findings,
    }
    print(json.dumps(report, indent=2))

    if not args.json_only:
        verdict = "FAIL" if gate_fail else "PASS"
        print("[deprecation-lint] scanned %d file(s): %d error(s), %d warning(s) -> %s"
              % (len(files), errors, warnings, verdict), file=sys.stderr)
        for f in findings:
            print("  %-5s %s:%d [%s] %s"
                  % (f["severity"].upper(), f["file"], f["line"], f["rule_id"], f["message"]),
                  file=sys.stderr)

    sys.exit(1 if gate_fail else 0)


if __name__ == "__main__":
    main()
