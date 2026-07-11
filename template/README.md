# Template payload

Everything under this directory makes up the reusable DV template: the
`uvm-gen` environment generator, the chkq checker-qualification kit, the
external vplan-drafting kit, the methodology guides, the cockpit config,
and the engineer-facing `USERGUIDE.md`.

**One deliberate exception:** `.github/` (the Copilot agent pack — agents,
prompts, skills) lives at the true repository root, one level up, not here.
GitHub Copilot only discovers `copilot-instructions.md`, `prompts/*`, and
`agents/*` at the root of whatever's actually open in the editor — nesting
it under `template/` would make the entire agent pack invisible to Copilot
on this repo. See the root `README.md`'s "What's in the template" section
for the full picture and the reasoning.

Generated IP environments (`<ip>_verif/`, created by running
`uvm-gen/uvm_gen.py`) land at the true repository root too, as siblings of
this directory — never inside it. That split is the point: this directory
is the template machinery; anything sitting next to it at the root is a
generated instance, not template content.
