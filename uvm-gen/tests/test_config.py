import pytest

from uvm_gen.config import (
    ConfigError,
    canonical_params,
    deep_merge,
    fnv1a32,
    load_config,
    load_raw_config,
    normalize_config,
    param_hash_hex,
)


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# hashing
# ---------------------------------------------------------------------------

def test_fnv1a32_known_vectors():
    assert fnv1a32("") == 0x811C9DC5          # offset basis
    assert fnv1a32("a") == 0xE40C292C         # FNV-1a reference vector
    assert fnv1a32("foobar") == 0xBF9CF968    # FNV-1a reference vector


def test_canonical_params_and_hash_are_sorted_and_stable():
    cfg = normalize_config(
        {"ip_name": "x", "params": {"B": 2, "A": 1, "C": "fast"}}
    )
    assert canonical_params(cfg["params"]) == "A=1,B=2,C=fast"
    assert param_hash_hex(cfg["params"]) == f"0x{fnv1a32('A=1,B=2,C=fast'):08x}"


# ---------------------------------------------------------------------------
# deep merge / extends
# ---------------------------------------------------------------------------

def test_deep_merge_semantics():
    base = {"a": {"x": 1, "y": 2}, "l": [1, 2], "s": "base", "keep": 7}
    over = {"a": {"y": 3, "z": 4}, "l": [9], "s": "child"}
    merged = deep_merge(base, over)
    assert merged == {
        "a": {"x": 1, "y": 3, "z": 4},
        "l": [9],          # lists replace wholesale
        "s": "child",      # scalars replace
        "keep": 7,
    }


def test_extends_chain_merges_child_wins(tmp_path):
    write(tmp_path / "grand.yaml", "ip_name: my_ip\nparams: {A: 1, B: 1}\n")
    write(tmp_path / "base.yaml", "extends: grand.yaml\nparams: {B: 2, C: 2}\n")
    child = write(
        tmp_path / "child.yaml",
        "extends: base.yaml\nconfig_name: small\nparams: {C: 3}\n",
    )
    raw, chain = load_raw_config(child)
    assert [p.name for p in chain] == ["grand.yaml", "base.yaml", "child.yaml"]
    assert raw["params"] == {"A": 1, "B": 2, "C": 3}
    assert raw["config_name"] == "small"
    assert "extends" not in raw


def test_extends_cycle_is_an_error(tmp_path):
    write(tmp_path / "a.yaml", "extends: b.yaml\nip_name: x\n")
    write(tmp_path / "b.yaml", "extends: a.yaml\n")
    with pytest.raises(ConfigError, match="circular"):
        load_raw_config(tmp_path / "a.yaml")


def test_extends_missing_base_is_an_error(tmp_path):
    cfg = write(tmp_path / "a.yaml", "extends: nope.yaml\nip_name: x\n")
    with pytest.raises(ConfigError, match="not found"):
        load_raw_config(cfg)


def test_extends_duplicate_basenames_rejected(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    write(sub / "my.yaml", "ip_name: x\n")
    cfg = write(tmp_path / "my.yaml", "extends: sub/my.yaml\n")
    with pytest.raises(ConfigError, match="distinct file names"):
        load_config(cfg)


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def test_ip_name_required_and_identifier():
    with pytest.raises(ConfigError, match="ip_name"):
        normalize_config({})
    with pytest.raises(ConfigError, match="identifier"):
        normalize_config({"ip_name": "my ip"})


def test_agent_validation():
    with pytest.raises(ConfigError, match="active|passive"):
        normalize_config({"ip_name": "x", "agents": [{"name": "a", "mode": "monitor"}]})
    with pytest.raises(ConfigError, match="unique"):
        normalize_config({"ip_name": "x", "agents": [{"name": "a"}, {"name": "a"}]})
    with pytest.raises(ConfigError, match="reserved"):
        normalize_config({"ip_name": "x", "agents": [{"name": "env"}]})
    cfg = normalize_config({"ip_name": "x", "agents": [{"name": "a"}]})
    assert cfg["agents"] == [{"name": "a", "mode": "active"}]


def test_vip_validation_and_roles():
    with pytest.raises(ConfigError, match="apb/ahb/i3c"):
        normalize_config({"ip_name": "x", "vips": [{"protocol": "axi", "name": "v"}]})
    with pytest.raises(ConfigError, match="role"):
        normalize_config(
            {"ip_name": "x", "vips": [{"protocol": "apb", "name": "v", "role": "controller"}]}
        )
    # i3c accepts legacy master/slave and maps to controller/target
    cfg = normalize_config(
        {"ip_name": "x", "vips": [{"protocol": "i3c", "name": "v", "role": "master"}]}
    )
    assert cfg["vips"][0]["role"] == "controller"
    assert cfg["vips"][0]["ibi_enable"] is True
    # defaults
    cfg = normalize_config({"ip_name": "x", "vips": [{"protocol": "ahb", "name": "v"}]})
    assert cfg["vips"][0]["role"] == "master"
    # agent/vip name collision
    with pytest.raises(ConfigError, match="unique"):
        normalize_config(
            {
                "ip_name": "x",
                "agents": [{"name": "v"}],
                "vips": [{"protocol": "apb", "name": "v"}],
            }
        )


def test_param_validation():
    cfg = normalize_config(
        {
            "ip_name": "x",
            "params": {
                "B_BOOL": True,
                "A_INT": 5,
                "C_STR": "fast",
                "D_DP": {"value": 4, "style": "defparam"},
            },
        }
    )
    names = [p["name"] for p in cfg["params"]]
    assert names == sorted(names)
    by_name = {p["name"]: p for p in cfg["params"]}
    assert by_name["B_BOOL"]["value"] == 1          # bools become ints
    assert by_name["D_DP"]["style"] == "defparam"

    with pytest.raises(ConfigError, match="defparam"):
        normalize_config(
            {"ip_name": "x", "params": {"P": {"value": "abc", "style": "defparam"}}}
        )
    with pytest.raises(ConfigError, match="style"):
        normalize_config(
            {"ip_name": "x", "params": {"P": {"value": 1, "style": "plusarg"}}}
        )
    with pytest.raises(ConfigError, match="32-bit"):
        normalize_config({"ip_name": "x", "params": {"P": 2**40}})
    with pytest.raises(ConfigError, match="plusargs"):
        normalize_config({"ip_name": "x", "params": {"P": "has space"}})
    with pytest.raises(ConfigError, match="int/bool/string"):
        normalize_config({"ip_name": "x", "params": {"P": 1.5}})


def test_dut_defaults_and_checks():
    cfg = normalize_config({"ip_name": "x"})
    assert cfg["dut"]["module"] == "x"
    assert cfg["dut"]["rtl_filelist"] is None
    assert cfg["config_name"] == "default"
    with pytest.raises(ConfigError, match="tb_top"):
        normalize_config({"ip_name": "x", "dut": {"module": "tb_top"}})


def test_unknown_top_level_keys_warn_not_error():
    cfg = normalize_config({"ip_name": "x", "future_key": 1})
    assert any("future_key" in w for w in cfg["warnings"])
