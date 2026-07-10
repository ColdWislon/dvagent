"""The tool's contract: never overwrite, only add; --force regenerates all
except verif_matrix.yaml."""

from conftest import tree_hashes


def test_rerun_changes_nothing(examples_copy, gen):
    env = gen(examples_copy / "my_ip.yaml")
    # user edits a generated file
    driver = env / "agents/ctrl_agent/my_ip_ctrl_driver.sv"
    driver.write_text(driver.read_text() + "\n// USER EDIT - precious\n")
    before = tree_hashes(env)

    gen(examples_copy / "my_ip.yaml")  # re-run, same config

    assert tree_hashes(env) == before
    assert "USER EDIT - precious" in driver.read_text()


def test_adding_agent_creates_only_new_files(examples_copy, gen, capsys):
    env = gen(examples_copy / "my_ip.yaml")
    before = tree_hashes(env)

    cfg = examples_copy / "my_ip.yaml"
    cfg.write_text(cfg.read_text().replace(
        "agents:\n", "agents:\n  - name: dbg\n    mode: active\n"
    ))
    gen(cfg)
    out = capsys.readouterr().out

    after = tree_hashes(env)
    new_files = sorted(set(after) - set(before))
    assert new_files == [
        "agents/dbg_agent/my_ip_dbg_agent.sv",
        "agents/dbg_agent/my_ip_dbg_agent_pkg.sv",
        "agents/dbg_agent/my_ip_dbg_base_seq.sv",
        "agents/dbg_agent/my_ip_dbg_cfg.sv",
        "agents/dbg_agent/my_ip_dbg_driver.sv",
        "agents/dbg_agent/my_ip_dbg_if.sv",
        "agents/dbg_agent/my_ip_dbg_monitor.sv",
        "agents/dbg_agent/my_ip_dbg_seq_item.sv",
        "agents/dbg_agent/my_ip_dbg_sequencer.sv",
        "env/my_ip_dbg_cov.sv",
    ]
    # every pre-existing file untouched
    assert all(after[p] == h for p, h in before.items())
    # and the user is told what to wire up by hand
    assert "wire them in by hand" in out
    assert "my_ip_env_cfg.sv" in out


def test_second_config_adds_only_cfg_copy_and_vsif(examples_copy, gen):
    env = gen(examples_copy / "my_ip.yaml")
    before = tree_hashes(env)

    gen(examples_copy / "my_ip_small.yaml")

    after = tree_hashes(env)
    assert sorted(set(after) - set(before)) == [
        "cfg/my_ip_small.yaml",
        "sim/my_ip_small.vsif",
    ]
    assert all(after[p] == h for p, h in before.items())
    vsif = (env / "sim/my_ip_small.vsif").read_text()
    assert "session my_ip_small {" in vsif
    assert "CFG=../cfg/my_ip_small.yaml" in vsif


def test_extends_rewritten_to_sibling_copy(tmp_path, gen):
    base_dir = tmp_path / "specs" / "shared"
    base_dir.mkdir(parents=True)
    (base_dir / "my_ip.yaml").write_text("ip_name: my_ip\nparams: {W: 8}\n")
    child = tmp_path / "specs" / "fast.yaml"
    child.write_text("extends: shared/my_ip.yaml\nconfig_name: fast\n")

    env = gen(child, out=tmp_path / "out")

    assert (env / "cfg/my_ip.yaml").exists()
    copied = (env / "cfg/fast.yaml").read_text()
    assert "extends: my_ip.yaml" in copied  # points at the sibling copy


def test_force_regenerates_but_preserves_matrix(examples_copy, gen):
    env = gen(examples_copy / "my_ip.yaml")

    driver = env / "agents/ctrl_agent/my_ip_ctrl_driver.sv"
    pristine = driver.read_text()
    driver.write_text(pristine + "\n// USER EDIT\n")

    matrix = env / "verif_matrix.yaml"
    matrix.write_text(
        matrix.read_text() + "- config_name: default\n  result: pass\n"
    )
    matrix_with_history = matrix.read_text()

    gen(examples_copy / "my_ip.yaml", force=True)

    assert driver.read_text() == pristine            # regenerated
    assert matrix.read_text() == matrix_with_history  # history kept


def test_input_config_inside_cfg_dir_is_never_touched(examples_copy, gen):
    env = gen(examples_copy / "my_ip.yaml")
    cfg_copy = env / "cfg/my_ip.yaml"
    cfg_copy.write_text(cfg_copy.read_text() + "# user tweak\n")
    content = cfg_copy.read_text()

    # regenerate FROM the copy in cfg/ (the canonical workflow) with --force
    gen(cfg_copy, force=True)

    assert cfg_copy.read_text() == content
