# uvm-gen — UVM IP verification environment generator for Cadence Xcelium

`uvm-gen` is a reusable command-line tool that generates a complete,
immediately-compilable SystemVerilog/UVM IP verification environment from one
YAML file: custom agents, Cadence VIP wrappers, env with scoreboard/coverage/
virtual-sequencer/RAL hooks, tests, testbench top, an xrun/Xcelium build flow,
a vManager regression (`.vsif`), multi-configuration verification tracking,
and a GitHub Copilot agentic kit that can drive the flow from testbench
creation to sign-off.

* **Simulator**: Cadence Xcelium only — single-step `xrun`, bundled UVM-1.2
  (`-uvmhome CDNS-1.2`).
* **Implementation**: Python 3, Jinja2 templates (`uvmgen/templates/*.j2` —
  all SV/Makefile content lives in template files, not strings), PyYAML.

```bash
pip install -r requirements.txt
python3 uvm_gen.py examples/my_ip.yaml -o ~/work
cd ~/work/my_ip_verif/sim
make compile                        # elaborates cleanly before any TODO is filled
make run TEST=my_ip_smoke_test      # reset + a few transactions, UVM_ERROR : 0
```

---

## CLI

```
uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force] [--dry-run] [--version]
```

| Option | Meaning |
|---|---|
| `config.yaml` | IP configuration (supports `extends:`) |
| `-o OUTPUT_DIR` | where `<ip_name>_verif/` is created (default `.`) |
| `--force` | overwrite **everything** (destroys local edits — see re-run policy) |
| `--dry-run` | show what would be created without writing |

### Re-run policy (never overwrite)

The generator **never overwrites an existing file** — it only creates files
that don't exist yet:

* Add an agent/VIP to the YAML and re-run → only the new agent/VIP files (and
  the new per-agent coverage subscriber) appear. Files that would need the new
  agent wired in (`env/*.sv`, `sim/tb.f`, `tb/*.sv`, ...) are reported as
  `[stale]` with a hint; wire them by hand — your edits are never touched.
* Add a new configuration YAML and re-run with it → only `cfg/<file>.yaml`
  and its `sim/<ip>_<config_name>.vsif` appear.
* `--force` regenerates every file from the templates (including
  `verif_matrix.yaml` — keep the env under git).

Re-running with an unchanged YAML changes **zero bytes** (verified by test).

---

## Configuration YAML

```yaml
ip_name: my_ip                  # prefix for every generated class/package/file

dut:
  module: my_ip_top             # instantiated in tb_top (ports left as TODOs)
  rtl_filelist: ../rtl/dut.f    # design filelist; relative to THIS file, $VARS ok.
                                # May itself use -f includes. While it does not
                                # resolve, the flow uses a generated DUT stub.

config_name: default            # identifies this configuration (multi-config)

params:                         # RTL parameters/defines for this configuration
  DATA_W: 32                    #   -> xrun flags (+define+NAME=VALUE, or
  FIFO_DEPTH: 16                #      -defparam <tb>.dut.NAME=VALUE with
                                #      param_style: defparam)
                                #   -> string map + typed mirrors (prm_data_w,
                                #      ...) in <ip>_env_cfg
# defines:                      # extra +define+ macros (never defparam'd)
#   EN_FEATURE_X: 1
# param_style: define           # 'define' (default) | 'defparam'
# dv_scaffold: true             # true (default): emit the docs/ + dv/ DV
                                #   methodology tree (see below); false: lean
                                #   standalone env without it

agents:                         # custom (non-VIP) interfaces
  - name: ctrl
    mode: active                # active | passive (default active)
  - name: stat
    mode: passive

vips:                           # Cadence VIP instances
  - protocol: apb               # apb | ahb | i3c
    name: apb_cfg
    role: master                # see roles below; 'monitor' => passive wrapper
```

### `extends:` — multi-configuration IPs without duplication

One YAML per configuration; shared spec lives in a base file:

```yaml
# cfg/my_ip_small.yaml
extends: my_ip.yaml             # resolved relative to this file
config_name: small
params:
  DATA_W: 16                    # deep-merge: FIFO_DEPTH inherited, DATA_W wins
```

Merge semantics: dictionaries merge recursively with the extending file
winning; lists (`agents:`, `vips:`) replace wholesale; chains
(`a extends b extends c`) and cycles are handled/detected. The generator
copies the whole chain into `cfg/` (rewriting `extends:` to the sibling
basename), so the generated env is self-contained.

### VIP protocols, roles, defaults

| Protocol | Roles | Seeded knobs (edit in `vip/<name>_vip/<ip>_<name>_vip_cfg.sv`) |
|---|---|---|
| `apb` | master, slave, monitor | `addr_width=32`, `data_width=32` |
| `ahb` | master, slave, monitor | `addr_width=32`, `data_width=32` |
| `i3c` | controller, target, monitor (aliases: master→controller, slave→target) | `ibi_enable=1`, `hot_join_enable=0`, `static_addr=7'h50`, `i3c_only_bus=1` |

Knob values can be overridden directly in the YAML entry
(e.g. `ibi_enable: false`). `role: monitor` seeds the wrapper passive.

---

## The generated environment

```
<ip_name>_verif/
├─ cfg/<config>.yaml           # copies of the input config (whole extends chain)
├─ agents/<name>_agent/        # per custom interface: interface, seq_item,
│                              # sequencer, driver, monitor, agent cfg, agent,
│                              # base sequence, package (compiling stubs with
│                              # TODO(protocol) markers)
├─ vip/<name>_vip/             # Cadence VIP wrapper: cfg + agent shell + pkg
├─ env/                        # env_cfg, env, scoreboard stub, per-interface
│                              # coverage subscribers, virtual sequencer,
│                              # RAL stub (reg_block + adapter + predictor wiring)
├─ seq_lib/                    # base + smoke virtual sequences, package
├─ tests/                      # <ip>_base_test, <ip>_smoke_test, package
├─ tb/                         # <ip>_tb_top (clock/reset gen, interfaces, DUT
│                              # instantiation with TODO ports) + DUT stub
├─ sim/                        # Makefile, tb.f, vip_<proto>.f, <ip>[_<cfg>].vsif,
│                              # scripts/ (cfg2args, record_result, matrix_report,
│                              # waves.tcl)
├─ docs/                       # CLAUDE.md (per-IP context) + vplan.md skeletons  ┐ DV methodology
├─ dv/                         # tests/negative/ (chkq kit + IP base/example +    │ scaffolding —
│                              # HDL-path registry + chkq.f), lists/{chkq,sanity},│ omitted when
│                              # cov/exclusion_requests.md, status/               ┘ dv_scaffold: false
├─ .github/                    # Copilot kit: copilot-instructions.md + prompts/
├─ Makefile                    # thin wrapper around sim/Makefile
├─ verif_matrix.yaml           # verification tracking (auto-appended)
└─ README.md, .gitignore
```

### DV methodology scaffolding (`dv_scaffold`, default on)

By default each env also carries the collateral the GitHub Copilot DV pack
expects, so a generated env drops straight into that workflow:

* `docs/CLAUDE.md` — per-IP context skeleton (read before working on the IP);
* `docs/vplan.md` — verification-plan table skeleton (`VP-<IP>-xxx` items that
  tests, bins, and checks trace back to);
* `dv/tests/negative/` — the checker-qualification (chkq) kit: the generic
  `chkq_pkg`, an `<ip>_chkq_base_test` reparented onto `<ip>_base_test`, a
  compiling `<ip>_example_neg_test`, the central `chkq_paths.svh` HDL-path
  registry, and an opt-in `chkq.f` filelist (functional builds never see it —
  add it with `EXTRA_FILELISTS=` and run with `+CHKQ_ENABLE -access +rwc`);
* `dv/lists/{chkq,sanity}.list`, `dv/cov/exclusion_requests.md`, `dv/status/`
  (session/verdict sidecars the local dashboard renders).

Set `dv_scaffold: false` in the config YAML for a lean standalone env (core
UVM env + sim flow + `.github` phase kit only, none of the `dv/` or `docs/`
tree). The switch is honored by the never-overwrite policy like everything
else.

Everything is prefixed `<ip_name>_` and the env/agent/seq code contains **no
testbench references and no hierarchical config_db lookups** (enforced by the
test suite) — that's what makes it SoC-reusable unmodified.

### Freshly generated = runnable

The generated stubs implement a generic valid/data handshake so that, before
any TODO is filled in:

* `make compile` elaborates cleanly (a `+define+<IP>_USE_DUT_STUB`-guarded
  stub module stands in while `dut.rtl_filelist` doesn't resolve — the
  Makefile switches to the real RTL automatically once it exists);
* `make run TEST=<ip>_smoke_test` finishes with `UVM_ERROR : 0`: the smoke
  virtual sequence runs each active agent's base sequence, monitors observe
  the traffic, the scoreboard counts it, coverage samples.

---

## Build & run flow (sim/Makefile)

```bash
make compile                                  # xrun -elaborate sanity
make run TEST=my_ip_smoke_test [SEED=7]       # single run (SEED=random ok)
make run TEST=x CFG=cfg/my_ip_small.yaml      # pick a configuration
make waves TEST=x                             # -access +rwc, SHM probing (waves.shm)
make regress                                  # vManager launch of the CFG's vsif
make matrix                                   # config vs. status summary
make clean
```

* **Filelists**: separate `.f` per domain, each passed as its own `-f`
  (never merged): the DUT filelist from the YAML, `vip_<protocol>.f` per
  requested VIP protocol, and the generated `tb.f` (packages, interfaces,
  tb_top in compile order, anchored on `$<IP>_VERIF_HOME`). The ordered list
  lives in the `FILELISTS` variable (design first, then DV); append extras
  without touching rules: `make run EXTRA_FILELISTS=soc_glue.f` or
  `FILELISTS+=...`.
* **xrun**: single step, `-64bit -sv -uvmhome CDNS-1.2 -timescale 1ns/1ps`;
  add flags with `XRUN_OPTS=...`.
* **Cadence VIPs**: located via `$CDN_VIP_ROOT`. If the active config
  requests VIPs and the variable is unset, `make` fails with a clear error
  before launching anything. The VIP install path is referenced only from
  `sim/vip_<protocol>.f` — one file to edit per protocol. The generated
  wrapper classes are compile-clean shells with `TODO(vip)` markers and
  example (release-dependent) Cadence class names; wiring the real VIP is a
  contained, documented edit.

## Multi-configuration verification tracking

* Configs are selected **at run time** (`CFG=cfg/<file>.yaml`);
  `sim/scripts/cfg2args.py` (same merge/hash logic as the generator) turns
  the YAML into xrun flags: `+define+`/`-defparam` for the RTL params plus
  `+<IP>_CFG_NAME/+<IP>_CFG_HASH/+<IP>_PARAM=` plusargs for the env.
* **Every simulation prints a config signature banner** (`CFG_BANNER`):
  config_name, full parameter values, and an 8-hex-char hash of the param
  set — two different config YAMLs give two distinct banners.
* **Every `make run` appends a record** to `verif_matrix.yaml` — config_name,
  param hash, params, test, seed (actual seed extracted from the log),
  pass/fail, UVM error counts, date, git revision, coverage % when present in
  the log. Since vManager runs go through `make run`, regressions land there
  automatically. The file is human-auditable YAML and machine-queryable;
  concurrent appends are flock-protected.
* `make matrix` prints the configs × verification status table
  (`matrix_report.py --yaml` for tooling).

## Regression: vsif + vManager

* One generated vsif **per configuration**: `sim/<ip>.vsif` for the default
  config, `sim/<ip>_<config_name>.vsif` otherwise, with the session named
  `<ip>_<config_name>` (`top_dir`, `output_mode`), a `group` per test
  category, and `test` entries carrying `run_script`, `scan_script`,
  `count`, `seed : random;`. The smoke test is pre-populated; commented
  placeholder groups show the pattern for new tests.
* Single source of truth: each `run_script` is
  `make -C $ENV(PWD) run TEST=<t> CFG=<cfg> SEED=$ATTR(seed)` — vManager runs
  and local runs share the exact xrun invocation.
* Launch: `make regress` runs `vmanager -execcmd "launch <vsif>"` from `sim/`
  (adapt inside the Makefile if your site starts vManager differently).

## Vertical reuse — dropping the env into an SoC

The env's only external contract is one `<ip>_env_cfg` object retrieved via
`uvm_config_db` — all agent/VIP sub-configs and **all virtual interfaces**
live inside it:

```systemverilog
// SoC env build_phase
my_ip_env_cfg ip_cfg = my_ip_env_cfg::type_id::create("ip_cfg");
ip_cfg.set_agent_activity("all", UVM_PASSIVE); // RTL drives the buses; monitors,
                                               // scoreboard, coverage stay live
ip_cfg.env_owns_bus = 0;                       // no RAL adapter/predictor wiring
ip_cfg.ctrl_cfg.vif = soc_ctrl_vif;            // SoC-level signals
uvm_config_db#(my_ip_env_cfg)::set(this, "m_my_ip_env", "cfg", ip_cfg);
m_my_ip_env = my_ip_env::type_id::create("m_my_ip_env", this);
```

* **Passive flip without source edits**: drivers/sequencers are simply not
  constructed for passive agents; virtual sequences null-check sequencer
  handles. Standalone demonstration:
  `make run TEST=<ip>_smoke_test XRUN_OPTS=+<IP>_PASSIVE=all`.
* **RAL**: `<ip>_reg_block` is instantiable as a child of the SoC register
  model with a configurable base offset
  (`soc_map.add_submap(ip_regs.default_map, 'h4000_0000)`); set
  `ip_cfg.regmodel = ip_regs` and the env skips building its own. Adapter and
  predictor are wired only while `env_owns_bus == 1`.
* **Compilation**: `export <IP>_VERIF_HOME=<env root>` and add
  `-f $<IP>_VERIF_HOME/sim/tb.f` to the SoC build (exclude the `tb/` entries
  when the SoC has its own top).

## Copilot agentic verification kit

Each generated env carries `.github/copilot-instructions.md` (layout, naming
prefix, `<ip>_env_cfg`/config_db pattern, is_active rules, multi-config
scheme, exact commands, never-overwrite policy, per-phase definition of done)
plus one prompt per phase in `.github/prompts/`, templated with the IP's real
names/paths/commands. The prompts chain — each states the previous phase's
done-criterion as its precondition — so an agent can run the whole flow:

1. `connect-dut.prompt.md` — fill tb_top port TODOs; prove `make compile`.
2. `implement-agents.prompt.md` — fill protocol TODOs; prove the smoke test.
3. `write-tests.prompt.md` — grow seq_lib/tests; register in the vsif.
4. `triage-regression.prompt.md` — parse logs/matrix, classify, fix, re-run.
5. `coverage-closure.prompt.md` — close holes per configuration.
6. `verif-closure.prompt.md` — all configs CLEAN in `verif_matrix.yaml`,
   closure summary.

## Acceptance criteria → how they're covered

| Criterion | Where |
|---|---|
| Fresh env compiles/elaborates before TODOs | DUT stub + compiling protocol stubs; `make compile` |
| Smoke test runs, UVM_ERROR 0 | generic handshake stubs drive/observe real traffic |
| Re-run changes nothing without new YAML entries / `--force` | write policy + `tests/test_generate.py` (byte-identical re-run) |
| All agents passive purely via env_cfg | `+<IP>_PASSIVE=all` plusarg → `set_agent_activity`; agents skip driver/sequencer construction |
| vsif syntax + smoke launch | vManager-format session/group/test; `make regress` |
| Two config YAMLs → two banners + two matrix entries | runtime plusargs from cfg2args; `tests/test_scripts.py::test_two_configs_two_matrix_entries` |
| Copilot kit with real names, working commands | templated prompts; `tests/test_generate.py::test_copilot_kit_uses_real_names` |
| README | this file + a per-env README |

## Development

```bash
pip install -r requirements.txt
python3 -m pytest tests/            # 30 tests: config merge/hash/validation,
                                    # generation, re-run policy, scripts
```

Layout: `uvm_gen.py` (entry) → `uvmgen/` (`config.py`, `generate.py`,
`cli.py`, `vip.py`) → `uvmgen/templates/` (all Jinja2 sources, grouped by
destination: `agent/`, `vip/`, `env/`, `seq_lib/`, `tests/`, `tb/`, `sim/`,
`root/`, `copilot/`).
