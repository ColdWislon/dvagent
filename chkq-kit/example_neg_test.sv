// ---------------------------------------------------------------------------
// Example negative test: qualifies check ID "SCBD_DATA_CMP".
// Pattern: normal traffic + one RTL-side corruption via the injector +
// a registered expectation that the scoreboard catches exactly it.
// Lives under dv/tests/negative/, runs with (no coverage):
//   make run TEST=axi_scbd_data_neg_test PLUSARGS='+CHKQ_ENABLE' XRUN_OPTS='-access +rwc'
//   (wrapper: dv sim <ip> axi_scbd_data_neg_test --plusargs +CHKQ_ENABLE)
// ---------------------------------------------------------------------------
`include "chkq_paths.svh"   // central registry of forced paths (CHKQ_PATH_*)

class axi_scbd_data_neg_test extends chkq_base_test;   // or your chkq-reparented base
  `uvm_component_utils(axi_scbd_data_neg_test)

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  task run_phase(uvm_phase phase);
    axi_smoke_vseq vseq;
    phase.raise_objection(this);

    // 1. Expectation FIRST: the scoreboard data compare must fire >= 1 time.
    void'(expect_check("SCBD_DATA_CMP", .min_c(1)));

    // 2. Normal legal traffic — the checker must be exercised, not idle.
    vseq = axi_smoke_vseq::type_id::create("vseq");
    fork
      vseq.start(env.vsequencer);
    join_none

    // 3. Corrupt the DUT read path mid-traffic. The forced path comes from
    //    the central registry (chkq_paths.svh, CHKQ_PATH_<CHECK_ID>) — the
    //    single audit point when RTL is refactored. A literal path here is
    //    a review finding. Value + window are part of the qualification
    //    record.
    #2us;
    injector.force_for(CHKQ_PATH_SCBD_DATA_CMP, 'hDEAD_BEEF, 300ns);

    // 4. Let traffic drain; check_phase enforces the expectation.
    #5us;
    phase.drop_objection(this);
  endtask
endclass
