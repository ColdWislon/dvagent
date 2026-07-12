// VP-UART-101 VP-UART-102
class uart_scoreboard extends uvm_scoreboard;
  virtual function void write_out(uart_item t);
    // PLACEHOLDER-CHECK: data compare per spec 4.2 (parity, framing)
  endfunction
endclass
