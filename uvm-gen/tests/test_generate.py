"""Generation: tree contents, re-run policy, incremental adds, vertical reuse."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from uvmgen.cli import main as cli_main
from uvmgen.config import load_config, param_hash, validate
from uvmgen.generate import generate

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture()
def work(tmp_path):
    """Isolated copy of the example configs + an output dir."""
    cfg_dir = tmp_path / "configs"
    shutil.copytree(EXAMPLES, cfg_dir)
    out = tmp_path / "out"
    out.mkdir()
    return cfg_dir, out


def gen(cfg_path, out, **kw):
    merged, chain = load_config(cfg_path)
    cfg = validate(merged)
    return cfg, generate(cfg, chain, out, **kw)


def tree_digest(root):
    digest = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest[str(path.relative_to(root))] = hashlib.md5(path.read_bytes()).hexdigest()
    return digest


def test_generated_tree_layout(work):
    cfg_dir, out = work
    _, report = gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    expected = [
        "cfg/my_ip.yaml",
        "agents/ctrl_agent/my_ip_ctrl_if.sv",
        "agents/ctrl_agent/my_ip_ctrl_seq_item.sv",
        "agents/ctrl_agent/my_ip_ctrl_sequencer.sv",
        "agents/ctrl_agent/my_ip_ctrl_driver.sv",
        "agents/ctrl_agent/my_ip_ctrl_monitor.sv",
        "agents/ctrl_agent/my_ip_ctrl_agent_cfg.sv",
        "agents/ctrl_agent/my_ip_ctrl_agent.sv",
        "agents/ctrl_agent/my_ip_ctrl_base_seq.sv",
        "agents/ctrl_agent/my_ip_ctrl_agent_pkg.sv",
        "agents/stat_agent/my_ip_stat_agent.sv",
        "vip/apb_cfg_vip/my_ip_apb_cfg_vip_cfg.sv",
        "vip/apb_cfg_vip/my_ip_apb_cfg_vip_agent.sv",
        "vip/apb_cfg_vip/my_ip_apb_cfg_vip_pkg.sv",
        "env/my_ip_env.sv",
        "env/my_ip_env_cfg.sv",
        "env/my_ip_env_pkg.sv",
        "env/my_ip_scoreboard.sv",
        "env/my_ip_ctrl_coverage.sv",
        "env/my_ip_stat_coverage.sv",
        "env/my_ip_virtual_sequencer.sv",
        "env/my_ip_reg_block.sv",
        "env/my_ip_reg_adapter.sv",
        "seq_lib/my_ip_base_vseq.sv",
        "seq_lib/my_ip_smoke_vseq.sv",
        "seq_lib/my_ip_seq_lib_pkg.sv",
        "tests/my_ip_base_test.sv",
        "tests/my_ip_smoke_test.sv",
        "tests/my_ip_test_pkg.sv",
        "tb/my_ip_tb_top.sv",
        "tb/my_ip_dut_stub.sv",
        "sim/Makefile",
        "sim/tb.f",
        "sim/vip_apb.f",
        "sim/my_ip.vsif",
        "sim/scripts/cfg2args.py",
        "sim/scripts/record_result.py",
        "sim/scripts/matrix_report.py",
        "sim/scripts/waves.tcl",
        "verif_matrix.yaml",
        "Makefile",
        "README.md",
        ".gitignore",
        ".github/copilot-instructions.md",
        ".github/prompts/connect-dut.prompt.md",
        ".github/prompts/implement-agents.prompt.md",
        ".github/prompts/write-tests.prompt.md",
        ".github/prompts/triage-regression.prompt.md",
        ".github/prompts/coverage-closure.prompt.md",
        ".github/prompts/verif-closure.prompt.md",
    ]
    for rel in expected:
        assert (env / rel).is_file(), f"missing: {rel}"
    assert len(report.created) == 58
    assert not report.skipped and not report.stale


def test_no_unrendered_jinja_and_sane_sv(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    for path in env.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text()
        assert "{{" not in text and "{%" not in text, f"unrendered jinja in {path}"
    for sv in env.rglob("*.sv"):
        text = sv.read_text()
        if "class " in text:
            assert "endclass" in text, sv
        if "package " in text:
            assert "endpackage" in text, sv
        if "interface " in text and "virtual" not in text.split("interface ")[0]:
            pass  # interface files checked below
    for name in ("agents/ctrl_agent/my_ip_ctrl_if.sv",):
        assert "endinterface" in (env / name).read_text()


def test_rerun_never_overwrites_and_reports_stale(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    driver = env / "agents/ctrl_agent/my_ip_ctrl_driver.sv"
    driver.write_text(driver.read_text() + "\n// my precious edit\n")
    before = tree_digest(env)

    _, report = gen(cfg_dir / "my_ip.yaml", out)
    assert tree_digest(env) == before                     # zero bytes changed
    assert not report.created
    assert "agents/ctrl_agent/my_ip_ctrl_driver.sv" in report.stale
    assert "// my precious edit" in driver.read_text()


def test_adding_agent_generates_only_new_files(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    before = tree_digest(env)

    # user adds an agent to the YAML later
    cfg_file = cfg_dir / "my_ip.yaml"
    data = yaml.safe_load(cfg_file.read_text())
    data["agents"].append({"name": "irq", "mode": "passive"})
    cfg_file.write_text(yaml.safe_dump(data, sort_keys=False))

    _, report = gen(cfg_file, out)
    created = set(report.created)
    assert created == {
        "agents/irq_agent/my_ip_irq_if.sv",
        "agents/irq_agent/my_ip_irq_seq_item.sv",
        "agents/irq_agent/my_ip_irq_agent_cfg.sv",
        "agents/irq_agent/my_ip_irq_sequencer.sv",
        "agents/irq_agent/my_ip_irq_driver.sv",
        "agents/irq_agent/my_ip_irq_monitor.sv",
        "agents/irq_agent/my_ip_irq_agent.sv",
        "agents/irq_agent/my_ip_irq_base_seq.sv",
        "agents/irq_agent/my_ip_irq_agent_pkg.sv",
        "env/my_ip_irq_coverage.sv",
    }
    # nothing pre-existing changed...
    after = tree_digest(env)
    for rel, digest in before.items():
        assert after[rel] == digest, f"pre-existing file changed: {rel}"
    # ...and the files needing manual wiring are flagged
    assert "sim/tb.f" in report.stale
    assert "env/my_ip_env.sv" in report.stale
    assert "env/my_ip_env_cfg.sv" in report.stale


def test_force_regenerates_everything(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    driver = env / "agents/ctrl_agent/my_ip_ctrl_driver.sv"
    pristine = driver.read_text()
    driver.write_text("// clobbered\n")

    _, report = gen(cfg_dir / "my_ip.yaml", out, force=True)
    assert driver.read_text() == pristine
    assert "agents/ctrl_agent/my_ip_ctrl_driver.sv" in report.forced


def test_dry_run_writes_nothing(work):
    cfg_dir, out = work
    _, report = gen(cfg_dir / "my_ip.yaml", out, dry_run=True)
    assert report.created
    assert not (out / "my_ip_verif").exists()


def test_extended_config_gets_own_vsif_and_cfg_copies(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    _, report = gen(cfg_dir / "my_ip_small.yaml", out)
    env = out / "my_ip_verif"
    # only the new per-config artifacts appear
    assert set(report.created) == {"sim/my_ip_small.vsif", "cfg/my_ip_small.yaml"}
    vsif = (env / "sim/my_ip_small.vsif").read_text()
    assert "session my_ip_small {" in vsif
    assert "CFG=cfg/my_ip_small.yaml" in vsif
    # the copied chain stays consistent: extends points at the sibling copy
    copied = yaml.safe_load((env / "cfg/my_ip_small.yaml").read_text())
    assert copied["extends"] == "my_ip.yaml"
    # base copy exists from the first run
    assert (env / "cfg/my_ip.yaml").is_file()


def test_baked_identity_matches_config(work):
    cfg_dir, out = work
    cfg, _ = gen(cfg_dir / "my_ip_small.yaml", out)
    env = out / "my_ip_verif"
    env_cfg = (env / "env/my_ip_env_cfg.sv").read_text()
    assert 'config_name = "small"' in env_cfg
    assert f'param_hash  = "{param_hash(cfg)}"' in env_cfg
    assert "prm_data_w = 16" in env_cfg     # typed mirror from params
    assert "prm_fifo_depth = 8" in env_cfg


def test_vertical_reuse_rules(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    reuse_dirs = ["agents", "vip", "env", "seq_lib"]
    for d in reuse_dirs:
        for sv in (env / d).rglob("*.sv"):
            text = sv.read_text()
            assert "tb_top" not in text, f"{sv} references the testbench top"
            assert "uvm_config_db#(virtual" not in text, \
                f"{sv} fetches a virtual interface from the config_db"
    # tests/tb are the standalone boundary — the vif handoff lives there
    assert "uvm_config_db#(virtual my_ip_ctrl_if)" in \
        (env / "tests/my_ip_base_test.sv").read_text()
    assert "uvm_config_db#(virtual my_ip_ctrl_if)" in \
        (env / "tb/my_ip_tb_top.sv").read_text()
    # passive agents build no driver/sequencer
    agent = (env / "agents/ctrl_agent/my_ip_ctrl_agent.sv").read_text()
    assert "if (is_active == UVM_ACTIVE) begin" in agent


def test_makefile_and_vsif_essentials(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    mk = (env / "sim/Makefile").read_text()
    assert "-uvmhome CDNS-1.2" in mk
    assert "FILELISTS ?=" in mk and "EXTRA_FILELISTS" in mk
    assert "CDN_VIP_ROOT" in mk
    assert 'vmanager -execcmd "launch' in mk
    for target in ("compile:", "run:", "waves:", "clean:", "regress:", "matrix:"):
        assert target in mk, f"missing target {target}"
    vsif = (env / "sim/my_ip.vsif").read_text()
    assert "session my_ip_default {" in vsif
    assert "top_dir" in vsif and "output_mode" in vsif
    assert "test my_ip_smoke_test {" in vsif
    assert "count : 1;" in vsif and "seed : random;" in vsif
    assert "make -C $ENV(PWD) run TEST=my_ip_smoke_test" in vsif
    tbf = (env / "sim/tb.f").read_text()
    # compile order: interface before agent pkg before env pkg before tests
    order = [tbf.index("my_ip_ctrl_if.sv"), tbf.index("my_ip_ctrl_agent_pkg.sv"),
             tbf.index("my_ip_env_pkg.sv"), tbf.index("my_ip_seq_lib_pkg.sv"),
             tbf.index("my_ip_test_pkg.sv"), tbf.index("my_ip_tb_top.sv")]
    assert order == sorted(order)


def test_copilot_kit_uses_real_names(work):
    cfg_dir, out = work
    gen(cfg_dir / "my_ip.yaml", out)
    env = out / "my_ip_verif"
    instructions = (env / ".github/copilot-instructions.md").read_text()
    assert "my_ip_env_cfg" in instructions
    assert "make run TEST=my_ip_smoke_test" in instructions
    assert "my_ip.vsif" in instructions
    for prompt in (env / ".github/prompts").glob("*.prompt.md"):
        text = prompt.read_text()
        assert "my_ip" in text, f"{prompt} has no IP-specific content"
        assert "<ip>" not in text and "<IP>" not in text, \
            f"{prompt} contains generic placeholders"
    # chaining: each later phase names its predecessor's prompt
    chain = [
        ("implement-agents", "connect-dut.prompt.md"),
        ("write-tests", "implement-agents.prompt.md"),
        ("triage-regression", "write-tests.prompt.md"),
        ("coverage-closure", "triage-regression.prompt.md"),
        ("verif-closure", "coverage-closure.prompt.md"),
    ]
    for phase, predecessor in chain:
        text = (env / f".github/prompts/{phase}.prompt.md").read_text()
        assert predecessor in text, f"{phase} does not chain to {predecessor}"


def test_cli_end_to_end(work, capsys):
    cfg_dir, out = work
    rc = cli_main([str(cfg_dir / "simple_fifo.yaml"), "-o", str(out)])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "simple_fifo_verif" in captured
    assert "next steps" in captured
    # no-VIP config: no vip dir, no vip filelists
    env = out / "simple_fifo_verif"
    assert not (env / "vip").exists()
    assert not list((env / "sim").glob("vip_*.f"))


def test_cli_config_error(work, capsys):
    cfg_dir, out = work
    bad = cfg_dir / "bad.yaml"
    bad.write_text("ip_name: 9bad\n")
    rc = cli_main([str(bad), "-o", str(out)])
    assert rc == 2
    assert "error" in capsys.readouterr().err
