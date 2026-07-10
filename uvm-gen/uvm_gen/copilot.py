"""GitHub Copilot DV agent pack integration.

uvm-gen stages Copilot collateral into generated environments in one of two
modes, so every env starts agent-ready without duplicated material:

IN-WORKSPACE (an ancestor of the output dir is already a pack root — e.g.
generating inside a clone of the starter template): the pack at the
workspace root serves every env; only per-IP collateral is staged:

  docs/CLAUDE.md                    per-IP agent context, PRE-FILLED from the
                                    generated architecture
  docs/vplan.md                     vplan skeleton (traceability contract)
  dv/status/.keep                   session sidecars / cockpit data dir
  dv/cov/exclusion_requests.md      coverage-exclusion proposal queue
  dv/lists/sanity.list, chkq.list   regression lists (smoke pre-seeded)
  dv/tests/negative/chkq_pkg.sv     checker-qualification kit (staged, not
  dv/tests/negative/example_neg_test.sv   compiled until wired in tb.f)
  dv/tests/negative/chkq_paths.svh  central forced-path registry

STANDALONE (the env becomes its own repo): additionally stage the full
pack so the env carries everything:

  .github/**                        verbatim copy of the pack
  .github/USERGUIDE.md              the pack's engineer quick start
  .github/instructions/uvm-gen-env.instructions.md   RENDERED per-IP bridge
  cockpit.ini, external-vplan-kit/**, docs/methodology/definition-of-done.md

All copies follow the normal write policy: never overwritten on re-run,
regenerated with --force. The pack is located automatically (workspace
ancestor first, then next to uvm-gen); point --copilot-pack (or the YAML
`copilot:` key) at a pack root otherwise.
"""

from __future__ import annotations

from pathlib import Path

from .config import ConfigError
from .generator import Action

# A directory qualifies as a pack root when this file exists under it.
PACK_MARKER = ".github/copilot-instructions.md"

# Workspace-level companions: only staged when the env becomes its own repo
# (standalone mode). Inside a pack-rooted workspace (the starter template)
# these already live at the repo root. (pack-relative, env-relative)
WORKSPACE_FILES = [
    ("USERGUIDE.md", ".github/USERGUIDE.md"),
    ("cockpit.ini", "cockpit.ini"),
    ("external-vplan-kit/README.md", "external-vplan-kit/README.md"),
    (
        "external-vplan-kit/VPLAN_DRAFTING_PROMPT.md",
        "external-vplan-kit/VPLAN_DRAFTING_PROMPT.md",
    ),
    (
        "docs/methodology/definition-of-done.md",
        "docs/methodology/definition-of-done.md",
    ),
]

# Per-IP companions: staged in both modes (they live inside the env).
PER_ENV_FILES = [
    ("chkq-kit/chkq_pkg.sv", "dv/tests/negative/chkq_pkg.sv"),
    ("chkq-kit/example_neg_test.sv", "dv/tests/negative/example_neg_test.sv"),
]

# Kept for compatibility with older callers/tests.
COMPANION_FILES = WORKSPACE_FILES + PER_ENV_FILES

# Rendered (IP-tailored) support files staged in both modes.
RENDERED_FILES = [
    ("copilot/claude_context.md.j2", "docs/CLAUDE.md"),
    ("copilot/vplan.md.j2", "docs/vplan.md"),
    ("copilot/exclusion_requests.md.j2", "dv/cov/exclusion_requests.md"),
    ("copilot/sanity.list.j2", "dv/lists/sanity.list"),
    ("copilot/chkq.list.j2", "dv/lists/chkq.list"),
    ("copilot/chkq_paths.svh.j2", "dv/tests/negative/chkq_paths.svh"),
    ("copilot/status_keep.j2", "dv/status/.keep"),
]

# Standalone mode only: the per-IP bridge lands in the env's own .github/
# (inside a workspace the root contract's golden-verb table already applies,
# and a nested instructions file would never be loaded by VS Code).
STANDALONE_RENDERED = [
    ("copilot/uvm_gen_env.instructions.md.j2", ".github/instructions/uvm-gen-env.instructions.md"),
]


def is_pack_root(path: Path) -> bool:
    return (path / PACK_MARKER).is_file()


def find_pack(explicit=None, config_dir: Path | None = None) -> Path | None:
    """Locate the Copilot pack root (the directory containing `.github/`).

    ``explicit`` (CLI --copilot-pack or YAML `copilot: <path>`) may name the
    pack root or its `.github/` directory; relative paths resolve against
    ``config_dir`` (the YAML's directory), then the CWD. Without ``explicit``
    the pack ships alongside uvm-gen: walk up from this package looking for
    the marker (found when running from a checkout of uvm-gen's home repo).
    """
    if explicit is not None:
        candidates = []
        for base in (config_dir, Path.cwd()):
            if base is None:
                continue
            p = (base / explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit)
            candidates += [p, p.parent if p.name == ".github" else p]
        for cand in candidates:
            if is_pack_root(cand):
                return cand
        raise ConfigError(
            f"Copilot pack not found at {explicit!r} "
            f"(expected {PACK_MARKER} under it)"
        )

    here = Path(__file__).resolve()
    for parent in here.parents[:6]:
        if is_pack_root(parent):
            return parent
    return None


def find_workspace_pack(env_root: Path) -> Path | None:
    """Nearest ancestor of the env root that is itself a pack root.

    When found, the environment is being generated INSIDE a Copilot-ready
    workspace (e.g. a clone of the starter template): the pack already
    applies from the repo root and must not be duplicated into the env.
    """
    for parent in Path(env_root).resolve().parents:
        if is_pack_root(parent):
            return parent
    return None


def plan_copilot(pack_root: Path, in_repo: bool = False) -> list[Action]:
    """Copy/render actions staging Copilot collateral into the env root.

    ``in_repo=False`` (standalone): the env becomes its own repo — stage the
    full ``.github/`` pack, the workspace companions, and the per-IP bridge.
    ``in_repo=True`` (inside a pack-rooted workspace): stage only the per-IP
    collateral; the pack at the workspace root serves every env.
    """
    actions: list[Action] = []

    if not in_repo:
        github = pack_root / ".github"
        for src in sorted(github.rglob("*")):
            if src.is_file():
                rel = src.relative_to(pack_root)
                actions.append(Action(relpath=str(rel), source=src))
        for pack_rel, env_rel in WORKSPACE_FILES:
            src = pack_root / pack_rel
            if src.is_file():
                actions.append(Action(relpath=env_rel, source=src))
        for template, env_rel in STANDALONE_RENDERED:
            actions.append(Action(relpath=env_rel, template=template))

    for pack_rel, env_rel in PER_ENV_FILES:
        src = pack_root / pack_rel
        if src.is_file():
            actions.append(Action(relpath=env_rel, source=src))

    for template, env_rel in RENDERED_FILES:
        actions.append(Action(relpath=env_rel, template=template))

    return actions
