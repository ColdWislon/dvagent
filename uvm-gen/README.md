# uvm-gen — UVM IP verification environment generator (Cadence Xcelium)

`uvm-gen` is a reusable command-line tool that generates a **complete,
immediately-compiling SystemVerilog/UVM verification environment** for an IP
from one YAML file: per-interface agents, env with scoreboard/coverage/virtual
sequencer/RAL hook, Cadence VIP hookups (APB / AHB / MIPI I3C), tests, tb_top,
and a full Xcelium build/run/regression flow (Makefile + `.f` filelists +
vManager `.vsif`), with multi-configuration tracking in `verif_matrix.yaml`.

Design goals, in order:

1. **Provable out of the box** — `make compile` elaborates cleanly and
   `make run TEST=<ip>_smoke_test` finishes with `UVM_ERROR : 0` on the
   freshly generated env (stub DUT, placeholder single-cycle protocol),
   before any `// TODO` is filled in.
2. **Never destroys your work** — re-running the generator only creates files
   that don't exist yet (see [Re-run semantics](#re-run-semantics)).
3. **Vertically reusable** — the generated env drops into an SoC environment
   unmodified (see [SoC reuse](#instantiating-the-env-inside-an-soc-env)).
4. **Multi-configuration first** — parameterizable IPs get one YAML, one vsif
   and one signature per configuration, and an auditable verification matrix.

Xcelium only: single-step `xrun` with the bundled UVM-1.2
(`-uvmhome CDNS-1.2`). No other simulators.

---

## Installation

```bash
pip install -r requirements.txt        # Jinja2 + PyYAML (Python 3.8+)
```

## Generating an environment

```bash
./uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force] [--dry-run]
```

Example, using the shipped sample IP:

```bash
./uvm_gen.py examples/my_ip.yaml -o ~/work
cd ~/work/my_ip_verif/sim
make compile                     # elab-only sanity (stub DUT)
make run TEST=my_ip_smoke_test   # reset + traffic, UVM_ERROR count 0
```

Generated layout:

```
<ip_name>_verif/
├─ cfg/<ip_name>.yaml        # copy of the input config (canonical home of configs)
├─ agents/<name>_agent/      # per custom interface: if, seq_item, sequencer,
│                            #   driver, monitor, cfg object, agent, base seq, pkg
├─ env/                      # env_cfg, env, scoreboard, per-interface coverage,
│                            #   virtual sequencer, RAL block+adapter, VIP wrappers
├─ seq_lib/                  # base + smoke virtual sequences
├─ tests/                    # <ip>_base_test, <ip>_smoke_test
├─ tb/                       # tb_top.sv + <dut>_stub.sv
├─ sim/                      # Makefile, dut.f, tb.f, vip_<proto>.f, <ip>_<cfg>.vsif,
│                            #   probe.tcl, scripts/cfg_tool.py
└─ verif_matrix.yaml         # append-only verification records
```

All code is `<ip_name>_`-prefixed, packaged, and free of testbench/hierarchy
references. Protocol specifics are compiling stubs with `// TODO` markers: the
placeholder protocol (a single-cycle `valid` pulse) gives the smoke test real
driver→monitor→scoreboard/coverage traffic until you replace it. Scoreboard
compare stubs carry `// PLACEHOLDER-CHECK:` markers and the coverage stubs
prompt for `// VP-xxx` vplan tags — the conventions the DV agent pack and its
cockpit key on (see below).

Every environment also gets **`GETTING_STARTED.md`** — the newcomer
walkthrough from first compile to first real task (and, when the agent pack
is staged, to the Copilot agent workflow).

## Configuration schema

```yaml
ip_name: my_ip                  # required; SV identifier, prefixes everything
config_name: default            # configuration identity (default: "default")
extends: base.yaml              # optional: deep-merge onto another YAML
                                #   (dicts merge recursively, this file wins;
                                #    lists/scalars replace)

dut:
  module: my_ip_top             # DUT module name (default: <ip_name>)
  rtl_filelist: ../rtl/dut.f    # RTL filelist; recorded into sim/dut.f
                                #   (may itself use -f includes)

agents:                         # custom (non-VIP) interfaces -> full UVM agent each
  - name: ctrl                  # SV identifier, unique
    mode: active                # active (default) | passive

vips:                           # Cadence VIP instances
  - protocol: apb               # apb | ahb | i3c
    name: apb0                  # SV identifier, unique
    role: master                # apb/ahb: master|slave|passive
  - protocol: i3c               #   i3c: controller|target|passive
    name: i3c0                  #   (legacy master/slave accepted for i3c)
    role: controller
    ibi_enable: true            # i3c only; In-Band Interrupts default

params:                         # RTL/DV parameters of THIS configuration
  DATA_WIDTH: 32                # scalar -> +define+DATA_WIDTH=32
  FIFO_DEPTH:
    value: 8
    style: defparam             # define (default) | defparam | env
    path: tb_top.dut.FIFO_DEPTH # defparam target (default: tb_top.dut.<NAME>)
```

Params flow three ways: `+define+`/`-defparam` xrun flags (compile),
`+PARAM_<name>=` plusargs into `<ip>_env_cfg` fields (so env behavior and
coverage adapt per configuration), and the config signature (below). Values
are int/bool/string; strings are limited to `[A-Za-z0-9_.+-]` so they survive
plusargs and hashing; `defparam` requires an int.

## Re-run semantics

The generator **never overwrites an existing file** — it only creates missing
ones. Consequences:

* Editing generated files is always safe; re-running `uvm_gen.py` changes
  nothing on an untouched env.
* Adding an agent/VIP to the YAML and re-running creates **just the new
  agent's files** (plus any missing collateral). Existing env files are left
  alone; the tool prints the exact hand-wiring checklist (env_cfg, env, pkg,
  scoreboard, vsequencer, smoke vseq, base test, tb_top, tb.f).
* Running with a new configuration YAML creates just that configuration's
  `cfg/` copy and `sim/<ip>_<config_name>.vsif`.
* `--force` regenerates everything — **except `verif_matrix.yaml`**, which is
  verification history, not generated code. Nothing is ever deleted.

## Build & run flow (sim/Makefile)

One `-f` per domain, never merged — design first, then DV
(`FILELISTS = -f dut.f -f tb.f [-f vip_<proto>.f ...]`; append site extras
with `make run FILELISTS+='-f soc_glue.f'`):

| Target | Purpose |
|---|---|
| `make compile` | elab-only sanity (`xrun -elaborate`) |
| `make run TEST=<name> [SEED=n] [CFG=...]` | interactive/debug run + matrix record |
| `make waves TEST=<name>` | run with `-access +rwc` + SHM probing (probe.tcl) |
| `make run ... PASSIVE=1` | flip all agents passive via `<ip>_env_cfg` (SoC readiness) |
| `make regress [CFG=...]` | launch the configuration's vsif via vManager |
| `make matrix` | verification summary from verif_matrix.yaml |
| `make clean` | remove simulation artifacts |

`sim/dut.f` starts on the generated DUT stub so everything is green
immediately; once you wire the DUT ports in `tb/tb_top.sv`, flip `dut.f` to
the real `rtl_filelist` (the path from the YAML is pre-filled, commented).

## Multi-configuration IPs

One YAML per configuration (e.g. `cfg/my_ip_small.yaml`,
`cfg/my_ip_large.yaml`), each carrying `config_name` + `params:` and typically
`extends:`-ing the shared base spec. Select at run time:

```bash
make run TEST=my_ip_smoke_test CFG=../cfg/my_ip_small.yaml
```

(`CFG` paths resolve relative to `sim/` or to the `*_verif` root.)

* **Signature banner** — every simulation prints `config_name`, the full
  param values and an FNV-1a hash of the param set (`[UVM_GEN_CFG]` lines),
  computed in-simulation from the values actually applied.
* **verif_matrix.yaml** — every `make run`/`make waves` (and therefore every
  vManager run) appends one record: config_name, param hash, test, seed,
  pass/fail + UVM error/fatal counts, date, git revision, coverage % when
  provided (`--coverage` hook in cfg_tool), log path, params.
* **`make matrix`** — prints configs × status (runs/pass/fail/coverage/last
  run/git/tests) for sign-off review; the YAML stays machine-queryable.
* Params only reach `<ip>_env_cfg` fields if they existed at generation time
  (the base YAML should declare the full param set); new params still reach
  the RTL via `+define+`/`-defparam` without regeneration.

## Cadence VIP support (APB, AHB, MIPI I3C)

Each `vips:` entry generates a config object + wrapper component
(`env/<ip>_<name>_vip.sv`), wired into env/vsequencer, with protocol defaults
(I3C: controller role, IBI enabled) you edit in one place.

* **`$CDN_VIP_ROOT`** locates the VIP installation. It is the single
  Makefile-level variable for the VIP path; if the configuration requests a
  VIP and it is unset, `make` fails immediately with a clear error. Wrapper
  installs therefore need exactly one edit (`export CDN_VIP_ROOT=...`).
* Per protocol, `sim/vip_<protocol>.f` is the one file referencing
  `$CDN_VIP_ROOT`: uncomment its `+define+<IP>_USE_CDN_<PROTO>_VIP` and VIP
  filelist lines once, per your VIP release.
* Until then the wrappers compile as placeholders, so a fresh env builds and
  runs without the VIP installed — VIP-release-specific class names live only
  in the wrapper files' `` `ifdef `` blocks (fill from the pure-UVM example
  shipped with your VIP).

## Regression: vsif + vManager

`sim/<ip>_<config_name>.vsif` is generated per configuration in vManager
format: one `session` (named `<ip>_<config_name>`, `top_dir`, `output_mode`),
a `group` per test category, each `test` with its `run_script`, `count` and
`sv_seed : random` — the smoke test pre-populated and commented placeholders
showing the pattern.

Every `run_script` goes through `make run`, so vManager and interactive runs
share **one source of truth** for the xrun invocation, and each run records
itself in `verif_matrix.yaml`; pass/fail is the run script's exit status
(non-zero on UVM_ERROR/UVM_FATAL/missing summary). Launch:

```bash
make regress CFG=../cfg/my_ip_small.yaml
# == UVM_GEN_SIM_DIR=$PWD vmanager -execcmd "launch my_ip_small.vsif"
```

Adapt `REGRESS_CMD` in `sim/Makefile` for your site (e.g.
`vmanager -server host:port -execcmd "launch ..."`). Runs point `XMLIBDIR`
into vManager's per-run scratch dir so parallel compiles never collide.

## GitHub Copilot DV agent pack integration

When uvm-gen runs from a checkout of its home repository (or is pointed at a
pack with `--copilot-pack PATH` / `copilot: <path>` in the YAML), it stages
the team's Copilot agent pack into the generated environment so the env is
**agent-ready on day one**:

| Staged | Content |
|---|---|
| `.github/` | the full pack: 7 `dv-*` agents, 13 prompts (incl. `/start-here` onboarding), 30 skills, instructions — plus the pack's `USERGUIDE.md` |
| `.github/instructions/uvm-gen-env.instructions.md` | **rendered bridge**: maps the pack's `dv` golden commands onto this env's make flow (verdicts ↔ exit status + banner + `verif_matrix.yaml`, log triage via the pack's `triage_log.py`) |
| `docs/CLAUDE.md` | per-IP agent context, **pre-filled from the generated architecture** (agents read it before any work) |
| `docs/vplan.md` | vplan skeleton in the team format (traceability contract; `/generate-vplan` fills it) |
| `docs/methodology/definition-of-done.md` | the DoD the reviewer audits against |
| `dv/tests/negative/` | chkq checker-qualification kit — staged, not compiled (activation checklist in `dv/lists/chkq.list`; commented block ready in `sim/tb.f`) |
| `dv/cov/exclusion_requests.md`, `dv/lists/`, `dv/status/` | exclusion queue, sanity/chkq regression lists (smoke pre-seeded), cockpit/session sidecar dir |
| `cockpit.ini`, `external-vplan-kit/` | verif-cockpit config, PDF-vision vplan drafting kit |

Control: default is auto (staged when a pack is discoverable, silently
skipped otherwise); `copilot: false` in the YAML or `--no-copilot` disables;
`copilot: true` makes a missing pack an error; a path selects the pack
explicitly. All copies obey the normal re-run policy (never overwritten;
`--force` regenerates). If `<ip>_verif/` is a subdirectory of a larger repo,
move `.github/` + `cockpit.ini` to the repo root — VS Code loads the pack
from there.

## Getting started (newcomers)

Generated envs are self-onboarding: open `<ip>_verif/GETTING_STARTED.md`.
It walks a new engineer through prerequisites, the first
compile/smoke/waves/matrix commands (with the expected output), a map of the
environment, the ordered list of first real tasks (TODO → real protocol →
DUT hookup → PLACEHOLDER-CHECKs → coverage → RAL → VIP), and — when the pack
is staged — the Copilot agent workflow, starting with `/start-here` in
Copilot chat (a read-only guided first session added to the pack by this
integration).

## Instantiating the env inside an SoC env

The generated env is SoC-ready by construction:

* self-contained `<ip>_`-prefixed packages; no `tb_top`/hierarchy references
  inside agents/env/sequences (a unit test enforces this);
* ONE `<ip>_env_cfg` retrieved via `uvm_config_db` — the SoC env sets it from
  above; **all virtual interfaces live in the config object**;
* per-agent `is_active`: passive agents build no driver/sequencer while
  monitor, scoreboard and coverage stay live (`set_all_passive()` helper);
* RAL: `<ip>_reg_block` instantiates as a child of the SoC register model
  with an `add_submap()` base-address offset; adapter/predictor/map-sequencer
  wiring only happens when `ral_env_owns_bus` is set (IP standalone).

```systemverilog
import my_ip_env_pkg::*;

class soc_env extends uvm_env;
  my_ip_env     ip0_env;
  my_ip_env_cfg ip0_cfg;

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ip0_cfg = my_ip_env_cfg::type_id::create("ip0_cfg");
    ip0_cfg.set_all_passive();          // RTL drives the buses at SoC level
    ip0_cfg.ral_env_owns_bus = 0;       // the SoC owns the register bus
    ip0_cfg.ctrl_cfg.vif = soc_tb_ctrl_vif;   // from the SoC testbench
    ip0_cfg.regmodel = soc_regs.ip0;    // my_ip_reg_block child @ SoC offset
    uvm_config_db #(my_ip_env_cfg)::set(this, "ip0_env", "cfg", ip0_cfg);
    ip0_env = my_ip_env::type_id::create("ip0_env", this);
  endfunction
endclass
```

Compile collateral: reuse `sim/tb.f` minus its final `tb_top` line. The smoke
test demonstrates the switch without SoC code:
`make run TEST=my_ip_smoke_test PASSIVE=1` runs the same env/sequence with
every agent passive, still `UVM_ERROR : 0`.

## Acceptance checklist

| Criterion | How to check |
|---|---|
| Fresh env elaborates cleanly (DUT stubbed) | `make compile` |
| Smoke test completes, UVM_ERROR 0 | `make run TEST=<ip>_smoke_test` |
| Re-run changes nothing (unless additions / `--force`) | re-run `uvm_gen.py`; pytest `test_rerun_policy.py` |
| All agents flip passive via cfg only | `make run TEST=<ip>_smoke_test PASSIVE=1` |
| vsif syntax-checks and launches smoke | `make regress` |
| Two config YAMLs → two banners + two matrix entries | `make run CFG=../cfg/a.yaml` / `CFG=../cfg/b.yaml`, then `make matrix` |

## Developing uvm-gen

```bash
pip install pytest
cd uvm-gen && pytest            # generator unit + generated-code sanity tests
```

Templates live in `uvm_gen/templates/` (`.sv.j2` Jinja2 files — no SV inside
Python). `sim/scripts/cfg_tool.py` is copied verbatim and kept IP-agnostic;
a test pins its param-hash implementation to the generator's.
