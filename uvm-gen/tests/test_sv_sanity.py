"""Structural sanity of the generated SystemVerilog (no simulator available
here): balanced constructs, resolvable includes, package compile order, and
the vertical-reuse guarantee (no tb_top/hierarchy references in env code)."""

import re
from pathlib import Path

import pytest


def strip_comments_and_strings(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)
    return text


BALANCED = [
    (r"\bclass\b", r"\bendclass\b"),
    (r"\bmodule\b", r"\bendmodule\b"),
    (r"\bpackage\b", r"\bendpackage\b"),
    (r"\binterface\b", r"\bendinterface\b"),
    (r"\bfunction\b", r"\bendfunction\b"),
    (r"\btask\b", r"\bendtask\b"),
    (r"\bcovergroup\b", r"\bendgroup\b"),
    (r"\bfork\b", r"\bjoin(_any|_none)?\b"),
    (r"^\s*(?:default\s+)?clocking\b", r"\bendclocking\b"),
]


def sv_files(env_root):
    # .github/ carries the Copilot pack verbatim, including deliberately-bad
    # lint fixtures - only the env's own SV is subject to these checks.
    return sorted(
        p for p in env_root.rglob("*.sv")
        if ".github" not in p.relative_to(env_root).parts
    )


def test_generated_env_has_sv_files(generated_env):
    # 2 agents x 9 + 11 env + 3 seq_lib + 3 tests + 2 tb
    # + 2 staged chkq kit files under dv/tests/negative/
    assert len(sv_files(generated_env)) == 39


def test_balanced_constructs(generated_env):
    for path in sv_files(generated_env):
        text = strip_comments_and_strings(path.read_text())
        for open_re, close_re in BALANCED:
            opens = len(re.findall(open_re, text, flags=re.M))
            closes = len(re.findall(close_re, text, flags=re.M))
            assert opens == closes, (
                f"{path.name}: {opens}x {open_re} vs {closes}x {close_re}"
            )


def test_begin_end_balance(generated_env):
    for path in sv_files(generated_env):
        text = strip_comments_and_strings(path.read_text())
        # exclude macro identifiers like `uvm_object_utils_begin (word chars
        # around them prevent \b...\b matches anyway) and match whole words
        begins = len(re.findall(r"\bbegin\b", text))
        ends = len(re.findall(r"\bend\b", text))
        assert begins == ends, f"{path.name}: {begins} begin vs {ends} end"


def test_package_includes_resolve(generated_env):
    for pkg in generated_env.rglob("*_pkg.sv"):
        for inc in re.findall(r'`include\s+"([^"]+)"', pkg.read_text()):
            if inc == "uvm_macros.svh":
                continue
            assert (pkg.parent / inc).exists(), f"{pkg.name}: missing include {inc}"


def test_every_included_file_defines_something(generated_env):
    for path in sv_files(generated_env):
        if path.parent.name == "tb" or path.name.endswith("_pkg.sv"):
            continue
        if path.name == "example_neg_test.sv":  # chkq kit reference example
            continue
        text = strip_comments_and_strings(path.read_text())
        assert re.search(r"\b(class|interface|module)\b", text), path.name


def test_no_hierarchy_references_in_reusable_code(generated_env):
    """SoC-reuse guarantee: nothing under agents/, env/, seq_lib/, tests/
    mentions tb_top or uses rooted hierarchical paths (code only; comments
    and strings are ignored)."""
    for sub in ("agents", "env", "seq_lib", "tests"):
        for path in (generated_env / sub).rglob("*.sv"):
            text = strip_comments_and_strings(path.read_text())
            assert not re.search(r"\btb_top\b", text), f"tb_top leaked into {path}"
            assert "$root" not in text, f"$root used in {path}"


def test_config_db_used_for_env_cfg_and_vifs(generated_env):
    env = (generated_env / "env/my_ip_env.sv").read_text()
    assert "uvm_config_db #(my_ip_env_cfg)::get" in env
    test = (generated_env / "tests/my_ip_base_test.sv").read_text()
    assert "uvm_config_db #(my_ip_env_cfg)::set" in test
    assert "uvm_config_db #(virtual my_ip_ctrl_if)::get" in test
    tb = (generated_env / "tb/tb_top.sv").read_text()
    assert "uvm_config_db #(virtual my_ip_ctrl_if)::set" in tb
    assert "run_test();" in tb


def test_passive_machinery(generated_env):
    agent = (generated_env / "agents/irq_agent/my_ip_irq_agent.sv").read_text()
    stripped = strip_comments_and_strings(agent)
    assert "cfg.is_active == UVM_ACTIVE" in stripped
    vseq = (generated_env / "seq_lib/my_ip_smoke_vseq.sv").read_text()
    assert "!= null" in vseq  # null-sequencer guard when passive
    env = (generated_env / "env/my_ip_env.sv").read_text()
    assert "? ctrl_agent.m_sequencer : null" in env


def test_ral_wiring(generated_env):
    env = (generated_env / "env/my_ip_env.sv").read_text()
    assert "uvm_reg_predictor #(my_ip_ctrl_seq_item)" in env
    assert "cfg.ral_env_owns_bus" in env
    assert "set_base_addr(cfg.ral_base_addr)" in env
    assert "set_sequencer(ctrl_agent.m_sequencer, reg_adapter)" in env
    block = (generated_env / "env/my_ip_reg_block.sv").read_text()
    assert "extends uvm_reg_block" in block
    assert "lock_model()" in block


def test_scoreboard_and_coverage_hookup(generated_env):
    sb = (generated_env / "env/my_ip_scoreboard.sv").read_text()
    for a in ("ctrl", "irq"):
        assert f"`uvm_analysis_imp_decl(_{a})" in sb
        assert f"write_{a}" in sb
    assert "TODO" in sb
    # the DV agent pack's cockpit/checker-writer key on this marker
    assert "PLACEHOLDER-CHECK" in sb
    cov = (generated_env / "env/my_ip_ctrl_cov.sv").read_text()
    assert "covergroup" in cov and "coverpoint" in cov and "cross" in cov
    env = (generated_env / "env/my_ip_env.sv").read_text()
    assert "scoreboard.ctrl_imp" in env
    assert "ctrl_cov.analysis_export" in env


def test_banner_and_result_lines_present(generated_env):
    cfg = (generated_env / "env/my_ip_env_cfg.sv").read_text()
    assert "UVM_GEN_CFG" in cfg
    test = (generated_env / "tests/my_ip_base_test.sv").read_text()
    assert "** UVM TEST PASSED **" in test
    assert "** UVM TEST FAILED **" in test
    assert "print_banner" in test


@pytest.mark.parametrize("todo_file", [
    "agents/ctrl_agent/my_ip_ctrl_if.sv",
    "agents/ctrl_agent/my_ip_ctrl_driver.sv",
    "agents/ctrl_agent/my_ip_ctrl_monitor.sv",
    "env/my_ip_scoreboard.sv",
    "env/my_ip_ctrl_cov.sv",
    "env/my_ip_reg_block.sv",
    "tb/tb_top.sv",
])
def test_protocol_stubs_carry_todo_markers(generated_env, todo_file):
    assert "TODO" in (generated_env / todo_file).read_text()
