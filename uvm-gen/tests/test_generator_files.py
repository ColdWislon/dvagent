from pathlib import Path

from uvm_gen import cli

EXPECTED_BASE = [
    "README.md",
    ".gitignore",
    "verif_matrix.yaml",
    "cfg/my_ip.yaml",
    "env/my_ip_reg_block.sv",
    "env/my_ip_reg_adapter.sv",
    "env/my_ip_apb0_vip.sv",
    "env/my_ip_i3c0_vip.sv",
    "env/my_ip_env_cfg.sv",
    "env/my_ip_scoreboard.sv",
    "env/my_ip_ctrl_cov.sv",
    "env/my_ip_irq_cov.sv",
    "env/my_ip_vsequencer.sv",
    "env/my_ip_env.sv",
    "env/my_ip_env_pkg.sv",
    "seq_lib/my_ip_base_vseq.sv",
    "seq_lib/my_ip_smoke_vseq.sv",
    "seq_lib/my_ip_seq_pkg.sv",
    "tests/my_ip_base_test.sv",
    "tests/my_ip_smoke_test.sv",
    "tests/my_ip_test_pkg.sv",
    "tb/my_ip_top_stub.sv",
    "tb/tb_top.sv",
    "sim/Makefile",
    "sim/dut.f",
    "sim/tb.f",
    "sim/vip_apb.f",
    "sim/vip_i3c.f",
    "sim/my_ip_default.vsif",
    "sim/probe.tcl",
    "sim/scripts/cfg_tool.py",
]

AGENT_FILES = [
    "{ip}_{a}_if.sv",
    "{ip}_{a}_seq_item.sv",
    "{ip}_{a}_cfg.sv",
    "{ip}_{a}_sequencer.sv",
    "{ip}_{a}_driver.sv",
    "{ip}_{a}_monitor.sv",
    "{ip}_{a}_agent.sv",
    "{ip}_{a}_base_seq.sv",
    "{ip}_{a}_agent_pkg.sv",
]


def expected_files():
    files = list(EXPECTED_BASE)
    for agent in ("ctrl", "irq"):
        files += [
            f"agents/{agent}_agent/" + f.format(ip="my_ip", a=agent)
            for f in AGENT_FILES
        ]
    return sorted(files)


def test_full_example_generates_exact_file_set(generated_env):
    actual = sorted(
        str(p.relative_to(generated_env))
        for p in generated_env.rglob("*")
        if p.is_file()
    )
    assert actual == expected_files()


def test_no_jinja_leftovers_or_empty_files(generated_env):
    for p in generated_env.rglob("*"):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        assert text.strip(), f"{p} is empty"
        assert "{{" not in text, f"jinja leftover in {p}"
        assert "{%" not in text, f"jinja leftover in {p}"


def test_env_cfg_content(generated_env):
    text = (generated_env / "env/my_ip_env_cfg.sv").read_text()
    # params (sorted) as fields with generation-time defaults
    assert "int DATA_WIDTH = 32;" in text
    assert "int FIFO_DEPTH = 8;" in text
    assert "int NUM_CHANNELS = 2;" in text
    # plusarg plumbing + passive switch + banner + hash
    assert '$value$plusargs("PARAM_DATA_WIDTH=%d", DATA_WIDTH)' in text
    assert '$sformatf("param DATA_WIDTH = %0d", DATA_WIDTH)' in text
    assert '$test$plusargs("MY_IP_ALL_PASSIVE")' in text
    assert "set_all_passive" in text
    assert "param_hash" in text and "32'h811c_9dc5" in text
    # agent + vip cfg handles, RAL knobs
    for handle in ("ctrl_cfg", "irq_cfg", "apb0_cfg", "i3c0_cfg"):
        assert handle in text
    for knob in ("enable_ral", "ral_env_owns_bus", "ral_base_addr", "regmodel"):
        assert knob in text
    # canonical order matches sorted param names
    canon = text.index("DATA_WIDTH="), text.index("FIFO_DEPTH="), text.index("NUM_CHANNELS=")
    assert list(canon) == sorted(canon)


def test_agent_modes_respected(generated_env):
    ctrl = (generated_env / "agents/ctrl_agent/my_ip_ctrl_cfg.sv").read_text()
    irq = (generated_env / "agents/irq_agent/my_ip_irq_cfg.sv").read_text()
    assert "is_active = UVM_ACTIVE;" in ctrl
    assert "is_active = UVM_PASSIVE;" in irq


def test_makefile_content(generated_env):
    text = (generated_env / "sim/Makefile").read_text()
    assert "-uvmhome CDNS-1.2" in text
    assert "CDN_VIP_ROOT" in text
    assert "-f $(DUT_F) -f $(TB_F) -f vip_apb.f -f vip_i3c.f" in text
    for target in ("compile:", "run:", "waves:", "regress:", "matrix:", "clean:"):
        assert target in text
    assert "-elaborate" in text
    assert "-access +rwc" in text
    assert 'vmanager -execcmd "launch' in text.replace("$(VMANAGER)", "vmanager")
    assert "+MY_IP_ALL_PASSIVE" in text
    # recipes must be tab-indented (make hard requirement)
    assert "\t$(XRUN_BASE) -elaborate" in text
    assert "\t-$(XRUN_BASE) $(RUN_ARGS)" in text
    assert "\t$(COLLECT)" in text
    assert "\trm -rf" in text


def test_vsif_content(generated_env):
    text = (generated_env / "sim/my_ip_default.vsif").read_text()
    assert "session my_ip_default {" in text
    assert "top_dir" in text and "output_mode" in text
    assert "group smoke {" in text
    assert "test my_ip_smoke_test {" in text
    assert "run_script" in text and "make -C" in text
    assert "count : 1;" in text
    assert "sv_seed : random;" in text
    # commented placeholder pattern present
    assert "// group traffic" in text or "// group" in text


def test_dut_f_stub_first_rtl_commented(generated_env):
    text = (generated_env / "sim/dut.f").read_text()
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    assert lines == ["../tb/my_ip_top_stub.sv"]
    assert "# -f " in text  # the real RTL filelist, pre-filled but commented


def test_tb_f_compile_order(generated_env):
    text = (generated_env / "sim/tb.f").read_text()
    order = [
        "my_ip_ctrl_if.sv",
        "my_ip_ctrl_agent_pkg.sv",
        "my_ip_env_pkg.sv",
        "my_ip_seq_pkg.sv",
        "my_ip_test_pkg.sv",
        "tb_top.sv",
    ]
    positions = [text.index(f) for f in order]
    assert positions == sorted(positions)
    assert "+incdir+../agents/ctrl_agent" in text
    assert "+incdir+../env" in text


def test_vip_wrappers_and_filelists(generated_env):
    apb = (generated_env / "env/my_ip_apb0_vip.sv").read_text()
    assert "MY_IP_USE_CDN_APB_VIP" in apb
    assert 'role = "master";' in apb
    i3c = (generated_env / "env/my_ip_i3c0_vip.sv").read_text()
    assert "MY_IP_USE_CDN_I3C_VIP" in i3c
    assert 'role = "controller";' in i3c
    assert "ibi_enable      = 1;" in i3c
    f = (generated_env / "sim/vip_i3c.f").read_text()
    assert "$CDN_VIP_ROOT" in f
    assert "+define+MY_IP_USE_CDN_I3C_VIP" in f


def test_stub_declares_defparam_params(generated_env):
    text = (generated_env / "tb/my_ip_top_stub.sv").read_text()
    assert "module my_ip_top;" in text
    assert "parameter FIFO_DEPTH = 8;" in text
    assert "DATA_WIDTH" not in text  # define-style params are not stub parameters


def test_minimal_and_cornercase_configs_render(tmp_path, gen):
    # no agents, no vips, no params
    cfg = tmp_path / "bare.yaml"
    cfg.write_text("ip_name: my_ip\n")
    env = gen(cfg, out=tmp_path / "bare_out")
    assert (env / "env/my_ip_env.sv").exists()
    assert not (env / "env/my_ip_reg_adapter.sv").exists()  # needs an agent
    assert (env / "sim/my_ip_default.vsif").exists()

    # vips only
    cfg2 = tmp_path / "viponly.yaml"
    cfg2.write_text(
        "ip_name: my_ip\nvips:\n  - {protocol: ahb, name: ahb0, role: slave}\n"
    )
    env2 = gen(cfg2, out=tmp_path / "vip_out")
    text = (env2 / "env/my_ip_env.sv").read_text()
    assert "ahb0_vip" in text


def test_dry_run_writes_nothing(examples_copy, tmp_path):
    out = tmp_path / "dry"
    rc = cli.main([str(examples_copy / "my_ip.yaml"), "-o", str(out), "--dry-run"])
    assert rc == 0
    assert not out.exists() or not any(out.rglob("*"))
