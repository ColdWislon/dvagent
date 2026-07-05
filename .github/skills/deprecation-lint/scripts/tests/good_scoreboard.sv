// Fixture: an independent scoreboard fed by monitors only (should PASS).
`uvm_analysis_imp_decl(_in)
`uvm_analysis_imp_decl(_out)

class good_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(good_scoreboard)

  uvm_analysis_imp_in  #(axi_item, good_scoreboard) imp_in;   // from INPUT monitor
  uvm_analysis_imp_out #(axi_item, good_scoreboard) imp_out;  // from OUTPUT monitor
  axi_item exp_q[$];

  function new(string name, uvm_component parent);
    super.new(name, parent);
    imp_in  = new("imp_in",  this);
    imp_out = new("imp_out", this);
  endfunction

  // observed input -> independent reference model -> expected
  virtual function void write_in(axi_item t);
    exp_q.push_back(ref_model::transform(t));   // spec-based, not the stimulus
  endfunction

  virtual function void write_out(axi_item t);
    axi_item exp;
    if (exp_q.size() == 0) begin
      `uvm_error("SCBD_UNEXPECTED", "unexpected output")
      return;
    end
    exp = exp_q.pop_front();
    if (!t.compare(exp)) `uvm_error("SCBD_DATA_CMP", "mismatch")
  endfunction

  virtual function void check_phase(uvm_phase phase);
    super.check_phase(phase);
    if (exp_q.size() != 0) `uvm_error("SCBD_RESIDUAL", "unmatched expected")
  endfunction
endclass
