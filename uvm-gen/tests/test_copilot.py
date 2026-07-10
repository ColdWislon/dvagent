"""Copilot DV agent pack staging: discovery, file set, bridge rendering,
per-IP support files, on/off switches, and the re-run policy on pack copies."""

from pathlib import Path

from conftest import tree_hashes

from uvm_gen.copilot import (
    COMPANION_FILES,
    PER_ENV_FILES,
    RENDERED_FILES,
    STANDALONE_RENDERED,
    find_pack,
    find_workspace_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[2]  # the pack's home repo
PACK_GITHUB = REPO_ROOT / ".github"


def pack_expected_files():
    """Full standalone staging set."""
    files = {
        str(p.relative_to(REPO_ROOT)) for p in PACK_GITHUB.rglob("*") if p.is_file()
    }
    files |= {
        env_rel
        for pack_rel, env_rel in COMPANION_FILES
        if (REPO_ROOT / pack_rel).is_file()
    }
    files |= {env_rel for _, env_rel in RENDERED_FILES + STANDALONE_RENDERED}
    return files


def test_pack_is_discovered_next_to_uvm_gen():
    assert find_pack() == REPO_ROOT


def test_pack_staged_by_default(generated_env):
    actual = {
        str(p.relative_to(generated_env))
        for p in generated_env.rglob("*")
        if p.is_file()
    }
    missing = pack_expected_files() - actual
    assert not missing, f"pack files not staged: {sorted(missing)[:10]}"
    # verbatim copies are byte-identical
    for rel in ("copilot-instructions.md", "prompts/start-here.prompt.md",
                "skills/dv-wrapper/SKILL.md", "USERGUIDE.md"):
        src = (PACK_GITHUB / rel) if rel != "USERGUIDE.md" else REPO_ROOT / "USERGUIDE.md"
        assert (generated_env / ".github" / rel).read_bytes() == src.read_bytes()
    assert (generated_env / "cockpit.ini").read_bytes() == (REPO_ROOT / "cockpit.ini").read_bytes()


def test_bridge_instructions_rendered(generated_env):
    text = (generated_env / ".github/instructions/uvm-gen-env.instructions.md").read_text()
    assert "applyTo: '**'" in text
    assert "dv compile my_ip" in text and "make compile" in text
    assert "make run TEST=<test> SEED=N" in text
    assert "triage_log.py" in text
    assert "+MY_IP_ALL_PASSIVE" in text
    assert "verif_matrix.yaml" in text


def test_claude_context_prefilled(generated_env):
    text = (generated_env / "docs/CLAUDE.md").read_text()
    assert "my_ip_ctrl_agent (ACTIVE)" in text
    assert "my_ip_irq_agent (PASSIVE)" in text
    assert "my_ip_scoreboard" in text and "PLACEHOLDER-CHECK" in text
    assert "my_ip_smoke_test" in text
    assert "apb0 (APB, master" in text and "i3c0 (I3C, controller" in text
    assert "`DATA_WIDTH=32`" in text


def test_support_files_rendered(generated_env):
    vplan = (generated_env / "docs/vplan.md").read_text()
    assert "VP-MY_IP-001" in vplan
    sanity = (generated_env / "dv/lists/sanity.list").read_text()
    assert "my_ip_smoke_test          random" in sanity
    chkq_list = (generated_env / "dv/lists/chkq.list").read_text()
    assert "+CHKQ_ENABLE" in chkq_list and "sim/tb.f" in chkq_list
    paths = (generated_env / "dv/tests/negative/chkq_paths.svh").read_text()
    assert "MY_IP_CHKQ_PATHS_SVH" in paths
    assert (generated_env / "dv/status/.keep").exists()
    assert (generated_env / "dv/cov/exclusion_requests.md").exists()
    assert (generated_env / "docs/methodology/definition-of-done.md").exists()
    assert (generated_env / "external-vplan-kit/README.md").exists()


def test_chkq_kit_staged_but_not_compiled(generated_env):
    assert (generated_env / "dv/tests/negative/chkq_pkg.sv").exists()
    tb_f = (generated_env / "sim/tb.f").read_text()
    assert "# ../dv/tests/negative/chkq_pkg.sv" in tb_f  # ready, commented
    active = [
        l.strip() for l in tb_f.splitlines()
        if l.strip() and not l.strip().startswith(("#", "+incdir"))
    ]
    assert not any("chkq" in l for l in active)


def test_getting_started_with_pack(generated_env):
    text = (generated_env / "GETTING_STARTED.md").read_text()
    assert "/start-here" in text
    assert "make run TEST=my_ip_smoke_test" in text
    assert ".github/USERGUIDE.md" in text
    assert "CDN_VIP_ROOT" in text  # example config has VIPs
    readme = (generated_env / "README.md").read_text()
    assert "GETTING_STARTED.md" in readme


def test_no_copilot_flag(examples_copy, gen, tmp_path):
    env = gen(examples_copy / "my_ip.yaml", out=tmp_path / "nc", extra=("--no-copilot",))
    assert not (env / ".github").exists()
    assert not (env / "docs").exists()
    assert not (env / "dv").exists()
    assert not (env / "cockpit.ini").exists()
    text = (env / "GETTING_STARTED.md").read_text()
    assert "## 5. Working with the Copilot DV agents" not in text
    assert "generated without the team's GitHub Copilot agent pack" in text
    assert "--copilot-pack" in text  # tells the user how to add it later


def test_yaml_copilot_false(examples_copy, gen, tmp_path):
    cfg = examples_copy / "my_ip.yaml"
    cfg.write_text(cfg.read_text() + "\ncopilot: false\n")
    env = gen(cfg, out=tmp_path / "yf")
    assert not (env / ".github").exists()


def test_yaml_copilot_explicit_path(tmp_path, gen):
    mini = tmp_path / "minipack"
    (mini / ".github/prompts").mkdir(parents=True)
    (mini / ".github/copilot-instructions.md").write_text("# mini contract\n")
    (mini / ".github/prompts/status.prompt.md").write_text("---\n---\nhi\n")
    cfg = tmp_path / "ip.yaml"
    cfg.write_text("ip_name: my_ip\ncopilot: minipack\n")

    env = gen(cfg, out=tmp_path / "out")

    assert (env / ".github/copilot-instructions.md").read_text() == "# mini contract\n"
    assert (env / ".github/prompts/status.prompt.md").exists()
    # rendered support files come from uvm-gen, not the pack
    assert (env / "docs/CLAUDE.md").exists()
    assert (env / ".github/instructions/uvm-gen-env.instructions.md").exists()
    # companions absent from the mini pack are skipped, not errors
    assert not (env / "dv/tests/negative/chkq_pkg.sv").exists()


def test_yaml_copilot_missing_path_errors(tmp_path, gen, capsys):
    cfg = tmp_path / "ip.yaml"
    cfg.write_text("ip_name: my_ip\ncopilot: nowhere/\n")
    gen(cfg, out=tmp_path / "out", expect_rc=1)
    assert "Copilot pack not found" in capsys.readouterr().err


def _make_workspace(root: Path):
    """A minimal pack-rooted workspace (as if cloned from the template)."""
    (root / ".github/prompts").mkdir(parents=True)
    (root / ".github/copilot-instructions.md").write_text("# contract\n")
    (root / ".github/prompts/start-here.prompt.md").write_text("---\n---\nhi\n")
    (root / "chkq-kit").mkdir()
    for f in ("chkq_pkg.sv", "example_neg_test.sv"):
        (root / "chkq-kit" / f).write_bytes((REPO_ROOT / "chkq-kit" / f).read_bytes())
    (root / "docs/methodology").mkdir(parents=True)
    (root / "docs/methodology/definition-of-done.md").write_text("# DoD\n")
    (root / "cockpit.ini").write_text("[tool]\n")
    return root


def test_workspace_mode_stages_per_ip_collateral_only(tmp_path, gen):
    ws = _make_workspace(tmp_path / "ws")
    cfg = ws / "uart.yaml"
    cfg.write_text("ip_name: my_ip\nagents: [{name: ctrl}]\n")

    env = gen(cfg, out=ws)

    assert find_workspace_pack(env) == ws.resolve()
    # the pack is NOT duplicated into the env
    assert not (env / ".github").exists()
    assert not (env / "cockpit.ini").exists()
    assert not (env / "external-vplan-kit").exists()
    assert not (env / "docs/methodology").exists()
    # per-IP collateral IS staged
    assert (env / "docs/CLAUDE.md").exists()
    assert (env / "docs/vplan.md").exists()
    assert (env / "dv/tests/negative/chkq_pkg.sv").exists()
    assert (env / "dv/lists/sanity.list").exists()
    # wording knows the pack lives at the workspace root
    text = (env / "GETTING_STARTED.md").read_text()
    assert "workspace root" in text
    assert "/start-here" in text
    assert "move `.github/`" not in text


def test_workspace_mode_wins_over_explicit_pack(tmp_path, gen):
    ws = _make_workspace(tmp_path / "ws")
    cfg = ws / "ip.yaml"
    cfg.write_text("ip_name: my_ip\ncopilot: true\n")
    env = gen(cfg, out=ws)
    assert not (env / ".github").exists()
    assert (env / "docs/CLAUDE.md").exists()


def test_standalone_mode_unaffected_outside_workspaces(examples_copy, gen, tmp_path):
    # tmp_path has no pack-rooted ancestor -> full staging (covered in depth
    # by the tests above); just pin the mode discriminator here.
    env = gen(examples_copy / "my_ip.yaml", out=tmp_path / "sa")
    assert find_workspace_pack(env) is None
    assert (env / ".github/copilot-instructions.md").exists()
    assert (env / ".github/instructions/uvm-gen-env.instructions.md").exists()


def test_rerun_policy_covers_pack_copies(examples_copy, gen):
    env = gen(examples_copy / "my_ip.yaml")
    contract = env / ".github/copilot-instructions.md"
    claude = env / "docs/CLAUDE.md"
    pristine_contract = contract.read_text()
    contract.write_text(pristine_contract + "\n<!-- team tweak -->\n")
    claude.write_text(claude.read_text() + "\n## Known quirks\n- the real list\n")
    before = tree_hashes(env)

    gen(examples_copy / "my_ip.yaml")  # re-run: nothing changes
    assert tree_hashes(env) == before

    gen(examples_copy / "my_ip.yaml", force=True)  # force restores pack copy
    assert contract.read_text() == pristine_contract
