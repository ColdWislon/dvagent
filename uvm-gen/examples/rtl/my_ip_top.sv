// Example RTL top for my_ip - a stand-in DUT so the example environment can
// exercise the "switch from stub to real RTL" flow (wire the ports in
// tb/tb_top.sv, then flip sim/dut.f).
module my_ip_top #(
  parameter FIFO_DEPTH = 8
) (
  input  logic        clk,
  input  logic        rst_n,
  // 'ctrl' interface (matches the generated placeholder signals)
  input  logic        ctrl_valid,
  input  logic        ctrl_write,
  input  logic [31:0] ctrl_addr,
  input  logic [31:0] ctrl_data,
  output logic        ctrl_ready,
  // 'irq' interface (driven by the DUT; the irq agent is passive)
  output logic        irq_valid
);

`ifdef DATA_WIDTH
  localparam int unsigned DataWidth = `DATA_WIDTH;
`else
  localparam int unsigned DataWidth = 32;
`endif

  logic [$clog2(FIFO_DEPTH+1)-1:0] fill;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      fill      <= '0;
      irq_valid <= 1'b0;
    end
    else begin
      if (ctrl_valid && ctrl_write && fill < FIFO_DEPTH[$bits(fill)-1:0])
        fill <= fill + 1'b1;
      irq_valid <= (fill == FIFO_DEPTH[$bits(fill)-1:0]);
    end
  end

  assign ctrl_ready = (fill < FIFO_DEPTH[$bits(fill)-1:0]);

  initial $display("[my_ip_top] real RTL: FIFO_DEPTH=%0d DATA_WIDTH=%0d",
                   FIFO_DEPTH, DataWidth);

endmodule : my_ip_top
