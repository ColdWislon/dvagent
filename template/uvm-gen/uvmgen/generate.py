"""Render the verification environment from a validated configuration.

Write policy (re-run semantics):
  * a file that does not exist is created;
  * an existing file is NEVER touched (re-running with an extended YAML only
    adds the new files, e.g. a newly listed agent);
  * --force regenerates everything;
  * existing files whose freshly rendered content differs are reported as
    "stale" so the user knows what to wire up by hand after adding
    agents/VIPs (tb.f, env class, ...).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import __version__
from .config import param_hash
from .vip import PROTOCOLS

TEMPLATE_ROOT = Path(__file__).parent / "templates"

#: prompt files of the Copilot agentic verification kit (phase order matters)
COPILOT_PROMPTS = [
    "connect-dut",
    "implement-agents",
    "write-tests",
    "triage-regression",
    "coverage-closure",
    "verif-closure",
]


@dataclass
class GenReport:
    """What one generator invocation did (or would do, for dry runs)."""

    env_root: Path
    created: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    forced: list = field(default_factory=list)
    stale: list = field(default_factory=list)


def jinja_env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _sv_literal(value):
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


def _enrich_agent(ip, agent):
    return {
        **agent,
        "NAME": agent["name"].upper(),
        "kind": "agent",
        "active_enum": "UVM_ACTIVE" if agent["mode"] == "active" else "UVM_PASSIVE",
        "item_type": f"{ip}_{agent['name']}_seq_item",
        "cfg_class": f"{ip}_{agent['name']}_agent_cfg",
    }


def _enrich_vip(ip, vip):
    proto = PROTOCOLS[vip["protocol"]]
    knobs = [
        {**knob, "sv_default": _sv_literal(vip.get(knob["name"], knob["default"]))}
        for knob in proto["knobs"]
    ]
    return {
        **vip,
        "NAME": vip["name"].upper(),
        "kind": "vip",
        "active_enum": "UVM_PASSIVE" if vip["role"] == "monitor" else "UVM_ACTIVE",
        "item_type": "uvm_sequence_item",
        "cfg_class": f"{ip}_{vip['name']}_vip_cfg",
        "title": proto["title"],
        "knobs": knobs,
        "example_pkg": proto["example_pkg"],
        "example_agent": proto["example_agent"],
        "example_cfg": proto["example_cfg"],
    }


def build_context(cfg, chain):
    """Assemble the single context dict every template renders against."""
    ip = cfg["ip_name"]
    agents = [_enrich_agent(ip, a) for a in cfg["agents"]]
    vips = [_enrich_vip(ip, v) for v in cfg["vips"]]

    params = []
    for name, value in cfg["params"].items():
        is_int = isinstance(value, int)
        params.append({
            "name": name,
            "value": value,
            "is_int": is_int,
            "sv_type": "int unsigned" if is_int else "string",
            "field": f"prm_{name.lower()}",
            "sv_default": str(value) if is_int else f'"{value}"',
        })

    config_name = cfg["config_name"]
    cfg_relname = chain[-1].name
    vsif_name = f"{ip}.vsif" if config_name == "default" else f"{ip}_{config_name}.vsif"

    vip_protocols = []
    for v in cfg["vips"]:
        if v["protocol"] not in vip_protocols:
            vip_protocols.append(v["protocol"])

    return {
        "ip": ip,
        "IP": ip.upper(),
        "gen_version": __version__,
        "dut": cfg["dut"],
        "config_name": config_name,
        "param_hash": param_hash(cfg),
        "param_style": cfg["param_style"],
        "params": params,
        "defines": cfg["defines"],
        "agents": agents,
        "vips": vips,
        "all_ifs": agents + vips,
        "reg_agent": agents[0] if agents else None,
        "vip_protocols": vip_protocols,
        "cfg_relname": cfg_relname,
        "cfg_rel_from_root": f"cfg/{cfg_relname}",
        "vsif_name": vsif_name,
        "copilot_prompts": COPILOT_PROMPTS,
    }


def manifest(ctx):
    """(output relpath, template name, extra context) for every generated file."""
    ip = ctx["ip"]
    files = [
        ("README.md", "root/README.md.j2", {}),
        (".gitignore", "root/gitignore.j2", {}),
        ("Makefile", "root/Makefile.j2", {}),
        ("verif_matrix.yaml", "root/verif_matrix.yaml.j2", {}),
        (".github/copilot-instructions.md", "copilot/copilot-instructions.md.j2", {}),
        (f"env/{ip}_reg_block.sv", "env/reg_block.sv.j2", {}),
        (f"env/{ip}_reg_adapter.sv", "env/reg_adapter.sv.j2", {}),
        (f"env/{ip}_env_cfg.sv", "env/env_cfg.sv.j2", {}),
        (f"env/{ip}_scoreboard.sv", "env/scoreboard.sv.j2", {}),
        (f"env/{ip}_virtual_sequencer.sv", "env/virtual_sequencer.sv.j2", {}),
        (f"env/{ip}_env.sv", "env/env.sv.j2", {}),
        (f"env/{ip}_env_pkg.sv", "env/env_pkg.sv.j2", {}),
        (f"seq_lib/{ip}_base_vseq.sv", "seq_lib/base_vseq.sv.j2", {}),
        (f"seq_lib/{ip}_smoke_vseq.sv", "seq_lib/smoke_vseq.sv.j2", {}),
        (f"seq_lib/{ip}_seq_lib_pkg.sv", "seq_lib/seq_lib_pkg.sv.j2", {}),
        (f"tests/{ip}_base_test.sv", "tests/base_test.sv.j2", {}),
        (f"tests/{ip}_smoke_test.sv", "tests/smoke_test.sv.j2", {}),
        (f"tests/{ip}_test_pkg.sv", "tests/test_pkg.sv.j2", {}),
        (f"tb/{ip}_dut_stub.sv", "tb/dut_stub.sv.j2", {}),
        (f"tb/{ip}_tb_top.sv", "tb/tb_top.sv.j2", {}),
        ("sim/Makefile", "sim/Makefile.j2", {}),
        ("sim/tb.f", "sim/tb.f.j2", {}),
        (f"sim/{ctx['vsif_name']}", "sim/vsif.j2", {}),
        ("sim/scripts/cfg2args.py", "sim/cfg2args.py.j2", {}),
        ("sim/scripts/record_result.py", "sim/record_result.py.j2", {}),
        ("sim/scripts/matrix_report.py", "sim/matrix_report.py.j2", {}),
        ("sim/scripts/waves.tcl", "sim/waves.tcl.j2", {}),
    ]

    for prompt in ctx["copilot_prompts"]:
        files.append((
            f".github/prompts/{prompt}.prompt.md",
            f"copilot/{prompt}.prompt.md.j2",
            {},
        ))

    agent_parts = [
        ("if", "if"),
        ("seq_item", "seq_item"),
        ("agent_cfg", "agent_cfg"),
        ("sequencer", "sequencer"),
        ("driver", "driver"),
        ("monitor", "monitor"),
        ("agent", "agent"),
        ("base_seq", "base_seq"),
        ("agent_pkg", "agent_pkg"),
    ]
    for agent in ctx["agents"]:
        adir = f"agents/{agent['name']}_agent"
        for suffix, tmpl in agent_parts:
            files.append((
                f"{adir}/{ip}_{agent['name']}_{suffix}.sv",
                f"agent/{tmpl}.sv.j2",
                {"agent": agent},
            ))
        files.append((
            f"env/{ip}_{agent['name']}_coverage.sv",
            "env/coverage.sv.j2",
            {"agent": agent},
        ))

    for vip in ctx["vips"]:
        vdir = f"vip/{vip['name']}_vip"
        files.append((f"{vdir}/{ip}_{vip['name']}_vip_cfg.sv",
                      "vip/vip_cfg.sv.j2", {"vip": vip}))
        files.append((f"{vdir}/{ip}_{vip['name']}_vip_agent.sv",
                      "vip/vip_agent.sv.j2", {"vip": vip}))
        files.append((f"{vdir}/{ip}_{vip['name']}_vip_pkg.sv",
                      "vip/vip_pkg.sv.j2", {"vip": vip}))

    for proto_key in ctx["vip_protocols"]:
        files.append((
            f"sim/vip_{proto_key}.f",
            "sim/vip.f.j2",
            {"proto": {**PROTOCOLS[proto_key], "key": proto_key}},
        ))

    return files


_EXTENDS_LINE_RE = re.compile(r"^(\s*extends\s*:\s*).*$", re.M)


def _config_copy_text(path):
    """Copy text for a config file; 'extends' rewritten to a sibling basename
    (the whole chain is copied into cfg/ side by side)."""
    text = path.read_text()
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return text
    extends = data.get("extends") if isinstance(data, dict) else None
    if extends:
        base_name = Path(str(extends)).name
        if str(extends) != base_name:
            text = _EXTENDS_LINE_RE.sub(
                lambda m: m.group(1) + base_name, text, count=1)
    return text


def _write(report, env_root, rel, content, force, dry_run):
    if "{{" in content or "{%" in content:
        raise RuntimeError(f"internal error: unrendered template markers in {rel}")
    dest = env_root / rel
    if dest.exists():
        current = dest.read_text()
        if current == content:
            report.skipped.append(rel)
            return
        if not force:
            report.skipped.append(rel)
            report.stale.append(rel)
            return
        report.forced.append(rel)
    else:
        report.created.append(rel)
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    if rel.startswith("sim/scripts/") and rel.endswith(".py"):
        os.chmod(dest, 0o755)


def generate(cfg, chain, output_dir, force=False, dry_run=False):
    """Generate <ip>_verif/ under output_dir; returns a GenReport."""
    ctx = build_context(cfg, chain)
    env_root = Path(output_dir) / f"{ctx['ip']}_verif"
    report = GenReport(env_root=env_root)
    env = jinja_env()

    items = [
        (rel, env.get_template(tmpl).render({**ctx, **extra}))
        for rel, tmpl, extra in manifest(ctx)
    ]
    # copy of the input config (and its whole 'extends' chain) into cfg/
    for path in chain:
        items.append((f"cfg/{path.name}", _config_copy_text(path)))

    for rel, content in items:
        _write(report, env_root, rel, content, force, dry_run)
    return report
