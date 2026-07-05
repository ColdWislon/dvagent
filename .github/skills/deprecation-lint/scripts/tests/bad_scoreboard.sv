// Fixture: a scoreboard that violates check-independence (should FAIL).
`include "burst_wr_seq.svh"                    // indep.sb_include_seq (error)

class bad_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(bad_scoreboard)

  uvm_analysis_imp #(axi_item, bad_scoreboard) imp;
  burst_wr_seq  m_ref_seq;                      // indep.sb_seq_handle (error)
  int           inject_pct;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    imp = new("imp", this);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    // pulling stimulus knobs to build "expected" -> tautological
    void'(uvm_config_db#(int)::get(this, "", "inject_pct", inject_pct)); // warn
  endfunction

  virtual function void write(axi_item t);
    // predict expected from the stimulus sequence -> wrong
    axi_item exp = burst_wr_seq::predict(t);    // indep.sb_seq_handle (error)
    if (!t.compare(exp)) `uvm_error(get_type_name(), "mismatch")
  endfunction
endclass
