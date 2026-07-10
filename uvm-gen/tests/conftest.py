import hashlib
import shutil
from pathlib import Path

import pytest

from uvm_gen import cli

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture
def examples_copy(tmp_path):
    """Mutable copy of the shipped example configs."""
    dest = tmp_path / "examples"
    shutil.copytree(EXAMPLES, dest)
    return dest


@pytest.fixture
def gen(tmp_path):
    """Run the real CLI; returns the env root."""

    def _gen(cfg_path, out=None, force=False, dry_run=False, expect_rc=0, extra=()):
        out = Path(out) if out else tmp_path / "out"
        argv = [str(cfg_path), "-o", str(out), *extra]
        if force:
            argv.append("--force")
        if dry_run:
            argv.append("--dry-run")
        rc = cli.main(argv)
        assert rc == expect_rc, f"uvm_gen exited {rc}, expected {expect_rc}"
        return out / "my_ip_verif"

    return _gen


@pytest.fixture
def generated_env(examples_copy, gen):
    """A fresh env generated from the full example config."""
    return gen(examples_copy / "my_ip.yaml")


def tree_hashes(root: Path) -> dict:
    """{relpath: sha1} for every file under root."""
    return {
        str(p.relative_to(root)): hashlib.sha1(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
