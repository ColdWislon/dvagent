# UVM verification skill pack

Agent Skills (agentskills.io / SKILL.md format) for **creating** and
**reviewing** UVM environments on a Cadence Xcelium / vManager / IMC / Jenkins
stack. Each skill is a self-contained folder that a skills-compatible agent
(GitHub Copilot agent mode, and any other agentskills client) loads on demand.

## Contents

### Authoring — build an environment
| Skill | Produces |
|---|---|
| `uvm-sequence-item` | transaction (fields, constraints, print/compare) |
| `uvm-driver` | pin driver (get_next_item/item_done, reset) |
| `uvm-monitor` | passive monitor (reconstruct + analysis_port) |
| `uvm-agent` | driver+monitor+sequencer+config, active/passive |
| `uvm-sequence` | stimulus sequence |
| `uvm-vsequence` | virtual sequence + vsequencer orchestration |
| `uvm-env` | top assembly + TLM connectivity |
| `uvm-scoreboard` | checker (expected vs actual, residual checks) |
| `uvm-coverage` | functional coverage subscriber, VP-xxx-tagged |
| `uvm-config` | config objects + config_db discipline, vif delivery |
| `uvm-ral` | register model + adapter + predictor |
| `uvm-test` | test class (config + launch vseq under objection) |

### Visibility
| Skill | Role |
|---|---|
| `verif-cockpit` | local static-HTML cockpit per IP (pending human, scorecard, vplan, clusters, sessions); `scripts/cockpit.py` + `cockpit.ini` tool abstraction |

### Review / enforcement — sign off an environment
| Skill | Role |
|---|---|
| `naming-conventions` | house naming ruleset (source of truth) |
| `phasing-check` | phase + objection ruleset (source of truth) |
| `deprecation-lint` | deprecated API + anti-pattern ruleset (source of truth) + `scripts/lint.py` |
| `log-triage` | parse/classify Xcelium+UVM logs; first causal error + normalized failure signature; `scripts/triage_log.py` (deterministic) |
| `regression-triage` | cluster a red regression by signature, rank, dispatch plan (consumes `log-triage`) |
| `debug-strategy` | hypothesis-driven debug of one failing sim; per-failure-mode playbooks (mismatch/hang/X-prop/SVA/randomize/RAL) |
| `verif-env-review` | the single review entry point: reviews the **full verification environment** (9 axes: testbench code + TB top, build, regression, coverage, SVA, vPlan, CI, reproducibility); folds the testbench-code review + the three law skills + `lint.py`; scorecard + milestone verdict |

## Dependency graph

```
authoring skills ─────────► naming-conventions
                            phasing-check        (rulesets: single source of
                            deprecation-lint      truth, referenced not copied)
                                 ▲
                                 │  + deprecation-lint/scripts/lint.py
verif-env-review ────────────────┘
   9 axes: TB code / TB top / build / regression / coverage / SVA / vPlan / CI / hygiene
   (the TB-code axis reuses the three law skills verbatim)
                  │
                  └─► aggregated JSON + scorecard ─► Jenkins milestone gate
                                                     (fail on error, M0-M3 rollup)

run/debug loop:   log-triage (triage_log.py) ─► regression-triage ─► debug-strategy
                  signature JSON ──► clusters/dispatch JSON ──► root cause + guard
```

Authoring skills point at the three law skills rather than restating rules.
`verif-env-review` runs those same rulesets over the testbench code (its first
axis) and adds the infrastructure axes -- so what the author is told to do and
what the environment audit signs off are consistent by construction.

## Jenkins gate hook

Four mechanical sign-off signals, no taste required:
- **DoD checklists** in each authoring `SKILL.md` — per-component done criteria,
  including scoreboard check-independence (expected from observed input + an
  independent reference, never from the stimulus).
- **`// VP-xxx` tags** on tests and coverpoints — greppable traceability
  to the vPlan.
- **`verif-env-review` JSON** — `summary.dod_pass` is `false` on any `error`
  finding; wire it into the Jenkins stage to pass/fail deterministically.
- **`deprecation-lint/scripts/lint.py`** — deterministic, LLM-free check of the
  independence rules (no sequence/stimulus coupling in scoreboards; no
  driver→scoreboard path); same JSON schema, non-zero exit on error.

## Install (GitHub Copilot)

Drop the skill folders where your Copilot setup discovers skills (repo skills
directory / `.github`), or package and install individual skills via the
Copilot CLI. The SKILL.md format is portable across agentskills.io clients, so
the same folders work in other compatible agents.

## Adapt before commit

Templates use placeholders: `<proj>`/`<PROJ>` (project prefix), `<proto>`
(protocol), `<feat>`, `<blk>`. Handle names (`m_env`, `m_vsequencer`,
`m_<role>_seqr`, `vif`) are conventions — match them to your base env's actual
handles. All tool commands go through the team `dv` wrapper (`dv compile`,
`dv sim`, `dv cov`, `dv log first-error`) -- never raw `xrun`/`imc`/vManager;
vsif snippets are repo files the CI flow consumes.

## Integration with the copilot-dv-agents pack

This skill pack is aligned with (and subordinate to, where they overlap) the
team's `copilot-dv-agents` repo:

- **Law of the land**: `.github/copilot-instructions.md` (dv wrapper golden
  commands, never-weaken-checkers, evidence contract, moving-DUT rules) and the
  team `uvm-coding-standard` skill override anything here on conflict. The
  three law skills in this pack (`naming-conventions`, `phasing-check`,
  `deprecation-lint`) are the DETAIL layer under `uvm-coding-standard`.
- **Role split with the six agents**: the agents deliberately do NOT create or
  restructure environments, agents, scoreboards, or RAL models (dv-test-writer
  boundary; dv-checker-writer is additive-only). The 12 authoring skills here
  cover exactly that missing role -- the ENVIRONMENT ARCHITECT: use them in
  plain chat / by the human architect, or as the basis for a future
  `dv-env-architect` agent. They are not for dv-test-writer sessions.
- **Skill complements** (no duplication): `debug-strategy/references/playbooks`
  extends the team `debug-playbook` (X-prop, randomize, RAL, SVA-vacuity
  recipes); `uvm-coverage` (authoring) complements `coverage-closure`
  (closure policy); `verif-env-review` (environment audit) complements the
  `dv-reviewer` agent (pre-MR diff review) and the per-item
  `definition-of-done.md`.
- **Scripts are CI-side**: `triage_log.py` and `lint.py` run in Jenkins (or
  behind `dv log first-error` / `dv lint`); agents access tools and logs only
  through the `dv` wrapper.
- **Conventions adopted from the team pack**: `// VP-xxx` vplan references,
  stable unique check IDs (`SCBD_*`) as chkq-keyed API, nested config objects
  set once at test level, objections in tests and virtual sequences only,
  chkq negative-test registration for every new check, >=3-seed + zero-new-
  warning pass criterion.

## Clone lineage

All skills share one spine (from `uvm-test`): frontmatter with a deliberately
"pushy" trigger description, then Inputs → Procedure → Hard rules → Definition
of Done. To add a skill, copy the closest sibling, rewrite the description with
the right trigger verbs, and push deep material into `references/`.
