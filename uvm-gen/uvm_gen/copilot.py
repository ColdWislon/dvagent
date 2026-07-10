"""GitHub Copilot DV agent pack integration.

uvm-gen can stage the team's Copilot agent pack (the `.github/` tree with
agents/prompts/skills/instructions) plus its companion kits into the generated
environment, so a freshly generated env is agent-ready:

  .github/**                        verbatim copy of the pack
  .github/USERGUIDE.md              the pack's engineer quick start
  .github/instructions/uvm-gen-env.instructions.md   RENDERED bridge: maps the
                                    pack's `dv` golden commands onto this
                                    env's make flow
  cockpit.ini                       verif-cockpit configuration
  external-vplan-kit/**             out-of-VS-Code vplan drafting kit
  docs/CLAUDE.md                    per-IP agent context, PRE-FILLED from the
                                    generated architecture
  docs/vplan.md                     vplan skeleton (traceability contract)
  docs/methodology/definition-of-done.md
  dv/status/.keep                   session sidecars / cockpit data dir
  dv/cov/exclusion_requests.md      coverage-exclusion proposal queue
  dv/lists/sanity.list, chkq.list   regression lists (smoke pre-seeded)
  dv/tests/negative/chkq_pkg.sv     checker-qualification kit (staged, not
  dv/tests/negative/example_neg_test.sv   compiled until wired in tb.f)
  dv/tests/negative/chkq_paths.svh  central forced-path registry

All copies follow the normal write policy: never overwritten on re-run,
regenerated with --force. The pack is located automatically when uvm-gen runs
from a checkout of its home repository; point --copilot-pack (or the YAML
`copilot:` key) at a pack root otherwise.
"""

from __future__ import annotations

from pathlib import Path

from .config import ConfigError
from .generator import Action

# A directory qualifies as a pack root when this file exists under it.
PACK_MARKER = ".github/copilot-instructions.md"

# Companion files staged relative to the env root: (pack-relative, env-relative)
COMPANION_FILES = [
    ("USERGUIDE.md", ".github/USERGUIDE.md"),
    ("cockpit.ini", "cockpit.ini"),
    ("chkq-kit/chkq_pkg.sv", "dv/tests/negative/chkq_pkg.sv"),
    ("chkq-kit/example_neg_test.sv", "dv/tests/negative/example_neg_test.sv"),
    ("external-vplan-kit/README.md", "external-vplan-kit/README.md"),
    (
        "external-vplan-kit/VPLAN_DRAFTING_PROMPT.md",
        "external-vplan-kit/VPLAN_DRAFTING_PROMPT.md",
    ),
    (
        "repo-templates/docs/methodology/definition-of-done.md",
        "docs/methodology/definition-of-done.md",
    ),
]

# Rendered (IP-tailored) support files: (template, env-relative destination)
RENDERED_FILES = [
    ("copilot/uvm_gen_env.instructions.md.j2", ".github/instructions/uvm-gen-env.instructions.md"),
    ("copilot/claude_context.md.j2", "docs/CLAUDE.md"),
    ("copilot/vplan.md.j2", "docs/vplan.md"),
    ("copilot/exclusion_requests.md.j2", "dv/cov/exclusion_requests.md"),
    ("copilot/sanity.list.j2", "dv/lists/sanity.list"),
    ("copilot/chkq.list.j2", "dv/lists/chkq.list"),
    ("copilot/chkq_paths.svh.j2", "dv/tests/negative/chkq_paths.svh"),
    ("copilot/status_keep.j2", "dv/status/.keep"),
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


def plan_copilot(pack_root: Path) -> list[Action]:
    """Copy/render actions staging the pack into the env root."""
    actions: list[Action] = []

    github = pack_root / ".github"
    for src in sorted(github.rglob("*")):
        if src.is_file():
            rel = src.relative_to(pack_root)
            actions.append(Action(relpath=str(rel), source=src))

    for pack_rel, env_rel in COMPANION_FILES:
        src = pack_root / pack_rel
        if src.is_file():
            actions.append(Action(relpath=env_rel, source=src))

    for template, env_rel in RENDERED_FILES:
        actions.append(Action(relpath=env_rel, template=template))

    return actions
