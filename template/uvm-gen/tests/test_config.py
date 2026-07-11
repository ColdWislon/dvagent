"""Config loading: extends deep-merge, param hashing, validation."""

import pytest

from uvmgen.config import ConfigError, deep_merge, load_config, param_hash, validate


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


BASE_YAML = """\
ip_name: my_ip
dut:
  module: my_ip_top
  rtl_filelist: ../rtl/dut.f
params:
  DATA_W: 32
  FIFO_DEPTH: 16
agents:
  - name: ctrl
    mode: active
vips:
  - protocol: apb
    name: apb_cfg
    role: master
"""


def test_deep_merge_child_wins_and_recurses():
    base = {"a": 1, "d": {"x": 1, "y": 2}, "l": [1, 2]}
    child = {"a": 9, "d": {"y": 7, "z": 3}, "l": [5]}
    merged = deep_merge(base, child)
    assert merged == {"a": 9, "d": {"x": 1, "y": 7, "z": 3}, "l": [5]}
    # inputs untouched
    assert base["d"] == {"x": 1, "y": 2}


def test_extends_chain_and_merge(tmp_path):
    write(tmp_path, "base.yaml", BASE_YAML)
    child = write(tmp_path, "small.yaml",
                  "extends: base.yaml\nconfig_name: small\nparams:\n  DATA_W: 16\n")
    merged, chain = load_config(child)
    assert merged["config_name"] == "small"
    assert merged["params"] == {"DATA_W": 16, "FIFO_DEPTH": 16}   # deep-merged
    assert merged["agents"][0]["name"] == "ctrl"                  # inherited
    assert [p.name for p in chain] == ["base.yaml", "small.yaml"]


def test_extends_cycle_detected(tmp_path):
    write(tmp_path, "a.yaml", "extends: b.yaml\nip_name: x\n")
    write(tmp_path, "b.yaml", "extends: a.yaml\n")
    with pytest.raises(ConfigError, match="circular"):
        load_config(tmp_path / "a.yaml")


def test_missing_file_is_config_error(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_param_hash_stable_and_value_sensitive():
    a = {"params": {"DATA_W": 32, "FIFO_DEPTH": 16}}
    b = {"params": {"FIFO_DEPTH": 16, "DATA_W": 32}}   # different key order
    c = {"params": {"DATA_W": 64, "FIFO_DEPTH": 16}}
    assert param_hash(a) == param_hash(b)
    assert param_hash(a) != param_hash(c)
    assert len(param_hash(a)) == 8


def test_validate_normalizes(tmp_path):
    write(tmp_path, "base.yaml", BASE_YAML)
    merged, _ = load_config(tmp_path / "base.yaml")
    cfg = validate(merged)
    assert cfg["ip_name"] == "my_ip"
    assert cfg["config_name"] == "default"
    assert cfg["param_style"] == "define"
    assert cfg["agents"] == [{"name": "ctrl", "mode": "active"}]
    assert cfg["vips"][0]["role"] == "master"


def test_validate_rejects_bad_input():
    with pytest.raises(ConfigError, match="ip_name"):
        validate({"ip_name": "1bad"})
    with pytest.raises(ConfigError, match="mode"):
        validate({"ip_name": "x", "agents": [{"name": "a", "mode": "weird"}]})
    with pytest.raises(ConfigError, match="protocol"):
        validate({"ip_name": "x", "vips": [{"protocol": "pcie", "name": "p"}]})
    with pytest.raises(ConfigError, match="role"):
        validate({"ip_name": "x",
                  "vips": [{"protocol": "apb", "name": "p", "role": "queen"}]})
    with pytest.raises(ConfigError, match="duplicate"):
        validate({"ip_name": "x",
                  "agents": [{"name": "a"}, {"name": "a"}]})
    with pytest.raises(ConfigError, match="param_style"):
        validate({"ip_name": "x", "param_style": "plusarg"})


def test_i3c_role_aliases_and_defaults():
    cfg = validate({"ip_name": "x",
                    "vips": [{"protocol": "i3c", "name": "bus", "role": "master"}]})
    assert cfg["vips"][0]["role"] == "controller"   # alias normalized
    cfg = validate({"ip_name": "x",
                    "vips": [{"protocol": "i3c", "name": "bus"}]})
    assert cfg["vips"][0]["role"] == "controller"   # sensible default


def test_bools_normalized_to_int():
    cfg = validate({"ip_name": "x", "params": {"EN": True},
                    "defines": {"OFF": False}})
    assert cfg["params"]["EN"] == 1
    assert cfg["defines"]["OFF"] == 0
