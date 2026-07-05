Fixture logs for triage_log.py self-test. Not real runs -- do not triage in CI.
- sb_mismatch_seed1/2.log : same bug, two seeds -> MUST produce one signature (x2)
- tb_fatal_vif.log        : tb_bug / config
- hang_timeout.log        : needs_waveform / hang (zero errors + watchdog)
- compile_err.log         : tb_bug / compile_elab (*E before time 0)
- false_pass.log          : dut_suspect + 2 flags (PASS banner with UVM_ERROR>0,
                            summary count mismatch)
