// Fixture: an env wiring a driver's analysis port to the scoreboard (should FAIL).
class bad_env extends uvm_env;
  `uvm_component_utils(bad_env)
  axi_agent         m_master_agent;
  good_scoreboard   m_scoreboard;

  function new(string name, uvm_component parent); super.new(name, parent); endfunction

  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    // expected should come from a MONITOR, not the driver:
    m_master_agent.m_driver.ap.connect(m_scoreboard.imp_master); // indep.driver_to_sb (error)
  endfunction
endclass
