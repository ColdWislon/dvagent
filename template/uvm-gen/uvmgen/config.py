"""Configuration loading, 'extends' deep-merge, validation, and param hashing.

The same semantics are replicated in the generated sim/scripts/cfg2args.py so
that a generated environment is self-contained: banners, matrix records and
Makefile flags always agree with the generator.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

from .vip import PROTOCOLS

SV_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
CONFIG_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class ConfigError(Exception):
    """User-facing configuration problem."""


def deep_merge(base, override):
    """Recursive dict merge; the override (config file) wins. Lists replace."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base[key], value) if key in base else value
        return merged
    return override


def load_config(path):
    """Load a YAML config resolving 'extends' chains (deep-merge, child wins).

    Returns (merged_dict, chain) where chain lists the Paths from the base of
    the extends chain to the requested file itself.
    """
    return _load(Path(path), ())


def _load(path, stack):
    path = Path(path).resolve()
    if path in stack:
        cycle = " -> ".join(str(p) for p in (*stack, path))
        raise ConfigError(f"circular 'extends' chain: {cycle}")
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    data = data or {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a YAML mapping")
    chain = [path]
    extends = data.pop("extends", None)
    if extends is not None:
        base_data, base_chain = _load(path.parent / str(extends), (*stack, path))
        data = deep_merge(base_data, data)
        chain = base_chain + [path]
    return data, chain


def _norm_scalar(value):
    return int(value) if isinstance(value, bool) else value


def _norm_map(raw):
    if not isinstance(raw, dict):
        return {}
    return {str(k): _norm_scalar(v) for k, v in raw.items()}


def param_hash(cfg):
    """Short, stable hash over the parameter set (params + defines + style)."""
    blob = json.dumps(
        {
            "params": _norm_map(cfg.get("params") or {}),
            "defines": _norm_map(cfg.get("defines") or {}),
            "param_style": cfg.get("param_style", "define"),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:8]


def _ident(value, what):
    if not isinstance(value, str) or not SV_IDENT_RE.match(value):
        raise ConfigError(f"{what} must be a SystemVerilog identifier, got: {value!r}")
    return value


def _scalar_map(raw, what):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"'{what}' must be a mapping of NAME: value")
    out = {}
    for key, value in raw.items():
        _ident(str(key), f"{what} key")
        value = _norm_scalar(value)
        if not isinstance(value, (int, float, str)):
            raise ConfigError(
                f"{what}['{key}'] must be a scalar, got {type(value).__name__}")
        out[str(key)] = value
    return out


def validate(cfg):
    """Validate and normalize a merged config; returns a new dict."""
    if not isinstance(cfg, dict):
        raise ConfigError("config must be a YAML mapping")
    out = {}
    out["ip_name"] = _ident(cfg.get("ip_name"), "ip_name")

    dut = cfg.get("dut") or {}
    if not isinstance(dut, dict):
        raise ConfigError("'dut' must be a mapping")
    module = dut.get("module") or f"{out['ip_name']}_top"
    out["dut"] = {
        "module": _ident(module, "dut.module"),
        "rtl_filelist": dut.get("rtl_filelist"),
    }

    config_name = str(cfg.get("config_name", "default"))
    if not CONFIG_NAME_RE.match(config_name):
        raise ConfigError(f"config_name must match [A-Za-z0-9_]+, got: {config_name!r}")
    out["config_name"] = config_name

    style = cfg.get("param_style", "define")
    if style not in ("define", "defparam"):
        raise ConfigError(f"param_style must be 'define' or 'defparam', got: {style!r}")
    out["param_style"] = style

    # DV methodology scaffolding (docs/CLAUDE.md + vplan, the dv/ tree with the
    # chkq negative-test kit, regression lists, exclusion file, status sidecars)
    # — on by default so a generated env drops straight into the Copilot DV
    # pack; set 'dv_scaffold: false' for a lean standalone env.
    scaffold = cfg.get("dv_scaffold", True)
    if isinstance(scaffold, str):
        scaffold = {"true": True, "false": False}.get(scaffold.strip().lower(), scaffold)
    if not isinstance(scaffold, bool):
        raise ConfigError(f"dv_scaffold must be a boolean, got: {cfg.get('dv_scaffold')!r}")
    out["dv_scaffold"] = scaffold

    out["params"] = _scalar_map(cfg.get("params"), "params")
    out["defines"] = _scalar_map(cfg.get("defines"), "defines")

    seen = set()
    agents = []
    for i, raw in enumerate(cfg.get("agents") or []):
        if not isinstance(raw, dict):
            raise ConfigError(f"agents[{i}] must be a mapping (name/mode)")
        name = _ident(raw.get("name"), f"agents[{i}].name")
        mode = raw.get("mode", "active")
        if mode not in ("active", "passive"):
            raise ConfigError(
                f"agents[{i}].mode must be 'active' or 'passive', got: {mode!r}")
        if name in seen:
            raise ConfigError(f"duplicate interface name: {name}")
        seen.add(name)
        agents.append({"name": name, "mode": mode})
    out["agents"] = agents

    vips = []
    for i, raw in enumerate(cfg.get("vips") or []):
        if not isinstance(raw, dict):
            raise ConfigError(f"vips[{i}] must be a mapping (protocol/name/role)")
        protocol = raw.get("protocol")
        if protocol not in PROTOCOLS:
            raise ConfigError(
                f"vips[{i}].protocol must be one of {sorted(PROTOCOLS)}, got: {protocol!r}")
        proto = PROTOCOLS[protocol]
        name = _ident(raw.get("name"), f"vips[{i}].name")
        if name in seen:
            raise ConfigError(f"duplicate interface name: {name}")
        seen.add(name)
        role = raw.get("role", proto["default_role"])
        role = proto["role_aliases"].get(role, role)
        if role not in proto["roles"]:
            raise ConfigError(
                f"vips[{i}].role for '{protocol}' must be one of {proto['roles']},"
                f" got: {raw.get('role')!r}")
        entry = {"protocol": protocol, "name": name, "role": role}
        for knob in proto["knobs"]:
            if knob["name"] in raw:
                entry[knob["name"]] = _norm_scalar(raw[knob["name"]])
        vips.append(entry)
    out["vips"] = vips

    return out
