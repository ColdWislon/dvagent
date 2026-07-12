#!/usr/bin/env python3
"""
dashboard.py -- local verification dashboard (verif-dashboard skill).

Generates a self-contained static HTML page ("dashboard") for one IP -- or, with
--all, one page per IP plus an index -- from artifacts already present in the
engineer's checkout. Python stdlib only. No server, no JS dependencies
(collapsible panels use <details>/<summary>).

Data sources (hybrid contract):
  - <ip>/<status_dir>/review.json     verif-env-review scorecard (axes, milestone)
  - <ip>/<status_dir>/lint.json       deprecation-lint lint.py verdict
  - <ip>/<status_dir>/triage.json     regression-triage clusters
  - <ip>/<status_dir>/session_*.json  agent session sidecars (pending-human data)
  - <ip>/dv/cov/exclusion_requests.md exclusion proposals (class C)
  - direct scans: `// PLACEHOLDER-CHECK` and `VP-xxx` tags in dv sources,
    `<ip>/docs/vplan.md` item ids (tolerant parse)

Tool abstraction: every Xcelium-specific location/pattern lives in the [tool]
section of dashboard.ini (repo root). Absent file = built-in xcelium defaults.
Missing data is a rendered state ("no data"), never an error.

Usage:
  python3 dashboard.py <ip_path> [--out dashboard.html] [--root REPO] [--config INI]
  python3 dashboard.py --all [--root REPO]        # per-IP pages + index.html

Intended invocation for engineers: `dv dashboard <ip>` (wrapper wiring -- see the
dv-wrapper skill). This is a HUMAN tool: agents have no reason to run it.
"""
import argparse
import configparser
import glob
import html
import json
import os
import re
import sys
import time

# --------------------------------------------------------------------------- #
# configuration (tool abstraction)                                            #
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "tool": {
        # Xcelium/dv-flow profile -- override in dashboard.ini for another stack
        "name":            "xcelium",
        "status_dir":      "dv/status",            # verdict drop dir (contract)
        "review_json":     "review.json",
        "lint_json":       "lint.json",
        "triage_json":     "triage.json",
        "session_glob":    "session_*.json",
        "exclusions_md":   "dv/cov/exclusion_requests.md",
        "vplan_md":        "docs/vplan.md",
        "scan_dirs":       "dv",                    # comma-separated, relative to ip
        "scan_exts":       ".sv,.svh",
        "placeholder_tag": "PLACEHOLDER-CHECK",
        "vplan_tag":       r"VP-[\w-]+",             # VP-<IP>-nnn (and legacy VP-nnn)
        "ip_glob":         "*/dv",                  # --all discovery: dirs whose parent is an IP
    },
    "display": {
        "title":        "DV Dashboard",
        "stale_hours":  "48",
    },
}


def load_cfg(root, path):
    cfg = configparser.ConfigParser()
    cfg.read_dict(DEFAULTS)
    ini = path or os.path.join(root, "dashboard.ini")
    if os.path.isfile(ini):
        cfg.read(ini)
    return cfg


# --------------------------------------------------------------------------- #
# collection                                                                  #
# --------------------------------------------------------------------------- #
def _load_json(path):
    try:
        with open(path) as fh:
            return json.load(fh), os.path.getmtime(path)
    except (OSError, ValueError):
        return None, None


def _scan_tags(ip, cfg):
    """Grep VP-xxx and PLACEHOLDER-CHECK tags in dv sources."""
    exts = tuple(e.strip() for e in cfg.get("tool", "scan_exts").split(","))
    vp_rx = re.compile(cfg.get("tool", "vplan_tag"))
    ph_tag = cfg.get("tool", "placeholder_tag")
    vp_hits, placeholders = set(), []
    for d in cfg.get("tool", "scan_dirs").split(","):
        base = os.path.join(ip, d.strip())
        for r, _dirs, files in os.walk(base):
            if os.sep + "status" in r:
                continue
            for f in files:
                if not f.endswith(exts):
                    continue
                p = os.path.join(r, f)
                try:
                    with open(p, errors="replace") as fh:
                        for n, line in enumerate(fh, 1):
                            for m in vp_rx.findall(line):
                                vp_hits.add(m)
                            if ph_tag in line:
                                placeholders.append(
                                    {"file": os.path.relpath(p, ip), "line": n,
                                     "text": line.strip()[:160]})
                except OSError:
                    pass
    return vp_hits, placeholders


def _parse_vplan(ip, cfg):
    """Tolerant: collect VP ids from vplan.md; None if file absent."""
    p = os.path.join(ip, cfg.get("tool", "vplan_md"))
    if not os.path.isfile(p):
        return None, None
    vp_rx = re.compile(cfg.get("tool", "vplan_tag"))
    ids = set()
    with open(p, errors="replace") as fh:
        for line in fh:
            ids.update(vp_rx.findall(line))
    return ids, os.path.getmtime(p)


def _parse_exclusions(ip, cfg):
    p = os.path.join(ip, cfg.get("tool", "exclusions_md"))
    if not os.path.isfile(p):
        return [], None
    items = []
    with open(p, errors="replace") as fh:
        for line in fh:
            ls = line.strip()
            if ls.startswith(("- ", "* ", "## ")) and len(ls) > 3:
                items.append(ls.lstrip("-*# ").strip()[:160])
    return items, os.path.getmtime(p)


def collect(ip, cfg):
    sdir = os.path.join(ip, cfg.get("tool", "status_dir"))
    d = {"ip": os.path.basename(os.path.abspath(ip)), "path": ip, "sources": {}}

    for key in ("review", "lint", "triage"):
        j, mt = _load_json(os.path.join(sdir, cfg.get("tool", key + "_json")))
        d[key] = j
        d["sources"][key] = mt

    sessions = []
    for p in sorted(glob.glob(os.path.join(sdir, cfg.get("tool", "session_glob")))):
        j, mt = _load_json(p)
        if j is not None:
            j["_file"] = os.path.basename(p)
            j["_mtime"] = mt
            sessions.append(j)
    sessions.sort(key=lambda s: s.get("_mtime") or 0, reverse=True)
    d["sessions"] = sessions

    d["vplan_ids"], d["sources"]["vplan"] = _parse_vplan(ip, cfg)
    d["vp_in_code"], d["placeholders"] = _scan_tags(ip, cfg)
    d["exclusions"], d["sources"]["exclusions"] = _parse_exclusions(ip, cfg)

    # ---- pending-human aggregation ----
    pend = []
    for s in sessions:
        st = (s.get("status") or "").lower()
        if st in ("awaiting_approval", "awaiting_signoff", "blocked"):
            pend.append({"kind": "session", "who": s.get("agent", "?"),
                         "what": "%s -- %s (gate %s)" % (
                             s.get("agent", "?"), st.replace("_", " "),
                             s.get("gate", "?")),
                         "ref": s["_file"]})
        for q in (s.get("open_questions") or []):
            pend.append({"kind": "question", "who": s.get("agent", "?"),
                         "what": str(q)[:160], "ref": s["_file"]})
    for e in d["exclusions"]:
        pend.append({"kind": "exclusion", "who": "coverage",
                     "what": "exclusion proposal: " + e, "ref": "exclusion_requests.md"})
    for p in d["placeholders"]:
        pend.append({"kind": "placeholder", "who": "env-architect",
                     "what": p["text"], "ref": "%s:%d" % (p["file"], p["line"])})
    d["pending"] = pend
    return d


# --------------------------------------------------------------------------- #
# rendering                                                                   #
# --------------------------------------------------------------------------- #
CSS = """
body{background:#0d1117;color:#c9d1d9;font-family:'SF Mono',Menlo,Consolas,monospace;
     margin:0;padding:24px;font-size:13px}
h1{font-size:18px;color:#e6edf3;margin:0 0 2px} .sub{color:#8b949e;margin-bottom:18px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;min-width:110px}
.card .k{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:.08em}
.card .v{font-size:20px;margin-top:2px}
.led{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:baseline}
.pass{background:#3fb950;box-shadow:0 0 6px #3fb95088}.warn{background:#d29922;box-shadow:0 0 6px #d2992288}
.fail{background:#f85149;box-shadow:0 0 6px #f8514988}.na{background:#484f58}
.badge{padding:2px 10px;border-radius:12px;font-weight:bold}
.badge.M0{background:#f8514933;color:#f85149}.badge.M1{background:#d2992233;color:#d29922}
.badge.M2{background:#58a6ff33;color:#58a6ff}.badge.M3{background:#3fb95033;color:#3fb950}
.badge.nd{background:#484f5833;color:#8b949e}
details{background:#161b22;border:1px solid #30363d;border-radius:8px;margin-bottom:10px}
summary{cursor:pointer;padding:10px 14px;color:#e6edf3;font-weight:bold;outline:none}
summary .cnt{color:#8b949e;font-weight:normal}
.panel{padding:0 14px 12px}
table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #21262d;padding:4px 8px;text-align:left;vertical-align:top}
th{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:.08em}
.hero{border-color:#d29922}
.mono{color:#8b949e}.stale{color:#d29922;font-size:10px;margin-left:6px}
a{color:#58a6ff;text-decoration:none}
.kind{font-size:10px;padding:1px 6px;border-radius:8px;background:#21262d;color:#8b949e;margin-right:6px}
"""


def _esc(x):
    return html.escape(str(x))


def _stale(mt, cfg):
    if mt is None:
        return ' <span class="stale">no data</span>'
    age_h = (time.time() - mt) / 3600.0
    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(mt))
    tag = ' <span class="stale">STALE</span>' if age_h > cfg.getfloat("display", "stale_hours") else ""
    return ' <span class="mono">(%s)</span>%s' % (ts, tag)


def _led(status):
    cls = {"pass": "pass", "warn": "warn", "fail": "fail"}.get(status, "na")
    return '<span class="led %s"></span>' % cls


def render_ip(d, cfg):
    rv = d["review"] or {}
    summ = rv.get("summary", {})
    ms = summ.get("milestone_ready")
    axes = rv.get("axes", [])
    lint = (d["lint"] or {}).get("summary", {})
    clusters = (d["triage"] or {}).get("clusters", [])
    flaky = sum(1 for c in clusters if c.get("quarantine") or c.get("verdict") == "flaky")

    vp_plan = d["vplan_ids"]
    vp_code = d["vp_in_code"]
    orphans = sorted(vp_plan - vp_code) if vp_plan is not None else []
    unknown = sorted(vp_code - vp_plan) if vp_plan is not None else []

    o = ["<!doctype html><html><head><meta charset='utf-8'><title>%s — %s</title>"
         "<style>%s</style></head><body>" % (_esc(cfg.get("display", "title")), _esc(d["ip"]), CSS)]
    o.append("<h1>%s — %s</h1><div class='sub'>tool profile: %s · generated %s · "
             "regenerate: <code>dv dashboard %s</code></div>"
             % (_esc(cfg.get("display", "title")), _esc(d["ip"]),
                _esc(cfg.get("tool", "name")),
                time.strftime("%Y-%m-%d %H:%M"), _esc(d["ip"])))

    # ---- HERO: pending human ----
    o.append("<details open class='hero'><summary>⏳ Pending human decisions "
             "<span class='cnt'>(%d)</span></summary><div class='panel'>" % len(d["pending"]))
    if d["pending"]:
        o.append("<table><tr><th></th><th>item</th><th>ref</th></tr>")
        for p in d["pending"]:
            o.append("<tr><td><span class='kind'>%s</span></td><td>%s</td>"
                     "<td class='mono'>%s</td></tr>"
                     % (_esc(p["kind"]), _esc(p["what"]), _esc(p["ref"])))
        o.append("</table>")
    else:
        o.append("<p class='mono'>nothing awaiting a human — flow unblocked.</p>")
    o.append("</div></details>")

    # ---- verdict row ----
    o.append("<div class='row'>")
    o.append("<div class='card'><div class='k'>milestone</div><div class='v'>"
             "<span class='badge %s'>%s</span>%s</div></div>"
             % (_esc(ms) if ms else "nd", _esc(ms) if ms else "n/a",
                _stale(d["sources"].get("review"), cfg)))
    ax_html = "".join("%s%s " % (_led(a.get("status")), _esc(a.get("axis", "?")[:14]))
                      for a in axes) or "<span class='mono'>no review.json</span>"
    o.append("<div class='card' style='flex:2'><div class='k'>review axes</div>"
             "<div style='margin-top:6px;line-height:1.9'>%s</div></div>" % ax_html)
    for label, val, src in (
            ("lint E/W", "%s/%s" % (lint.get("errors", "–"), lint.get("warnings", "–")), "lint"),
            ("placeholders", len(d["placeholders"]), None),
            ("fail clusters", len(clusters), "triage"),
            ("flaky quarantined", flaky, None),
            ("vplan orphans", len(orphans) if vp_plan is not None else "–", None)):
        o.append("<div class='card'><div class='k'>%s</div><div class='v'>%s%s</div></div>"
                 % (_esc(label), _esc(val),
                    _stale(d["sources"].get(src), cfg) if src else ""))
    o.append("</div>")

    # ---- panels ----
    def panel(title, count, rows_html, opened=False):
        o.append("<details%s><summary>%s <span class='cnt'>(%s)</span></summary>"
                 "<div class='panel'>%s</div></details>"
                 % (" open" if opened else "", _esc(title), count, rows_html))

    ph = "<table><tr><th>file:line</th><th>stub</th></tr>" + "".join(
        "<tr><td class='mono'>%s:%d</td><td>%s</td></tr>"
        % (_esc(p["file"]), p["line"], _esc(p["text"])) for p in d["placeholders"]) + "</table>" \
        if d["placeholders"] else "<p class='mono'>none — no unresolved check stubs.</p>"
    panel("PLACEHOLDER-CHECK inventory", len(d["placeholders"]), ph)

    if vp_plan is None:
        vp_html = "<p class='mono'>no vplan.md found%s</p>" % _stale(None, cfg)
    else:
        vp_html = ("<p>plan items: <b>%d</b> · referenced in code: <b>%d</b> · "
                   "orphans (in plan, no code ref): <b>%d</b> · unknown (in code, not in plan): <b>%d</b>%s</p>"
                   % (len(vp_plan), len(vp_plan & vp_code), len(orphans), len(unknown),
                      _stale(d["sources"].get("vplan"), cfg)))
        if orphans:
            vp_html += "<p><b>orphans:</b> <span class='mono'>%s</span></p>" % _esc(", ".join(orphans[:40]))
        if unknown:
            vp_html += "<p><b>unknown refs:</b> <span class='mono'>%s</span></p>" % _esc(", ".join(unknown[:40]))
    panel("vPlan traceability", len(vp_plan) if vp_plan is not None else "?", vp_html)

    if clusters:
        cl = "<table><tr><th>#</th><th>size</th><th>signature</th><th>verdict</th><th>repro</th></tr>"
        for c in clusters:
            rep = c.get("repro") or {}
            cl += ("<tr><td>%s</td><td>%s</td><td class='mono'>%s</td><td>%s%s</td>"
                   "<td class='mono'>%s seed %s</td></tr>"
                   % (c.get("id", ""), c.get("size", ""), _esc(c.get("signature", ""))[:110],
                      _led("fail" if c.get("verdict") in ("tb_bug", "dut_suspect") else "warn"),
                      _esc(c.get("verdict", "")), _esc(rep.get("test", "")), _esc(rep.get("seed", ""))))
        cl += "</table>"
    else:
        cl = "<p class='mono'>no triage.json — run regression triage to populate.</p>"
    panel("Regression clusters", len(clusters), cl)

    lf = (d["lint"] or {}).get("findings", [])
    lint_html = "<table><tr><th>sev</th><th>rule</th><th>file:line</th><th>message</th></tr>" + "".join(
        "<tr><td>%s%s</td><td class='mono'>%s</td><td class='mono'>%s:%s</td><td>%s</td></tr>"
        % (_led("fail" if f.get("severity") == "error" else "warn"), _esc(f.get("severity", "")),
           _esc(f.get("rule_id", "")), _esc(f.get("file", "")), f.get("line", ""),
           _esc(f.get("message", ""))) for f in lf) + "</table>" \
        if lf else "<p class='mono'>no lint findings%s</p>" % _stale(d["sources"].get("lint"), cfg)
    panel("Lint findings", len(lf), lint_html)

    if d["sessions"]:
        se = "<table><tr><th>when</th><th>agent</th><th>gate</th><th>status</th><th>rtl rev</th></tr>"
        for s in d["sessions"][:20]:
            se += ("<tr><td class='mono'>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                   "<td class='mono'>%s</td></tr>"
                   % (time.strftime("%m-%d %H:%M", time.localtime(s.get("_mtime") or 0)),
                      _esc(s.get("agent", "?")), _esc(s.get("gate", "")),
                      _esc(s.get("status", "")), _esc(s.get("rtl_rev", "?"))))
        se += "</table>"
    else:
        se = ("<p class='mono'>no session sidecars in %s/ — sessions write "
              "session_&lt;date&gt;.json per the evidence contract.</p>"
              % _esc(cfg.get("tool", "status_dir")))
    panel("Agent sessions", len(d["sessions"]), se)

    help_html = (
        "<ul style='margin:6px 0 0;padding-left:18px;line-height:1.7'>"
        "<li><b>Start at the amber Pending panel</b> — it lists what blocks the "
        "flow until a human acts (approvals, sign-offs, exclusions, open "
        "questions, unresolved PLACEHOLDER-CHECKs). Empty = unblocked.</li>"
        "<li><b>Verdict row</b>: LEDs are the 9 review axes; the badge is the "
        "milestone reached. A red axis with a failing DoD is what stops the "
        "next milestone.</li>"
        "<li><b>Red regression?</b> Debug the top cluster's repro (test+seed), "
        "not every failure — one fix usually clears the whole cluster.</li>"
        "<li><b>Before an MR</b>: placeholders and lint errors should be 0.</li>"
        "<li><b>STALE / no data</b>: the source JSON is old or was never "
        "produced — re-run the matching <code>dv</code> step and regenerate "
        "with <code>dv dashboard %s</code>.</li>"
        "<li>Panels feed from <code>%s/</code> verdicts plus live tag scans; "
        "retarget via <code>dashboard.ini</code> [tool].</li>"
        "</ul>") % (_esc(d["ip"]), _esc(cfg.get("tool", "status_dir")))
    panel("How to read this", "?", help_html)

    o.append("</body></html>")
    return "".join(o)


def render_index(items, cfg):
    o = ["<!doctype html><html><head><meta charset='utf-8'><title>%s — index</title>"
         "<style>%s</style></head><body><h1>%s — all IPs</h1>"
         "<div class='sub'>generated %s</div><table><tr><th>ip</th><th>milestone</th>"
         "<th>pending human</th><th>placeholders</th><th>clusters</th><th>page</th></tr>"
         % (_esc(cfg.get("display", "title")), CSS, _esc(cfg.get("display", "title")),
            time.strftime("%Y-%m-%d %H:%M"))]
    for it in items:
        ms = ((it["d"]["review"] or {}).get("summary", {}) or {}).get("milestone_ready")
        o.append("<tr><td><b>%s</b></td><td><span class='badge %s'>%s</span></td>"
                 "<td>%d</td><td>%d</td><td>%d</td><td><a href='%s'>open</a></td></tr>"
                 % (_esc(it["d"]["ip"]), _esc(ms) if ms else "nd", _esc(ms) if ms else "n/a",
                    len(it["d"]["pending"]), len(it["d"]["placeholders"]),
                    len((it["d"]["triage"] or {}).get("clusters", [])), _esc(it["page"])))
    o.append("</table></body></html>")
    return "".join(o)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="local DV dashboard generator")
    ap.add_argument("ip", nargs="?", help="path to the IP directory")
    ap.add_argument("--all", action="store_true", help="all IPs + index page")
    ap.add_argument("--root", default=".", help="repo root (config + discovery)")
    ap.add_argument("--config", default=None, help="dashboard.ini path")
    ap.add_argument("--out", default=None, help="output html (single-IP mode)")
    args = ap.parse_args()

    cfg = load_cfg(args.root, args.config)

    if args.all:
        ips = sorted({os.path.dirname(p) for p in
                      glob.glob(os.path.join(args.root, cfg.get("tool", "ip_glob")))})
        if not ips:
            sys.exit("no IPs found with ip_glob=%r under %s" % (cfg.get("tool", "ip_glob"), args.root))
        items = []
        for ip in ips:
            d = collect(ip, cfg)
            page = "dashboard_%s.html" % d["ip"]
            with open(os.path.join(args.root, page), "w") as fh:
                fh.write(render_ip(d, cfg))
            items.append({"d": d, "page": page})
            print("wrote", page, file=sys.stderr)
        idx = os.path.join(args.root, "index.html")
        with open(idx, "w") as fh:
            fh.write(render_index(items, cfg))
        print("wrote", idx, file=sys.stderr)
        return

    if not args.ip:
        sys.exit("usage: dashboard.py <ip_path> | --all")
    d = collect(args.ip, cfg)
    out = args.out or os.path.join(args.ip, "dashboard.html")
    with open(out, "w") as fh:
        fh.write(render_ip(d, cfg))
    print("wrote %s  (pending=%d placeholders=%d clusters=%d)"
          % (out, len(d["pending"]), len(d["placeholders"]),
             len((d["triage"] or {}).get("clusters", []))), file=sys.stderr)


if __name__ == "__main__":
    main()
