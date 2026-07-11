"""Generated sim/scripts/ behave correctly (run via subprocess like make does)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from uvmgen.config import load_config, param_hash, validate
from uvmgen.generate import generate

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

PASS_LOG = """\
UVM_INFO @ 0: reporter [RNTST] Running test my_ip_smoke_test...
SVSEED default: 1
--- UVM Report Summary ---
** Report counts by severity
UVM_INFO :   57
UVM_WARNING :    0
UVM_ERROR :    0
UVM_FATAL :    0
Simulation complete via $finish(1)
"""

FAIL_LOG = """\
UVM_ERROR tb.sv(10) @ 55: uvm_test_top [SB] mismatch
--- UVM Report Summary ---
UVM_INFO :   12
UVM_WARNING :    1
UVM_ERROR :    2
UVM_FATAL :    0
"""


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    """One generated my_ip env shared by the script tests."""
    tmp = tmp_path_factory.mktemp("scripts")
    cfg_dir = tmp / "configs"
    shutil.copytree(EXAMPLES, cfg_dir)
    for name in ("my_ip.yaml", "my_ip_small.yaml"):
        merged, chain = load_config(cfg_dir / name)
        generate(validate(merged), chain, tmp)
    return tmp / "my_ip_verif"


def run_script(env, script, *args):
    proc = subprocess.run(
        [sys.executable, str(env / "sim/scripts" / script), *args],
        capture_output=True, text=True, cwd=env)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_cfg2args_xrun_args_default_style(env):
    out = run_script(env, "cfg2args.py", "cfg/my_ip.yaml", "--xrun-args")
    assert "+define+DATA_W=32" in out
    assert "+define+FIFO_DEPTH=16" in out
    assert "+MY_IP_CFG_NAME=default" in out
    assert "+MY_IP_PARAM=DATA_W=32" in out
    assert "-defparam" not in out


def test_cfg2args_defparam_style(env, tmp_path):
    cfg = tmp_path / "dp.yaml"
    cfg.write_text(
        "ip_name: my_ip\nconfig_name: dp\nparam_style: defparam\n"
        "params:\n  DATA_W: 8\n")
    out = run_script(env, "cfg2args.py", str(cfg), "--xrun-args",
                     "--tb-top", "my_ip_tb_top")
    assert "-defparam my_ip_tb_top.dut.DATA_W=8" in out
    assert "+define+DATA_W" not in out


def test_cfg2args_hash_matches_generator(env):
    merged, _ = load_config(env / "cfg/my_ip_small.yaml")
    expected = param_hash(validate(merged))
    assert run_script(env, "cfg2args.py", "cfg/my_ip_small.yaml", "--param-hash") == expected


def test_cfg2args_extends_resolution(env):
    # the copied small config extends the sibling base copy
    assert run_script(env, "cfg2args.py", "cfg/my_ip_small.yaml", "--config-name") == "small"
    out = run_script(env, "cfg2args.py", "cfg/my_ip_small.yaml", "--params-json")
    assert json.loads(out)["params"] == {"DATA_W": 16, "FIFO_DEPTH": 8}


def test_cfg2args_vip_queries_and_vsif_names(env):
    assert run_script(env, "cfg2args.py", "cfg/my_ip.yaml", "--has-vips") == "1"
    assert run_script(env, "cfg2args.py", "cfg/my_ip.yaml", "--vip-protocols") == "apb"
    assert run_script(env, "cfg2args.py", "cfg/my_ip.yaml", "--vsif-name") == "my_ip.vsif"
    assert run_script(env, "cfg2args.py", "cfg/my_ip_small.yaml", "--vsif-name") == "my_ip_small.vsif"


def test_two_configs_two_matrix_entries(env, tmp_path):
    """Acceptance proxy: smoke under two config YAMLs -> two distinct records."""
    pass_log = tmp_path / "pass.log"
    pass_log.write_text(PASS_LOG)
    fail_log = tmp_path / "fail.log"
    fail_log.write_text(FAIL_LOG)
    matrix = tmp_path / "verif_matrix.yaml"

    run_script(env, "record_result.py", "--matrix", str(matrix),
               "--config", "cfg/my_ip.yaml", "--test", "my_ip_smoke_test",
               "--seed", "1", "--log", str(pass_log), "--xrun-status", "0")
    run_script(env, "record_result.py", "--matrix", str(matrix),
               "--config", "cfg/my_ip_small.yaml", "--test", "my_ip_smoke_test",
               "--seed", "2", "--log", str(pass_log), "--xrun-status", "0")
    run_script(env, "record_result.py", "--matrix", str(matrix),
               "--config", "cfg/my_ip_small.yaml", "--test", "my_ip_smoke_test",
               "--seed", "3", "--log", str(fail_log), "--xrun-status", "0")

    data = yaml.safe_load(matrix.read_text())
    runs = data["runs"]
    assert len(runs) == 3
    assert runs[0]["config_name"] == "default" and runs[0]["status"] == "pass"
    assert runs[1]["config_name"] == "small" and runs[1]["status"] == "pass"
    assert runs[2]["status"] == "fail" and runs[2]["uvm_errors"] == 2
    assert runs[0]["param_hash"] != runs[1]["param_hash"]   # distinct signatures
    assert runs[0]["params"] == {"DATA_W": 32, "FIFO_DEPTH": 16}
    assert runs[1]["params"] == {"DATA_W": 16, "FIFO_DEPTH": 8}

    report = run_script(env, "matrix_report.py", str(matrix))
    assert "default" in report and "small" in report
    assert "CLEAN" in report and "FAILING" in report

    machine = run_script(env, "matrix_report.py", str(matrix), "--yaml")
    aggregate = yaml.safe_load(machine)["configs"]
    assert {g["config_name"] for g in aggregate} == {"default", "small"}


def test_record_result_xrun_crash_is_fail(env, tmp_path):
    log = tmp_path / "crash.log"
    log.write_text("xmelab: *E, something exploded\n")   # no UVM summary
    matrix = tmp_path / "m.yaml"
    run_script(env, "record_result.py", "--matrix", str(matrix),
               "--config", "cfg/my_ip.yaml", "--test", "t", "--seed", "1",
               "--log", str(log), "--xrun-status", "1")
    runs = yaml.safe_load(matrix.read_text())["runs"]
    assert runs[0]["status"] == "fail"


def test_matrix_report_empty_ok(env, tmp_path):
    out = run_script(env, "matrix_report.py", str(tmp_path / "missing.yaml"))
    assert "no" in out.lower()
