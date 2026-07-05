// Central registry of ALL hdl paths forced by chkq negative tests.
// One audit point after every RTL restructure: fix paths here, re-run
// dv/lists/chkq.list, done. Tests reference these localparams only —
// a literal path in a test file is a review finding.
// Naming: CHKQ_PATH_<CHECK_ID>.
`ifndef CHKQ_PATHS_SVH
`define CHKQ_PATHS_SVH
// localparam string CHKQ_PATH_SCBD_DATA_CMP = "tb_top.dut.u_rd_path.rdata_q";
`endif
