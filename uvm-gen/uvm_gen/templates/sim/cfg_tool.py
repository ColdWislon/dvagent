#!/usr/bin/env python3
"""uvm-gen simulation helper (copied verbatim into sim/scripts/ by uvm-gen).

IP-agnostic: everything is derived from the configuration YAML and the
simulation log. Invoked by sim/Makefile - not usually run by hand.

Subcommands
-----------
makevars <cfg.yaml> [--out FILE.mk]
    Resolve the 'extends' chain of the configuration and emit make variables:
    CONFIG_NAME, PARAM_XRUN_ARGS (+define+ / -defparam), PARAM_PLUSARGS
    (+PARAM_<name>=...), VIP_PROTOCOLS.

collect <cfg.yaml> --log LOG --test TEST --seed SEED --matrix FILE [--coverage PCT]
    Parse the run log (config signature banner + UVM report summary), append
    one record to verif_matrix.yaml, print a one-line verdict. Exit status is
    the pass/fail verdict - vManager and CI use it directly.

matrix <verif_matrix.yaml>
    Print the per-configuration verification summary table.

The FNV-1a hash and the canonical parameter string implemented here MUST match
<ip>_env_cfg::params_canonical()/param_hash() in the generated SV (and the
uvm-gen generator itself).
"""

import argparse
import datetime
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("cfg_tool: PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)


# ----------------------------------------------------------------------------
# Configuration loading (mirror of the uvm-gen generator, kept dependency-free)
# ----------------------------------------------------------------------------

class CfgError(Exception):
    pass


def fnv1a32(s):
    h = 0x811C9DC5
    for byte in s.encode("utf-8"):
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return h


def deep_merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base[key], value) if key in base else value
        return merged
    return override


def resolve_cfg_path(path):
    """Accept paths relative to sim/ (the cwd) or to the *_verif root."""
    if os.path.exists(path) or os.path.isabs(path):
        return path
    parent = os.path.join("..", path)
    if os.path.exists(parent):
        return parent
    return path  # let the open() error carry the original name


def load_cfg(path):
    """Resolve the 'extends' chain and deep-merge (config file wins)."""
    seen = set()

    def _load(p):
        p = os.path.abspath(p)
        if p in seen:
            raise CfgError("circular 'extends' chain at %s" % p)
        seen.add(p)
        try:
            with open(p, "r") as fh:
                data = yaml.safe_load(fh) or {}
        except OSError as exc:
            raise CfgError("cannot read config: %s" % exc)
        except yaml.YAMLError as exc:
            raise CfgError("invalid YAML in %s: %s" % (p, exc))
        if not isinstance(data, dict):
            raise CfgError("%s: top level must be a YAML mapping" % p)
        extends = data.pop("extends", None)
        if extends is None:
            return data
        if not isinstance(extends, str):
            raise CfgError("%s: 'extends' must be a path string" % p)
        base = _load(os.path.join(os.path.dirname(p), extends))
        return deep_merge(base, data)

    return _load(path)


def normalize_params(cfg):
    """-> sorted list of dicts {name, value, style, path}."""
    params = []
    raw = cfg.get("params") or {}
    if not isinstance(raw, dict):
        raise CfgError("'params' must be a mapping")
    for name, spec in raw.items():
        style, path, value = "define", None, spec
        if isinstance(spec, dict):
            value = spec.get("value")
            style = spec.get("style", "define")
            path = spec.get("path")
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, (int, str)):
            raise CfgError("param '%s': unsupported value %r" % (name, value))
        if style not in ("define", "defparam", "env"):
            raise CfgError("param '%s': unknown style %r" % (name, style))
        params.append({"name": name, "value": value, "style": style, "path": path})
    params.sort(key=lambda p: p["name"])
    return params


def canonical_params(params):
    return ",".join("%s=%s" % (p["name"], p["value"]) for p in params)


def param_hash_hex(params):
    return "0x%08x" % fnv1a32(canonical_params(params))


# ----------------------------------------------------------------------------
# makevars
# ----------------------------------------------------------------------------

def cmd_makevars(args):
    path = resolve_cfg_path(args.config)
    cfg = load_cfg(path)
    params = normalize_params(cfg)
    config_name = str(cfg.get("config_name", "default"))

    xrun_args, plusargs = [], []
    for p in params:
        if p["style"] == "define":
            xrun_args.append("+define+%s=%s" % (p["name"], p["value"]))
        elif p["style"] == "defparam":
            target = p["path"] or ("tb_top.dut.%s" % p["name"])
            xrun_args.append("-defparam %s=%s" % (target, p["value"]))
        plusargs.append("+PARAM_%s=%s" % (p["name"], p["value"]))

    protocols = sorted({v.get("protocol") for v in (cfg.get("vips") or [])
                        if isinstance(v, dict) and v.get("protocol")})

    lines = [
        "# generated by cfg_tool.py makevars - do not edit, do not commit",
        "CONFIG_NAME := %s" % config_name,
        "CONFIG_HASH := %s" % param_hash_hex(params),
        "PARAM_XRUN_ARGS := %s" % " ".join(xrun_args),
        "PARAM_PLUSARGS := %s" % " ".join(plusargs),
        "VIP_PROTOCOLS := %s" % " ".join(protocols),
        "",
    ]
    text = "\n".join(lines)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


# ----------------------------------------------------------------------------
# collect
# ----------------------------------------------------------------------------

BANNER_NAME_RE = re.compile(r"\[UVM_GEN_CFG\]\s*config_name\s*:\s*(\S+)")
BANNER_HASH_RE = re.compile(r"\[UVM_GEN_CFG\]\s*param_hash\s*:\s*(0x[0-9a-fA-F]+)")
BANNER_PARAM_RE = re.compile(r"\[UVM_GEN_CFG\]\s*param\s+(\w+)\s*=\s*(\S+)")
SUMMARY_RE = {
    "uvm_errors": re.compile(r"^\s*UVM_ERROR\s*:\s*(\d+)\s*$", re.MULTILINE),
    "uvm_fatals": re.compile(r"^\s*UVM_FATAL\s*:\s*(\d+)\s*$", re.MULTILINE),
}
SEED_RES = (
    re.compile(r"SVSEED\s*[:=]\s*(\d+)", re.IGNORECASE),
    re.compile(r"-svseed\s+(\d+)"),
    re.compile(r"random seed\s*[:=]?\s*(\d+)", re.IGNORECASE),
)


def _maybe_int(text):
    try:
        return int(text)
    except ValueError:
        return text


def parse_log(log_path):
    info = {
        "log_found": False,
        "banner_found": False,
        "summary_found": False,
        "config_name": None,
        "param_hash": None,
        "params": {},
        "uvm_errors": None,
        "uvm_fatals": None,
        "seed": None,
    }
    try:
        with open(log_path, "r", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return info
    info["log_found"] = True

    m = BANNER_NAME_RE.search(text)
    if m:
        info["banner_found"] = True
        info["config_name"] = m.group(1)
    m = BANNER_HASH_RE.search(text)
    if m:
        info["param_hash"] = m.group(1)
    for name, value in BANNER_PARAM_RE.findall(text):
        info["params"][name] = _maybe_int(value)

    counts = {}
    for key, rx in SUMMARY_RE.items():
        matches = rx.findall(text)
        if matches:
            counts[key] = int(matches[-1])  # the report summary is last
    if len(counts) == len(SUMMARY_RE):
        info["summary_found"] = True
        info.update(counts)

    for rx in SEED_RES:
        m = rx.search(text)
        if m:
            info["seed"] = int(m.group(1))
            break
    return info


def git_rev(start_dir):
    try:
        out = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        rev = out.stdout.strip()
        return rev if out.returncode == 0 and rev else "unknown"
    except Exception:
        return "unknown"


def append_record(matrix_path, record):
    text = yaml.safe_dump([record], sort_keys=False, default_flow_style=False)
    directory = os.path.dirname(os.path.abspath(matrix_path)) or "."
    os.makedirs(directory, exist_ok=True)
    with open(matrix_path, "a") as fh:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except Exception:
            pass  # non-POSIX fallback: plain append
        fh.write(text)


def cmd_collect(args):
    path = resolve_cfg_path(args.config)
    try:
        cfg = load_cfg(path)
        params = normalize_params(cfg)
        yaml_name = str(cfg.get("config_name", "default"))
        yaml_hash = param_hash_hex(params)
        yaml_params = {p["name"]: p["value"] for p in params}
    except CfgError as exc:
        sys.stderr.write("cfg_tool: warning: %s\n" % exc)
        yaml_name, yaml_hash, yaml_params = "unknown", None, {}

    info = parse_log(args.log)

    passed = bool(
        info["banner_found"]
        and info["summary_found"]
        and info["uvm_errors"] == 0
        and info["uvm_fatals"] == 0
    )
    if not info["log_found"]:
        reason = "no_log"
    elif not info["banner_found"] or not info["summary_found"]:
        reason = "no_uvm_summary"  # compile/elaboration error or early abort
    elif not passed:
        reason = "uvm_errors"
    else:
        reason = None

    seed = _maybe_int(args.seed) if args.seed is not None else None
    if not isinstance(seed, int) and info["seed"] is not None:
        seed = info["seed"]

    matrix_dir = os.path.dirname(os.path.abspath(args.matrix)) or "."
    record = {
        "config_name": info["config_name"] or yaml_name,
        "param_hash": info["param_hash"] or yaml_hash,
        "test": args.test,
        "seed": seed,
        "result": "pass" if passed else "fail",
        "uvm_errors": info["uvm_errors"],
        "uvm_fatals": info["uvm_fatals"],
        "coverage": _maybe_int(args.coverage) if args.coverage is not None else None,
        "date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "git_rev": git_rev(matrix_dir),
        "log": args.log,
        "params": info["params"] or yaml_params,
    }
    if reason:
        record["fail_reason"] = reason
    append_record(args.matrix, record)

    verdict = "PASS" if passed else "FAIL (%s)" % reason
    print(
        "cfg_tool: %s  test=%s config=%s hash=%s seed=%s -> recorded in %s"
        % (verdict, args.test, record["config_name"], record["param_hash"],
           seed, args.matrix)
    )
    return 0 if passed else 1


# ----------------------------------------------------------------------------
# matrix
# ----------------------------------------------------------------------------

def cmd_matrix(args):
    try:
        with open(args.matrix, "r") as fh:
            records = yaml.safe_load(fh) or []
    except OSError:
        print("cfg_tool: no verification records yet (%s not found)" % args.matrix)
        return 0
    if not isinstance(records, list) or not records:
        print("cfg_tool: no verification records yet in %s" % args.matrix)
        return 0

    groups = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        key = (str(rec.get("config_name")), str(rec.get("param_hash")))
        g = groups.setdefault(
            key,
            {"runs": 0, "pass": 0, "fail": 0, "tests": set(),
             "last_date": "", "last_git": "", "coverage": None},
        )
        g["runs"] += 1
        g["pass" if rec.get("result") == "pass" else "fail"] += 1
        if rec.get("test"):
            g["tests"].add(str(rec["test"]))
        date = str(rec.get("date") or "")
        if date >= g["last_date"]:
            g["last_date"] = date
            g["last_git"] = str(rec.get("git_rev") or "")
        if rec.get("coverage") is not None:
            g["coverage"] = rec["coverage"]

    header = ("CONFIG", "PARAM_HASH", "RUNS", "PASS", "FAIL", "COV%",
              "LAST_RUN", "GIT", "TESTS")
    rows = []
    for (name, phash), g in sorted(groups.items()):
        tests = ",".join(sorted(g["tests"])) or "-"
        if len(tests) > 40:
            tests = tests[:37] + "..."
        cov = "-" if g["coverage"] is None else str(g["coverage"])
        rows.append((name, phash, str(g["runs"]), str(g["pass"]),
                     str(g["fail"]), cov, g["last_date"][:16] or "-",
                     g["last_git"] or "-", tests))

    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    fmt = "  ".join("%%-%ds" % w for w in widths)
    print("Verification matrix (%s):" % args.matrix)
    print(fmt % header)
    print(fmt % tuple("-" * w for w in widths))
    for row in rows:
        print(fmt % row)
    failing = [name for (name, _), g in sorted(groups.items()) if g["fail"]]
    if failing:
        print("\nATTENTION: configuration(s) with failures: %s" % ", ".join(failing))
    return 0


# ----------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog="cfg_tool.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("makevars", help="emit make variables for a config YAML")
    p.add_argument("config")
    p.add_argument("--out", help="write to this file instead of stdout")
    p.set_defaults(func=cmd_makevars)

    p = sub.add_parser("collect", help="record one simulation run")
    p.add_argument("config")
    p.add_argument("--log", required=True)
    p.add_argument("--test", required=True)
    p.add_argument("--seed", default=None)
    p.add_argument("--matrix", required=True)
    p.add_argument("--coverage", default=None,
                   help="coverage %% for this run, if known (e.g. from IMC)")
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("matrix", help="print the verification summary table")
    p.add_argument("matrix")
    p.set_defaults(func=cmd_matrix)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CfgError as exc:
        sys.stderr.write("cfg_tool: error: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
