import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(ROOT / "uvm_gen.py"), *args],
        capture_output=True, text=True, cwd=cwd,
    )


def test_version():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert "uvm-gen" in proc.stdout


def test_missing_config_is_clean_error(tmp_path):
    proc = run_cli("nope.yaml", "-o", str(tmp_path))
    assert proc.returncode == 1
    assert "uvm-gen: error:" in proc.stderr
    assert "not found" in proc.stderr


def test_invalid_config_is_clean_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("agents: [{name: a}]\n")  # no ip_name
    proc = run_cli(str(bad), "-o", str(tmp_path))
    assert proc.returncode == 1
    assert "ip_name" in proc.stderr


def test_end_to_end_generation_via_script(tmp_path):
    proc = run_cli(str(ROOT / "examples/my_ip.yaml"), "-o", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "created" in proc.stdout
    assert (tmp_path / "my_ip_verif/sim/Makefile").exists()
    # second run: everything skipped
    proc2 = run_cli(str(ROOT / "examples/my_ip.yaml"), "-o", str(tmp_path))
    assert proc2.returncode == 0
    assert "created: 0 file(s)" in proc2.stdout
    assert "skipped" in proc2.stdout
