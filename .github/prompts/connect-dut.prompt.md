---
agent: dv-dut-integrator
description: 'Wire tb_top to the real DUT RTL from the port list'
argument-hint: '<ip>'
---
Connect the DUT for IP ${input:ip:ip name}: read `${input:ip}_verif/cfg/*.yaml`
for `dut.rtl_filelist` and `dut.module`, read that module's real port list,
and produce the port-mapping table (Gate 1) — STOP there for my approval
before editing any interface or tb_top file. Once approved, wire it and
prove with `make compile` against the real RTL (no stub note).
