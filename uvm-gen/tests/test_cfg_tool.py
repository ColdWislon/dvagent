"""sim/scripts/cfg_tool.py (copied verbatim into every env): makevars,
collect, matrix - and its hash implementation pinned to the generator's."""

import importlib.util
import os
from pathlib import Path

import pytest
import yaml

from uvm_gen import config as gen_config

TEMPLATE_CFG_TOOL = (
    Path(__file__).resolve().parents[1] / "uvm_gen/templates/sim/cfg_tool.py"
)


@pytest.fixture
def cfg_tool():
    spec = importlib.util.spec_from_file_location("cfg_tool", TEMPLATE_CFG_TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def in_sim_dir(generated_env, monkeypatch):
    sim = generated_env / "sim"
    monkeypatch.chdir(sim)
    return sim


PASS_LOG = """\
xcelium> run
UVM_INFO env/my_ip_env_cfg.sv(100) @ 0: uvm_test_top [UVM_GEN_CFG] ------------
UVM_INFO env/my_ip_env_cfg.sv(101) @ 0: uvm_test_top [UVM_GEN_CFG] ip          : my_ip
UVM_INFO env/my_ip_env_cfg.sv(102) @ 0: uvm_test_top [UVM_GEN_CFG] config_name : small
UVM_INFO env/my_ip_env_cfg.sv(103) @ 0: uvm_test_top [UVM_GEN_CFG] param_hash  : 0xdeadbeef
UVM_INFO env/my_ip_env_cfg.sv(104) @ 0: uvm_test_top [UVM_GEN_CFG] param DATA_WIDTH = 32
UVM_INFO env/my_ip_env_cfg.sv(105) @ 0: uvm_test_top [UVM_GEN_CFG] param NAME = fast
UVM_INFO tests/my_ip_base_test.sv(60) @ 500ns: uvm_test_top [RESULT] ** UVM TEST PASSED **

--- UVM Report Summary ---
UVM_INFO :   42
UVM_WARNING :    0
UVM_ERROR :    0
UVM_FATAL :    0
Simulation complete via $finish(1) at time 700 NS + 0
"""

FAIL_LOG = PASS_LOG.replace("UVM_ERROR :    0", "UVM_ERROR :    3")


def test_hash_matches_generator_implementation(cfg_tool):
    for canon in ("", "A=1", "A=1,B=fast,C=-3"):
        assert cfg_tool.fnv1a32(canon) == gen_config.fnv1a32(canon)


def test_canonical_and_hash_match_on_real_config(cfg_tool, examples_copy):
    path = str(examples_copy / "my_ip_small.yaml")
    tool_params = cfg_tool.normalize_params(cfg_tool.load_cfg(path))
    gen_cfg, _ = gen_config.load_config(path)
    assert cfg_tool.canonical_params(tool_params) == gen_config.canonical_params(
        gen_cfg["params"]
    )
    assert cfg_tool.param_hash_hex(tool_params) == gen_config.param_hash_hex(
        gen_cfg["params"]
    )


def test_makevars_output(cfg_tool, in_sim_dir, capsys):
    # CFG given relative to the *_verif root: resolved via the .. fallback
    rc = cfg_tool.main(["makevars", "cfg/my_ip.yaml", "--out", ".mk"])
    assert rc == 0
    text = Path(".mk").read_text()
    vars = dict(
        line.split(" := ", 1)
        for line in text.splitlines()
        if " := " in line
    )
    assert vars["CONFIG_NAME"] == "default"
    assert "+define+DATA_WIDTH=32" in vars["PARAM_XRUN_ARGS"]
    assert "+define+NUM_CHANNELS=2" in vars["PARAM_XRUN_ARGS"]
    assert "-defparam tb_top.dut.FIFO_DEPTH=8" in vars["PARAM_XRUN_ARGS"]
    assert vars["PARAM_PLUSARGS"] == (
        "+PARAM_DATA_WIDTH=32 +PARAM_FIFO_DEPTH=8 +PARAM_NUM_CHANNELS=2"
    )
    assert vars["VIP_PROTOCOLS"] == "apb i3c"
    assert vars["CONFIG_HASH"].startswith("0x")


def test_makevars_bad_config_fails(cfg_tool, in_sim_dir):
    rc = cfg_tool.main(["makevars", "nonexistent.yaml", "--out", ".mk"])
    assert rc == 2


def test_collect_pass_and_fail_records(cfg_tool, in_sim_dir, capsys):
    Path("logs").mkdir(exist_ok=True)
    Path("logs/pass.log").write_text(PASS_LOG)
    Path("logs/fail.log").write_text(FAIL_LOG)
    matrix = "../verif_matrix.yaml"

    rc = cfg_tool.main([
        "collect", "../cfg/my_ip.yaml", "--log", "logs/pass.log",
        "--test", "my_ip_smoke_test", "--seed", "7", "--matrix", matrix,
    ])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out

    rc = cfg_tool.main([
        "collect", "../cfg/my_ip.yaml", "--log", "logs/fail.log",
        "--test", "my_ip_smoke_test", "--seed", "8", "--matrix", matrix,
    ])
    assert rc == 1

    # missing log -> fail, but still recorded
    rc = cfg_tool.main([
        "collect", "../cfg/my_ip.yaml", "--log", "logs/gone.log",
        "--test", "my_ip_smoke_test", "--seed", "9", "--matrix", matrix,
    ])
    assert rc == 1

    records = yaml.safe_load(Path(matrix).read_text())
    assert len(records) == 3
    first, second, third = records
    # banner values win over the YAML (they are what the sim actually used)
    assert first["config_name"] == "small"
    assert first["param_hash"] == "0xdeadbeef"
    assert first["result"] == "pass"
    assert first["seed"] == 7
    assert first["uvm_errors"] == 0
    assert first["params"] == {"DATA_WIDTH": 32, "NAME": "fast"}
    assert first["test"] == "my_ip_smoke_test"
    assert first["date"] and first["git_rev"]
    assert second["result"] == "fail"
    assert second["fail_reason"] == "uvm_errors"
    assert second["uvm_errors"] == 3
    assert third["result"] == "fail"
    assert third["fail_reason"] == "no_log"
    # header comments survive appends
    assert Path(matrix).read_text().startswith("# verif_matrix.yaml")


def test_matrix_summary_table(cfg_tool, in_sim_dir, capsys):
    Path("logs").mkdir(exist_ok=True)
    Path("logs/pass.log").write_text(PASS_LOG)
    big = PASS_LOG.replace("config_name : small", "config_name : large") \
                  .replace("0xdeadbeef", "0xcafef00d")
    Path("logs/pass_large.log").write_text(big)
    matrix = "../verif_matrix.yaml"
    for log, seed in (("logs/pass.log", 1), ("logs/pass.log", 2),
                      ("logs/pass_large.log", 3)):
        cfg_tool.main([
            "collect", "../cfg/my_ip.yaml", "--log", log,
            "--test", "my_ip_smoke_test", "--seed", str(seed),
            "--matrix", matrix,
        ])
    capsys.readouterr()

    rc = cfg_tool.main(["matrix", matrix])
    assert rc == 0
    out = capsys.readouterr().out
    assert "small" in out and "large" in out
    assert "0xdeadbeef" in out and "0xcafef00d" in out
    assert "my_ip_smoke_test" in out
    # two distinct config entries (acceptance: two YAMLs -> two entries)
    lines = [l for l in out.splitlines() if "0x" in l]
    assert len(lines) == 2


def test_matrix_empty_and_missing(cfg_tool, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cfg_tool.main(["matrix", "does_not_exist.yaml"])
    assert rc == 0
    assert "no verification records" in capsys.readouterr().out


def test_seed_sniffed_from_log_when_random(cfg_tool, in_sim_dir):
    Path("logs").mkdir(exist_ok=True)
    log = PASS_LOG + "\nSVSEED: 123456\n"
    Path("logs/rand.log").write_text(log)
    rc = cfg_tool.main([
        "collect", "../cfg/my_ip.yaml", "--log", "logs/rand.log",
        "--test", "t", "--seed", "random", "--matrix", "../verif_matrix.yaml",
    ])
    assert rc == 0
    records = yaml.safe_load(Path("../verif_matrix.yaml").read_text())
    assert records[-1]["seed"] == 123456
