"""Render plan + write policy for uvm-gen.

Write policy (the tool's contract):
  * a file that does not exist is created;
  * a file that exists is NEVER touched (so re-running after adding an agent
    to the YAML creates just the new agent's files);
  * ``--force`` regenerates everything EXCEPT ``verif_matrix.yaml``, which is
    verification history, not generated code;
  * nothing is ever deleted.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import __version__
from .config import ROLES, canonical_params, param_hash_hex

TEMPLATE_ROOT = Path(__file__).parent / "templates"

# Files that --force must not overwrite (data, not generated code).
PROTECTED = {"verif_matrix.yaml"}


@dataclass
class Action:
    """One planned output file."""

    relpath: str                      # destination, relative to the env root
    template: str | None = None      # template to render, or ...
    source: Path | None = None       # ... a file to copy verbatim, or ...
    content: str | None = None       # ... literal content
    ctx: dict = field(default_factory=dict)  # per-file template context


@dataclass
class GenResult:
    env_root: Path
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    protected: list[str] = field(default_factory=list)


def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _sv_literal(value) -> str:
    return f'"{value}"' if isinstance(value, str) else str(value)


def build_context(cfg: dict, input_basename: str) -> dict:
    """Template context shared by every rendered file."""
    ip = cfg["ip_name"]
    agents = [
        {
            "name": a["name"],
            "mode": a["mode"],
            "uvm_active": "UVM_ACTIVE" if a["mode"] == "active" else "UVM_PASSIVE",
        }
        for a in cfg["agents"]
    ]
    vips = []
    for v in cfg["vips"]:
        vips.append(
            {
                "protocol": v["protocol"],
                "name": v["name"],
                "role": v["role"],
                "uvm_active": "UVM_PASSIVE" if v["role"] == "passive" else "UVM_ACTIVE",
                "guard_define": f"{ip.upper()}_USE_CDN_{v['protocol'].upper()}_VIP",
                "ibi_enable_bit": 1 if v.get("ibi_enable", True) else 0,
                "roles_str": "/".join(ROLES[v["protocol"]]),
            }
        )
    params = []
    for p in cfg["params"]:
        is_str = isinstance(p["value"], str)
        sv_type = "string" if is_str else "int"
        params.append(
            {
                "name": p["name"],
                "value": p["value"],
                "style": p["style"],
                "path": p["path"],
                "is_str": is_str,
                "fmt": "%s" if is_str else "%0d",
                "plusarg_fmt": "%s" if is_str else "%d",
                "sv_decl": f"{sv_type} {p['name']} = {_sv_literal(p['value'])};",
                "sv_literal": _sv_literal(p["value"]),
            }
        )
    return {
        "tool_version": __version__,
        "ip": ip,
        "IP": ip.upper(),
        "config_name": cfg["config_name"],
        "dut_module": cfg["dut"]["module"],
        "rtl_filelist": cfg["dut"]["rtl_filelist"],
        # possibly refined by finalize_context() once the output dir is known
        "rtl_filelist_sim": cfg["dut"]["rtl_filelist"],
        "agents": agents,
        "vips": vips,
        "vip_protocols": sorted({v["protocol"] for v in vips}),
        "params": params,
        "defparam_params": [p for p in params if p["style"] == "defparam"],
        "first_agent": agents[0]["name"] if agents else None,
        "input_basename": input_basename,
        "params_canonical": canonical_params(cfg["params"]),
        "param_hash": param_hash_hex(cfg["params"]),
    }


def finalize_context(ctx: dict, config_path: Path, env_root: Path) -> None:
    """Re-express dut.rtl_filelist (given relative to the YAML) relative to
    the generated sim/ directory, where dut.f consumes it. Paths using
    environment variables ('$...') are kept verbatim."""
    rtl = ctx["rtl_filelist"]
    if not rtl or "$" in rtl:
        return
    src = Path(config_path).parent / rtl
    if not src.is_absolute():
        src = src.resolve()
    try:
        rel = os.path.relpath(src, (env_root / "sim").resolve())
    except ValueError:  # e.g. different drive on Windows
        rel = None
    if rel is None or _leading_ups(rel) > 4:
        # unrelated trees - an absolute path reads better than ../../../..
        ctx["rtl_filelist_sim"] = str(src)
    else:
        ctx["rtl_filelist_sim"] = rel


def _leading_ups(relpath: str) -> int:
    count = 0
    for part in Path(relpath).parts:
        if part != "..":
            break
        count += 1
    return count


def _rewrite_extends(text: str, base_basename: str) -> str:
    """Point the copied config's 'extends' at its sibling copy in cfg/."""
    return re.sub(
        r"^(\s*extends\s*:).*$",
        rf"\1 {base_basename}",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def plan(cfg: dict, chain: list[Path], ctx: dict) -> list[Action]:
    ip = ctx["ip"]
    actions: list[Action] = []

    def render(relpath: str, template: str, **extra):
        actions.append(Action(relpath=relpath, template=template, ctx=extra))

    # --- env root --------------------------------------------------------
    render("README.md", "env_readme.md.j2")
    render(".gitignore", "gitignore.j2")
    render("verif_matrix.yaml", "verif_matrix.yaml.j2")

    # --- cfg/: copies of the input config chain (base first) --------------
    for i, src in enumerate(chain):
        text = src.read_text(encoding="utf-8")
        if i > 0:
            text = _rewrite_extends(text, chain[i - 1].name)
        actions.append(Action(relpath=f"cfg/{src.name}", content=text, source=src))

    # --- agents/ -----------------------------------------------------------
    agent_templates = [
        ("if.sv.j2", "{ip}_{name}_if.sv"),
        ("seq_item.sv.j2", "{ip}_{name}_seq_item.sv"),
        ("cfg.sv.j2", "{ip}_{name}_cfg.sv"),
        ("sequencer.sv.j2", "{ip}_{name}_sequencer.sv"),
        ("driver.sv.j2", "{ip}_{name}_driver.sv"),
        ("monitor.sv.j2", "{ip}_{name}_monitor.sv"),
        ("agent.sv.j2", "{ip}_{name}_agent.sv"),
        ("base_seq.sv.j2", "{ip}_{name}_base_seq.sv"),
        ("agent_pkg.sv.j2", "{ip}_{name}_agent_pkg.sv"),
    ]
    for a in ctx["agents"]:
        for template, name_fmt in agent_templates:
            fname = name_fmt.format(ip=ip, name=a["name"])
            render(f"agents/{a['name']}_agent/{fname}", f"agent/{template}", a=a)

    # --- env/ --------------------------------------------------------------
    render(f"env/{ip}_reg_block.sv", "env/reg_block.sv.j2")
    if ctx["first_agent"]:
        render(f"env/{ip}_reg_adapter.sv", "env/reg_adapter.sv.j2")
    for v in ctx["vips"]:
        render(f"env/{ip}_{v['name']}_vip.sv", "env/vip.sv.j2", v=v)
    render(f"env/{ip}_env_cfg.sv", "env/env_cfg.sv.j2")
    render(f"env/{ip}_scoreboard.sv", "env/scoreboard.sv.j2")
    for a in ctx["agents"]:
        render(f"env/{ip}_{a['name']}_cov.sv", "env/cov.sv.j2", a=a)
    render(f"env/{ip}_vsequencer.sv", "env/vsequencer.sv.j2")
    render(f"env/{ip}_env.sv", "env/env.sv.j2")
    render(f"env/{ip}_env_pkg.sv", "env/env_pkg.sv.j2")

    # --- seq_lib/ ------------------------------------------------------------
    render(f"seq_lib/{ip}_base_vseq.sv", "seq_lib/base_vseq.sv.j2")
    render(f"seq_lib/{ip}_smoke_vseq.sv", "seq_lib/smoke_vseq.sv.j2")
    render(f"seq_lib/{ip}_seq_pkg.sv", "seq_lib/seq_pkg.sv.j2")

    # --- tests/ --------------------------------------------------------------
    render(f"tests/{ip}_base_test.sv", "tests/base_test.sv.j2")
    render(f"tests/{ip}_smoke_test.sv", "tests/smoke_test.sv.j2")
    render(f"tests/{ip}_test_pkg.sv", "tests/test_pkg.sv.j2")

    # --- tb/ -------------------------------------------------------------------
    render(f"tb/{ctx['dut_module']}_stub.sv", "tb/dut_stub.sv.j2")
    render("tb/tb_top.sv", "tb/tb_top.sv.j2")

    # --- sim/ ------------------------------------------------------------------
    render("sim/Makefile", "sim/Makefile.j2")
    render("sim/dut.f", "sim/dut.f.j2")
    render("sim/tb.f", "sim/tb.f.j2")
    for proto in ctx["vip_protocols"]:
        instances = [v for v in ctx["vips"] if v["protocol"] == proto]
        render(
            f"sim/vip_{proto}.f",
            "sim/vip.f.j2",
            proto=proto,
            instances=instances,
            guard=instances[0]["guard_define"],
        )
    render(f"sim/{ip}_{ctx['config_name']}.vsif", "sim/vsif.j2")
    render("sim/probe.tcl", "sim/probe.tcl.j2")
    actions.append(
        Action(relpath="sim/scripts/cfg_tool.py", source=TEMPLATE_ROOT / "sim/cfg_tool.py")
    )

    seen: dict[str, str] = {}
    for act in actions:
        if act.relpath in seen:
            raise RuntimeError(
                f"internal plan collision on '{act.relpath}' - check agent/vip names"
            )
        seen[act.relpath] = act.template or "copy"
    return actions


def execute(
    actions: list[Action],
    env_root: Path,
    ctx: dict,
    force: bool = False,
    dry_run: bool = False,
) -> GenResult:
    env = jinja_env()
    result = GenResult(env_root=env_root)
    for act in actions:
        dest = env_root / act.relpath
        if act.content is not None:
            content = act.content
        elif act.source is not None:
            if act.source.resolve() == dest.resolve():
                # input config already lives in cfg/ - never rewrite the input
                result.skipped.append(act.relpath + "  (is the input file)")
                continue
            content = act.source.read_text(encoding="utf-8")
        else:
            content = env.get_template(act.template).render(**{**ctx, **act.ctx})

        if dest.exists():
            if not force:
                result.skipped.append(act.relpath)
                continue
            if act.relpath in PROTECTED:
                result.protected.append(act.relpath)
                continue
            result.overwritten.append(act.relpath)
        else:
            result.created.append(act.relpath)

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
    return result


def new_agent_hints(result: GenResult, ctx: dict) -> list[str]:
    """When agent files were created into an existing env, tell the user what
    to wire up by hand (existing files are never modified)."""
    new_agents = sorted(
        {
            m.group(1)
            for p in result.created
            if (m := re.match(r"agents/(\w+)_agent/", p))
        }
    )
    if not new_agents or not result.skipped:
        return []
    ip = ctx["ip"]
    hints = [
        f"new agent(s) {', '.join(new_agents)} were generated, but existing env "
        "files are never modified - wire them in by hand:",
    ]
    for n in new_agents:
        hints += [
            f"  [{n}] env/{ip}_env_cfg.sv     : add '{ip}_{n}_cfg {n}_cfg;' (+ create in new(), set_all_passive/active)",
            f"  [{n}] env/{ip}_env_pkg.sv     : import {ip}_{n}_agent_pkg::*; include env/{ip}_{n}_cov.sv",
            f"  [{n}] env/{ip}_env.sv         : create {n}_agent (+ cov), connect scoreboard/vsequencer",
            f"  [{n}] env/{ip}_scoreboard.sv  : add analysis imp + write_{n}()",
            f"  [{n}] env/{ip}_vsequencer.sv  : add '{ip}_{n}_sequencer {n}_sqr;'",
            f"  [{n}] seq_lib/{ip}_smoke_vseq.sv : add stimulus branch (guard for null sequencer)",
            f"  [{n}] tests/{ip}_base_test.sv : fetch '{n}_vif' into cfg.{n}_cfg.vif",
            f"  [{n}] tb/tb_top.sv            : instantiate {ip}_{n}_if, publish '{n}_vif'",
            f"  [{n}] sim/tb.f                : add +incdir+ and the interface/package lines",
        ]
    return hints
