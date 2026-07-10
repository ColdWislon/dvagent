"""Configuration loading, 'extends' merging, validation, and param hashing.

The canonical parameter string and its FNV-1a hash implemented here MUST stay
in sync with two other implementations:
  * ``<ip>_env_cfg::params_canonical()`` / ``param_hash()`` (generated SV), and
  * ``sim/scripts/cfg_tool.py`` (copied verbatim into every generated env).
A unit test pins the Python implementations against each other.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

PROTOCOLS = ("apb", "ahb", "i3c")
ROLES = {
    "apb": ("master", "slave", "passive"),
    "ahb": ("master", "slave", "passive"),
    "i3c": ("controller", "target", "passive"),
}
# MIPI I3C renamed master/slave to controller/target; accept the legacy terms.
I3C_ROLE_ALIASES = {"master": "controller", "slave": "target"}
DEFAULT_ROLES = {"apb": "master", "ahb": "master", "i3c": "controller"}
PARAM_STYLES = ("define", "defparam", "env")

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CONFIG_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
# Param string values must survive make -> xrun plusargs unquoted and the
# canonical "name=value,..." hash string.
PARAM_STR_RE = re.compile(r"^[A-Za-z0-9_.+\-]+$")

# Instance names that would collide with generated env-level class names
# (e.g. an agent called 'env' would generate '<ip>_env_cfg' twice).
RESERVED_INSTANCE_NAMES = {"env", "vsequencer", "scoreboard", "reg"}


class ConfigError(Exception):
    """Invalid configuration input."""


def fnv1a32(s: str) -> int:
    """FNV-1a 32-bit hash; matches ``<ip>_env_cfg::param_hash()`` in SV."""
    h = 0x811C9DC5
    for byte in s.encode("utf-8"):
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return h


def deep_merge(base, override):
    """Mappings merge recursively (override wins); everything else replaces."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base[key], value) if key in base else value
        return merged
    return override


def _read_yaml(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from None
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a YAML mapping")
    return data


def load_raw_config(path) -> tuple[dict, list[Path]]:
    """Resolve the ``extends`` chain and deep-merge it (config file wins).

    Returns ``(merged, chain)`` where ``chain`` lists the resolved file paths
    from the deepest base to the given file.
    """
    chain: list[Path] = []
    seen: set[Path] = set()

    def _load(p: Path) -> dict:
        p = p.resolve()
        if p in seen:
            raise ConfigError(f"circular 'extends' chain at {p}")
        seen.add(p)
        data = _read_yaml(p)
        extends = data.pop("extends", None)
        merged: dict = {}
        if extends is not None:
            if not isinstance(extends, str):
                raise ConfigError(f"{p}: 'extends' must be a path string")
            merged = _load((p.parent / extends).resolve())
        chain.append(p)
        return deep_merge(merged, data)

    merged = _load(Path(path))
    return merged, chain


def _require_ident(value, what: str, source: str) -> str:
    if not isinstance(value, str) or not IDENT_RE.match(value):
        raise ConfigError(
            f"{source}: {what} must be a SystemVerilog identifier "
            f"(got {value!r})"
        )
    return value


def _normalize_param(name, spec, source: str) -> dict:
    _require_ident(name, f"param name {name!r}", source)
    style, path = "define", None
    value = spec
    if isinstance(spec, dict):
        unknown = set(spec) - {"value", "style", "path"}
        if unknown:
            raise ConfigError(
                f"{source}: param '{name}': unknown key(s) {sorted(unknown)} "
                "(allowed: value, style, path)"
            )
        if "value" not in spec:
            raise ConfigError(f"{source}: param '{name}': missing 'value'")
        value = spec["value"]
        style = spec.get("style", "define")
        path = spec.get("path")
        if style not in PARAM_STYLES:
            raise ConfigError(
                f"{source}: param '{name}': style must be one of "
                f"{'/'.join(PARAM_STYLES)} (got {style!r})"
            )
        if path is not None and not isinstance(path, str):
            raise ConfigError(f"{source}: param '{name}': 'path' must be a string")

    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        if not -(2**31) <= value < 2**31:
            raise ConfigError(
                f"{source}: param '{name}': integer value out of 32-bit range "
                "(pass wide literals as string params and handle them in RTL)"
            )
    elif isinstance(value, str):
        if not PARAM_STR_RE.match(value):
            raise ConfigError(
                f"{source}: param '{name}': string values may only contain "
                "[A-Za-z0-9_.+-] (they travel through plusargs and the "
                f"config-signature hash), got {value!r}"
            )
        if style == "defparam":
            raise ConfigError(
                f"{source}: param '{name}': style 'defparam' requires an "
                "integer value"
            )
    else:
        raise ConfigError(
            f"{source}: param '{name}': value must be int/bool/string "
            f"(got {type(value).__name__})"
        )
    return {"name": name, "value": value, "style": style, "path": path}


def normalize_config(raw: dict, source: str = "<config>") -> dict:
    """Validate the merged raw config and return the normalized form."""
    warnings: list[str] = []
    known = {"ip_name", "config_name", "dut", "agents", "vips", "params", "copilot"}
    for key in raw:
        if key not in known:
            warnings.append(f"unknown top-level key '{key}' (ignored)")

    # Copilot DV agent pack staging: unset -> auto (include when the pack is
    # discoverable), true -> required, false -> off, string -> pack root path.
    copilot = raw.get("copilot")
    if copilot is not None and not isinstance(copilot, (bool, str)):
        raise ConfigError(
            f"{source}: 'copilot' must be true/false or a pack path "
            f"(got {type(copilot).__name__})"
        )

    ip = raw.get("ip_name")
    if ip is None:
        raise ConfigError(f"{source}: 'ip_name' is required")
    ip = _require_ident(ip, "'ip_name'", source)

    config_name = raw.get("config_name", "default")
    if not isinstance(config_name, str) or not CONFIG_NAME_RE.match(config_name):
        raise ConfigError(
            f"{source}: 'config_name' must match [A-Za-z0-9_]+ "
            f"(got {config_name!r})"
        )

    dut = raw.get("dut") or {}
    if not isinstance(dut, dict):
        raise ConfigError(f"{source}: 'dut' must be a mapping")
    module = _require_ident(dut.get("module", ip), "'dut.module'", source)
    if module == "tb_top":
        raise ConfigError(f"{source}: 'dut.module' may not be 'tb_top'")
    rtl_filelist = dut.get("rtl_filelist")
    if rtl_filelist is not None and not isinstance(rtl_filelist, str):
        raise ConfigError(f"{source}: 'dut.rtl_filelist' must be a string path")

    agents = []
    raw_agents = raw.get("agents") or []
    if not isinstance(raw_agents, list):
        raise ConfigError(f"{source}: 'agents' must be a list")
    for entry in raw_agents:
        if not isinstance(entry, dict):
            raise ConfigError(f"{source}: each agent must be a mapping")
        name = _require_ident(entry.get("name"), "agent 'name'", source)
        mode = entry.get("mode", "active")
        if mode not in ("active", "passive"):
            raise ConfigError(
                f"{source}: agent '{name}': mode must be active|passive "
                f"(got {mode!r})"
            )
        unknown = set(entry) - {"name", "mode"}
        if unknown:
            warnings.append(f"agent '{name}': unknown key(s) {sorted(unknown)} (ignored)")
        agents.append({"name": name, "mode": mode})

    vips = []
    raw_vips = raw.get("vips") or []
    if not isinstance(raw_vips, list):
        raise ConfigError(f"{source}: 'vips' must be a list")
    for entry in raw_vips:
        if not isinstance(entry, dict):
            raise ConfigError(f"{source}: each vip must be a mapping")
        protocol = entry.get("protocol")
        if protocol not in PROTOCOLS:
            raise ConfigError(
                f"{source}: vip protocol must be one of {'/'.join(PROTOCOLS)} "
                f"(got {protocol!r})"
            )
        name = _require_ident(entry.get("name"), f"vip ({protocol}) 'name'", source)
        role = entry.get("role", DEFAULT_ROLES[protocol])
        if protocol == "i3c":
            role = I3C_ROLE_ALIASES.get(role, role)
        if role not in ROLES[protocol]:
            raise ConfigError(
                f"{source}: vip '{name}': role for {protocol} must be one of "
                f"{'/'.join(ROLES[protocol])} (got {entry.get('role')!r})"
            )
        vip = {"protocol": protocol, "name": name, "role": role}
        if protocol == "i3c":
            ibi = entry.get("ibi_enable", True)
            if not isinstance(ibi, bool):
                raise ConfigError(f"{source}: vip '{name}': 'ibi_enable' must be a bool")
            vip["ibi_enable"] = ibi
            known_vip = {"protocol", "name", "role", "ibi_enable"}
        else:
            known_vip = {"protocol", "name", "role"}
        unknown = set(entry) - known_vip
        if unknown:
            warnings.append(f"vip '{name}': unknown key(s) {sorted(unknown)} (ignored)")
        vips.append(vip)

    names = [a["name"] for a in agents] + [v["name"] for v in vips]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise ConfigError(
            f"{source}: agent/vip instance names must be unique "
            f"(duplicated: {sorted(dupes)})"
        )
    reserved = set(names) & RESERVED_INSTANCE_NAMES
    if reserved:
        raise ConfigError(
            f"{source}: instance name(s) {sorted(reserved)} are reserved "
            "(they collide with generated env-level class names)"
        )

    raw_params = raw.get("params") or {}
    if not isinstance(raw_params, dict):
        raise ConfigError(f"{source}: 'params' must be a mapping")
    params = sorted(
        (_normalize_param(n, s, source) for n, s in raw_params.items()),
        key=lambda p: p["name"],
    )

    return {
        "ip_name": ip,
        "config_name": config_name,
        "dut": {"module": module, "rtl_filelist": rtl_filelist},
        "agents": agents,
        "vips": vips,
        "params": params,
        "copilot": copilot,
        "warnings": warnings,
    }


def canonical_params(params: list[dict]) -> str:
    """Canonical "name=value" list, sorted by name (params are pre-sorted)."""
    return ",".join(f"{p['name']}={p['value']}" for p in params)


def param_hash_hex(params: list[dict]) -> str:
    return f"0x{fnv1a32(canonical_params(params)):08x}"


def load_config(path) -> tuple[dict, list[Path]]:
    """Load + merge + validate; returns (normalized_config, extends_chain)."""
    raw, chain = load_raw_config(path)
    cfg = normalize_config(raw, source=str(path))
    basenames = [p.name for p in chain]
    if len(set(basenames)) != len(basenames):
        raise ConfigError(
            "config files in an 'extends' chain must have distinct file names "
            f"(they are all copied into cfg/): {basenames}"
        )
    return cfg, chain
