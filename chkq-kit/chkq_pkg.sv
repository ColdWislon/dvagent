// ---------------------------------------------------------------------------
// chkq_pkg — checker-qualification (negative test) kit
//
// Purpose: tests in which a checker is EXPECTED to fire. Pass semantics are
// inverted per registered expectation: the test fails if the expected check
// does NOT fire (CHKQ_BLIND) or if any unexpected error fires.
//
// Rules of use (enforced by guards below + repo policy):
//   * Negative tests live under dv/tests/negative/ and extend chkq_base_test
//     (reparent chkq_base_test to your team base test as needed).
//   * They run with +CHKQ_ENABLE. Functional tests must NEVER set it.
//   * Coverage collection OFF for these runs; CI merge excludes chkq runs.
//   * RTL forcing only via chkq_injector (needs xrun ... -access +rwc).
// ---------------------------------------------------------------------------
`ifndef CHKQ_PKG_SV
`define CHKQ_PKG_SV
package chkq_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  // -------------------------------------------------------------------------
  // Expectation: catch a specific check ID, demote it, count it.
  // UVM_ERROR only by design — a check qualified this way must report via
  // uvm_error with a stable ID (team checker standard). UVM_FATALs are not
  // demotable safely and are not supported.
  // -------------------------------------------------------------------------
  class chkq_expectation extends uvm_report_catcher;
    string       check_id;
    int unsigned min_count = 1;
    int unsigned max_count = 0;   // 0 = no upper bound
    int unsigned matched   = 0;

    function new(string name = "chkq_expectation");
      super.new(name);
    endfunction

    virtual function action_e catch();
      if (get_severity() == UVM_ERROR && get_id() == check_id) begin
        matched++;
        set_severity(UVM_INFO);
        set_id({"CHKQ_CAUGHT_", check_id});
      end
      return THROW;
    endfunction

    function bit satisfied();
      return (matched >= min_count) &&
             (max_count == 0 || matched <= max_count);
    endfunction
  endclass

  // -------------------------------------------------------------------------
  // Injector: the ONLY sanctioned way to force DUT signals, gated on
  // +CHKQ_ENABLE so it is structurally unusable from functional tests.
  // -------------------------------------------------------------------------
  class chkq_injector extends uvm_object;
    `uvm_object_utils(chkq_injector)

    function new(string name = "chkq_injector");
      super.new(name);
    endfunction

    static function bit enabled();
      return $test$plusargs("CHKQ_ENABLE");
    endfunction

    // Force `path` to `value` for `hold`, then release. Blocking.
    task automatic force_for(string path, uvm_hdl_data_t value, time hold);
      if (!enabled())
        `uvm_fatal("CHKQ_GUARD",
          {"Injection attempted without +CHKQ_ENABLE: ", path})
      if (!uvm_hdl_check_path(path))
        `uvm_fatal("CHKQ_PATH",
          {"HDL path not found/forcible (compile with -access +rwc): ", path})
      void'(uvm_hdl_force(path, value));
      `uvm_info("CHKQ_INJECT",
        $sformatf("force %s = 'h%0h for %0t", path, value, hold), UVM_LOW)
      #hold;
      void'(uvm_hdl_release(path));
      `uvm_info("CHKQ_RELEASE", path, UVM_LOW)
    endtask

    // Single-shot deposit (for state corruption sampled once).
    task automatic deposit(string path, uvm_hdl_data_t value);
      if (!enabled())
        `uvm_fatal("CHKQ_GUARD",
          {"Injection attempted without +CHKQ_ENABLE: ", path})
      if (!uvm_hdl_check_path(path))
        `uvm_fatal("CHKQ_PATH",
          {"HDL path not found (compile with -access +rwc): ", path})
      void'(uvm_hdl_deposit(path, value));
      `uvm_info("CHKQ_DEPOSIT",
        $sformatf("deposit %s = 'h%0h", path, value), UVM_LOW)
    endtask
  endclass

  // -------------------------------------------------------------------------
  // Base negative test. Register expectations, run traffic, inject, and the
  // check_phase turns unmet expectations into CHKQ_BLIND errors.
  // NOTE: teams should reparent this to their own base test class.
  // -------------------------------------------------------------------------
  class chkq_base_test extends uvm_test;
    `uvm_component_utils(chkq_base_test)

    chkq_expectation expectations[$];
    chkq_injector    injector;

    function new(string name, uvm_component parent);
      super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if (!chkq_injector::enabled())
        `uvm_fatal("CHKQ_GUARD",
          "chkq negative tests require +CHKQ_ENABLE (and functional tests must never set it)")
      injector = chkq_injector::type_id::create("injector");
    endfunction

    // Declare that check `check_id` MUST fire between min_c and max_c times.
    function chkq_expectation expect_check(string check_id,
                                           int unsigned min_c = 1,
                                           int unsigned max_c = 0);
      chkq_expectation e = new({"exp_", check_id});
      e.check_id  = check_id;
      e.min_count = min_c;
      e.max_count = max_c;
      uvm_report_cb::add(null, e);
      expectations.push_back(e);
      return e;
    endfunction

    function void check_phase(uvm_phase phase);
      super.check_phase(phase);
      foreach (expectations[i]) begin
        if (!expectations[i].satisfied())
          `uvm_error("CHKQ_BLIND",
            $sformatf("Check '%s' did not fire as expected (matched=%0d, min=%0d, max=%0d) — checker may be vacuous or eroded",
              expectations[i].check_id, expectations[i].matched,
              expectations[i].min_count, expectations[i].max_count))
        else
          `uvm_info("CHKQ_OK",
            $sformatf("Check '%s' fired %0d time(s) as expected",
              expectations[i].check_id, expectations[i].matched), UVM_LOW)
      end
    endfunction
  endclass

endpackage
`endif
