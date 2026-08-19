*FIRST LINE IS A COMMENT

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u

.SUBCKT bias_l1_pinv_dec_4
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 4
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u
.ENDS bias_l1_pinv_dec_4

.SUBCKT bias_l1_rom_output_buffer
+ in_0 in_1 in_2 in_3 in_4 in_5 in_6 in_7 in_8 in_9 in_10 in_11 in_12
+ in_13 in_14 in_15 in_16 in_17 in_18 in_19 in_20 in_21 in_22 in_23
+ out_0 out_1 out_2 out_3 out_4 out_5 out_6 out_7 out_8 out_9 out_10
+ out_11 out_12 out_13 out_14 out_15 out_16 out_17 out_18 out_19 out_20
+ out_21 out_22 out_23 vdd gnd
* INPUT : in_0 
* INPUT : in_1 
* INPUT : in_2 
* INPUT : in_3 
* INPUT : in_4 
* INPUT : in_5 
* INPUT : in_6 
* INPUT : in_7 
* INPUT : in_8 
* INPUT : in_9 
* INPUT : in_10 
* INPUT : in_11 
* INPUT : in_12 
* INPUT : in_13 
* INPUT : in_14 
* INPUT : in_15 
* INPUT : in_16 
* INPUT : in_17 
* INPUT : in_18 
* INPUT : in_19 
* INPUT : in_20 
* INPUT : in_21 
* INPUT : in_22 
* INPUT : in_23 
* OUTPUT: out_0 
* OUTPUT: out_1 
* OUTPUT: out_2 
* OUTPUT: out_3 
* OUTPUT: out_4 
* OUTPUT: out_5 
* OUTPUT: out_6 
* OUTPUT: out_7 
* OUTPUT: out_8 
* OUTPUT: out_9 
* OUTPUT: out_10 
* OUTPUT: out_11 
* OUTPUT: out_12 
* OUTPUT: out_13 
* OUTPUT: out_14 
* OUTPUT: out_15 
* OUTPUT: out_16 
* OUTPUT: out_17 
* OUTPUT: out_18 
* OUTPUT: out_19 
* OUTPUT: out_20 
* OUTPUT: out_21 
* OUTPUT: out_22 
* OUTPUT: out_23 
* POWER : vdd 
* GROUND: gnd 
* rows: 24 Buffer size of: 4
Xwld0
+ in_0 out_0 vdd gnd
+ bias_l1_pinv_dec_4
Xwld1
+ in_1 out_1 vdd gnd
+ bias_l1_pinv_dec_4
Xwld2
+ in_2 out_2 vdd gnd
+ bias_l1_pinv_dec_4
Xwld3
+ in_3 out_3 vdd gnd
+ bias_l1_pinv_dec_4
Xwld4
+ in_4 out_4 vdd gnd
+ bias_l1_pinv_dec_4
Xwld5
+ in_5 out_5 vdd gnd
+ bias_l1_pinv_dec_4
Xwld6
+ in_6 out_6 vdd gnd
+ bias_l1_pinv_dec_4
Xwld7
+ in_7 out_7 vdd gnd
+ bias_l1_pinv_dec_4
Xwld8
+ in_8 out_8 vdd gnd
+ bias_l1_pinv_dec_4
Xwld9
+ in_9 out_9 vdd gnd
+ bias_l1_pinv_dec_4
Xwld10
+ in_10 out_10 vdd gnd
+ bias_l1_pinv_dec_4
Xwld11
+ in_11 out_11 vdd gnd
+ bias_l1_pinv_dec_4
Xwld12
+ in_12 out_12 vdd gnd
+ bias_l1_pinv_dec_4
Xwld13
+ in_13 out_13 vdd gnd
+ bias_l1_pinv_dec_4
Xwld14
+ in_14 out_14 vdd gnd
+ bias_l1_pinv_dec_4
Xwld15
+ in_15 out_15 vdd gnd
+ bias_l1_pinv_dec_4
Xwld16
+ in_16 out_16 vdd gnd
+ bias_l1_pinv_dec_4
Xwld17
+ in_17 out_17 vdd gnd
+ bias_l1_pinv_dec_4
Xwld18
+ in_18 out_18 vdd gnd
+ bias_l1_pinv_dec_4
Xwld19
+ in_19 out_19 vdd gnd
+ bias_l1_pinv_dec_4
Xwld20
+ in_20 out_20 vdd gnd
+ bias_l1_pinv_dec_4
Xwld21
+ in_21 out_21 vdd gnd
+ bias_l1_pinv_dec_4
Xwld22
+ in_22 out_22 vdd gnd
+ bias_l1_pinv_dec_4
Xwld23
+ in_23 out_23 vdd gnd
+ bias_l1_pinv_dec_4
.ENDS bias_l1_rom_output_buffer

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=1.26 l=0.15 pd=2.82 ps=2.82 as=0.47u ad=0.47u

.SUBCKT bias_l1_pinv_dec_0
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 3
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=1.26 l=0.15 pd=2.82 ps=2.82 as=0.47u ad=0.47u
.ENDS bias_l1_pinv_dec_0

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=7.0 l=0.15 pd=14.30 ps=14.30 as=2.62u ad=2.62u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u

.SUBCKT bias_l1_pinv_dec_1
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 12
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=7.0 l=0.15 pd=14.30 ps=14.30 as=2.62u ad=2.62u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u
.ENDS bias_l1_pinv_dec_1

.SUBCKT bias_l1_pbuf_dec
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 12
Xbuf_inv1
+ A zb_int vdd gnd
+ bias_l1_pinv_dec_0
Xbuf_inv2
+ zb_int Z vdd gnd
+ bias_l1_pinv_dec_1
.ENDS bias_l1_pbuf_dec

.SUBCKT bias_l1_rom_row_decode_wordline_buffer
+ in_0 in_1 in_2 in_3 in_4 in_5 in_6 in_7 out_0 out_1 out_2 out_3 out_4
+ out_5 out_6 out_7 vdd gnd
* INPUT : in_0 
* INPUT : in_1 
* INPUT : in_2 
* INPUT : in_3 
* INPUT : in_4 
* INPUT : in_5 
* INPUT : in_6 
* INPUT : in_7 
* OUTPUT: out_0 
* OUTPUT: out_1 
* OUTPUT: out_2 
* OUTPUT: out_3 
* OUTPUT: out_4 
* OUTPUT: out_5 
* OUTPUT: out_6 
* OUTPUT: out_7 
* POWER : vdd 
* GROUND: gnd 
* rows: 8 Buffer size of: 12
Xwld0
+ in_0 out_0 vdd gnd
+ bias_l1_pbuf_dec
Xwld1
+ in_1 out_1 vdd gnd
+ bias_l1_pbuf_dec
Xwld2
+ in_2 out_2 vdd gnd
+ bias_l1_pbuf_dec
Xwld3
+ in_3 out_3 vdd gnd
+ bias_l1_pbuf_dec
Xwld4
+ in_4 out_4 vdd gnd
+ bias_l1_pbuf_dec
Xwld5
+ in_5 out_5 vdd gnd
+ bias_l1_pbuf_dec
Xwld6
+ in_6 out_6 vdd gnd
+ bias_l1_pbuf_dec
Xwld7
+ in_7 out_7 vdd gnd
+ bias_l1_pbuf_dec
.ENDS bias_l1_rom_row_decode_wordline_buffer
* Copyright 2020 The SkyWater PDK Authors
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     https://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
* SPDX-License-Identifier: Apache-2.0

* NGSPICE file created from sky130_fd_bd_sram__openram_sp_nand2_dec.ext - technology: EFS8A


* Top level circuit sky130_fd_bd_sram__openram_sp_nand2_dec
.subckt sky130_fd_bd_sram__openram_sp_nand2_dec A B Z VDD GND

X1001 Z B VDD VDD sky130_fd_pr__pfet_01v8 W=1.12 L=0.15
X1002 VDD A Z VDD sky130_fd_pr__pfet_01v8 W=1.12 L=0.15
X1000 Z A a_n722_276# GND sky130_fd_pr__nfet_01v8 W=0.74 L=0.15
X1003 a_n722_276# B GND GND sky130_fd_pr__nfet_01v8 W=0.74 L=0.15
.ends


* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u

.SUBCKT bias_l1_inv_array_mod
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 1.9600000000000002
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u
.ENDS bias_l1_inv_array_mod

.SUBCKT bias_l1_rom_address_control_buf
+ A_in A_out Abar_out clk vdd gnd
* INPUT : A_in 
* INOUT : A_out 
* OUTPUT: Abar_out 
* INPUT : clk 
* POWER : vdd 
* GROUND: gnd 
XXinvAbar
+ A_in Abar_internal vdd gnd
+ bias_l1_inv_array_mod
XXnand_addr
+ clk Abar_internal A_out vdd gnd
+ sky130_fd_bd_sram__openram_sp_nand2_dec
XXnand_addr_bar
+ clk A_out Abar_out vdd gnd
+ sky130_fd_bd_sram__openram_sp_nand2_dec
.ENDS bias_l1_rom_address_control_buf

.SUBCKT bias_l1_rom_address_control_array
+ A0_in A1_in A2_in A0_out A1_out A2_out Abar0_out Abar1_out Abar2_out
+ clk vdd gnd
* INPUT : A0_in 
* INPUT : A1_in 
* INPUT : A2_in 
* OUTPUT: A0_out 
* OUTPUT: A1_out 
* OUTPUT: A2_out 
* OUTPUT: Abar0_out 
* OUTPUT: Abar1_out 
* OUTPUT: Abar2_out 
* INPUT : clk 
* POWER : vdd 
* GROUND: gnd 
XXaddr_buf_0
+ A0_in A0_out Abar0_out clk vdd gnd
+ bias_l1_rom_address_control_buf
XXaddr_buf_1
+ A1_in A1_out Abar1_out clk vdd gnd
+ bias_l1_rom_address_control_buf
XXaddr_buf_2
+ A2_in A2_out Abar2_out clk vdd gnd
+ bias_l1_rom_address_control_buf
.ENDS bias_l1_rom_address_control_array

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=0.42 l=0.15 pd=1.14 ps=1.14 as=0.16u ad=0.16u

.SUBCKT bias_l1_precharge_cell
+ vdd gate bitline
* POWER : vdd 
* INPUT : gate 
* OUTPUT: bitline 
Xprecharge_pmos bitline gate vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=0.42 l=0.15 pd=1.14 ps=1.14 as=0.16u ad=0.16u
.ENDS bias_l1_precharge_cell

.SUBCKT bias_l1_rom_precharge_array_0
+ pre_bl0_out pre_bl1_out pre_bl2_out pre_bl3_out pre_bl4_out
+ pre_bl5_out pre_bl6_out pre_bl7_out gate vdd
* OUTPUT: pre_bl0_out 
* OUTPUT: pre_bl1_out 
* OUTPUT: pre_bl2_out 
* OUTPUT: pre_bl3_out 
* OUTPUT: pre_bl4_out 
* OUTPUT: pre_bl5_out 
* OUTPUT: pre_bl6_out 
* OUTPUT: pre_bl7_out 
* INPUT : gate 
* POWER : vdd 
Xpmos_c0
+ vdd gate pre_bl0_out
+ bias_l1_precharge_cell
Xpmos_c1
+ vdd gate pre_bl1_out
+ bias_l1_precharge_cell
Xpmos_c2
+ vdd gate pre_bl2_out
+ bias_l1_precharge_cell
Xpmos_c3
+ vdd gate pre_bl3_out
+ bias_l1_precharge_cell
Xpmos_c4
+ vdd gate pre_bl4_out
+ bias_l1_precharge_cell
Xpmos_c5
+ vdd gate pre_bl5_out
+ bias_l1_precharge_cell
Xpmos_c6
+ vdd gate pre_bl6_out
+ bias_l1_precharge_cell
Xpmos_c7
+ vdd gate pre_bl7_out
+ bias_l1_precharge_cell
.ENDS bias_l1_rom_precharge_array_0

* spice ptx X{0} {1} sky130_fd_pr__special_nfet_01v8 m=1 w=0.36 l=0.15 pd=1.02 ps=1.02 as=0.14u ad=0.14u

.SUBCKT bias_l1_rom_base_zero_cell
+ bl wl gnd
* INOUT : bl 
* INPUT : wl 
* GROUND: gnd 
Xbias_l1_rom_base_zero_cell_nmos bl wl bl gnd sky130_fd_pr__special_nfet_01v8 m=1 w=0.36 l=0.15 pd=1.02 ps=1.02 as=0.14u ad=0.14u
.ENDS bias_l1_rom_base_zero_cell

.SUBCKT bias_l1_rom_base_one_cell
+ bl_h bl_l wl gnd
* INOUT : bl_h 
* INOUT : bl_l 
* INPUT : wl 
* GROUND: gnd 
Xbias_l1_rom_base_one_cell_nmos bl_h wl bl_l gnd sky130_fd_pr__special_nfet_01v8 m=1 w=0.36 l=0.15 pd=1.02 ps=1.02 as=0.14u ad=0.14u
.ENDS bias_l1_rom_base_one_cell

.SUBCKT bias_l1_rom_row_decode_array
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 bl_0_4 bl_0_5 bl_0_6 bl_0_7 wl_0_0 wl_0_1
+ wl_0_2 wl_0_3 wl_0_4 wl_0_5 precharge vdd gnd
* OUTPUT: bl_0_0 
* OUTPUT: bl_0_1 
* OUTPUT: bl_0_2 
* OUTPUT: bl_0_3 
* OUTPUT: bl_0_4 
* OUTPUT: bl_0_5 
* OUTPUT: bl_0_6 
* OUTPUT: bl_0_7 
* INPUT : wl_0_0 
* INPUT : wl_0_1 
* INPUT : wl_0_2 
* INPUT : wl_0_3 
* INPUT : wl_0_4 
* INPUT : wl_0_5 
* INPUT : precharge 
* POWER : vdd 
* GROUND: gnd 
Xbit_r0_c0
+ bl_int_0_0 bl_0_0 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c1
+ bl_int_0_1 bl_0_1 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c2
+ bl_int_0_2 bl_0_2 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c3
+ bl_int_0_3 bl_0_3 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c4
+ bl_0_4 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c5
+ bl_0_5 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c6
+ bl_0_6 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c7
+ bl_0_7 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c0
+ bl_int_0_0 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c1
+ bl_int_0_1 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c2
+ bl_int_0_2 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c3
+ bl_int_0_3 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c4
+ bl_int_1_4 bl_0_4 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c5
+ bl_int_1_5 bl_0_5 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c6
+ bl_int_1_6 bl_0_6 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c7
+ bl_int_1_7 bl_0_7 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c0
+ bl_int_2_0 bl_int_0_0 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c1
+ bl_int_2_1 bl_int_0_1 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c2
+ bl_int_0_2 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c3
+ bl_int_0_3 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c4
+ bl_int_2_4 bl_int_1_4 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c5
+ bl_int_2_5 bl_int_1_5 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c6
+ bl_int_1_6 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c7
+ bl_int_1_7 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c0
+ bl_int_2_0 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c1
+ bl_int_2_1 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c2
+ bl_int_3_2 bl_int_0_2 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c3
+ bl_int_3_3 bl_int_0_3 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c4
+ bl_int_2_4 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c5
+ bl_int_2_5 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c6
+ bl_int_3_6 bl_int_1_6 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c7
+ bl_int_3_7 bl_int_1_7 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c0
+ bl_int_4_0 bl_int_2_0 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c1
+ bl_int_2_1 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c2
+ bl_int_4_2 bl_int_3_2 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c3
+ bl_int_3_3 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c4
+ bl_int_4_4 bl_int_2_4 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c5
+ bl_int_2_5 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c6
+ bl_int_4_6 bl_int_3_6 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c7
+ bl_int_3_7 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c0
+ bl_int_4_0 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c1
+ bl_int_5_1 bl_int_2_1 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c2
+ bl_int_4_2 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c3
+ bl_int_5_3 bl_int_3_3 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c4
+ bl_int_4_4 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c5
+ bl_int_5_5 bl_int_2_5 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c6
+ bl_int_4_6 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c7
+ bl_int_5_7 bl_int_3_7 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c0
+ gnd bl_int_4_0 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c1
+ gnd bl_int_5_1 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c2
+ gnd bl_int_4_2 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c3
+ gnd bl_int_5_3 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c4
+ gnd bl_int_4_4 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c5
+ gnd bl_int_5_5 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c6
+ gnd bl_int_4_6 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c7
+ gnd bl_int_5_7 precharge gnd
+ bias_l1_rom_base_one_cell
Xbitcell_array_precharge
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 bl_0_4 bl_0_5 bl_0_6 bl_0_7 precharge vdd
+ bias_l1_rom_precharge_array_0
.ENDS bias_l1_rom_row_decode_array

.SUBCKT bias_l1_rom_row_decode
+ A0 A1 A2 wl_0 wl_1 wl_2 wl_3 wl_4 wl_5 wl_6 wl_7 precharge clk vdd gnd
* INPUT : A0 
* INPUT : A1 
* INPUT : A2 
* OUTPUT: wl_0 
* OUTPUT: wl_1 
* OUTPUT: wl_2 
* OUTPUT: wl_3 
* OUTPUT: wl_4 
* OUTPUT: wl_5 
* OUTPUT: wl_6 
* OUTPUT: wl_7 
* INPUT : precharge 
* INPUT : clk 
* POWER : vdd 
* GROUND: gnd 
Xdecode_array_inst
+ wl_int0 wl_int1 wl_int2 wl_int3 wl_int4 wl_int5 wl_int6 wl_int7
+ Ab_int_2 A_int_2 Ab_int_1 A_int_1 Ab_int_0 A_int_0 precharge vdd gnd
+ bias_l1_rom_row_decode_array
Xpre_control_array
+ A0 A1 A2 A_int_0 A_int_1 A_int_2 Ab_int_0 Ab_int_1 Ab_int_2 clk vdd
+ gnd
+ bias_l1_rom_address_control_array
Xrom_wordline_driver
+ wl_int0 wl_int1 wl_int2 wl_int3 wl_int4 wl_int5 wl_int6 wl_int7 wl_0
+ wl_1 wl_2 wl_3 wl_4 wl_5 wl_6 wl_7 vdd gnd
+ bias_l1_rom_row_decode_wordline_buffer
.ENDS bias_l1_rom_row_decode

.SUBCKT bias_l1_rom_precharge_array
+ pre_bl0_out pre_bl1_out pre_bl2_out pre_bl3_out pre_bl4_out
+ pre_bl5_out pre_bl6_out pre_bl7_out pre_bl8_out pre_bl9_out
+ pre_bl10_out pre_bl11_out pre_bl12_out pre_bl13_out pre_bl14_out
+ pre_bl15_out pre_bl16_out pre_bl17_out pre_bl18_out pre_bl19_out
+ pre_bl20_out pre_bl21_out pre_bl22_out pre_bl23_out pre_bl24_out
+ pre_bl25_out pre_bl26_out pre_bl27_out pre_bl28_out pre_bl29_out
+ pre_bl30_out pre_bl31_out pre_bl32_out pre_bl33_out pre_bl34_out
+ pre_bl35_out pre_bl36_out pre_bl37_out pre_bl38_out pre_bl39_out
+ pre_bl40_out pre_bl41_out pre_bl42_out pre_bl43_out pre_bl44_out
+ pre_bl45_out pre_bl46_out pre_bl47_out pre_bl48_out pre_bl49_out
+ pre_bl50_out pre_bl51_out pre_bl52_out pre_bl53_out pre_bl54_out
+ pre_bl55_out pre_bl56_out pre_bl57_out pre_bl58_out pre_bl59_out
+ pre_bl60_out pre_bl61_out pre_bl62_out pre_bl63_out pre_bl64_out
+ pre_bl65_out pre_bl66_out pre_bl67_out pre_bl68_out pre_bl69_out
+ pre_bl70_out pre_bl71_out pre_bl72_out pre_bl73_out pre_bl74_out
+ pre_bl75_out pre_bl76_out pre_bl77_out pre_bl78_out pre_bl79_out
+ pre_bl80_out pre_bl81_out pre_bl82_out pre_bl83_out pre_bl84_out
+ pre_bl85_out pre_bl86_out pre_bl87_out pre_bl88_out pre_bl89_out
+ pre_bl90_out pre_bl91_out pre_bl92_out pre_bl93_out pre_bl94_out
+ pre_bl95_out gate vdd
* OUTPUT: pre_bl0_out 
* OUTPUT: pre_bl1_out 
* OUTPUT: pre_bl2_out 
* OUTPUT: pre_bl3_out 
* OUTPUT: pre_bl4_out 
* OUTPUT: pre_bl5_out 
* OUTPUT: pre_bl6_out 
* OUTPUT: pre_bl7_out 
* OUTPUT: pre_bl8_out 
* OUTPUT: pre_bl9_out 
* OUTPUT: pre_bl10_out 
* OUTPUT: pre_bl11_out 
* OUTPUT: pre_bl12_out 
* OUTPUT: pre_bl13_out 
* OUTPUT: pre_bl14_out 
* OUTPUT: pre_bl15_out 
* OUTPUT: pre_bl16_out 
* OUTPUT: pre_bl17_out 
* OUTPUT: pre_bl18_out 
* OUTPUT: pre_bl19_out 
* OUTPUT: pre_bl20_out 
* OUTPUT: pre_bl21_out 
* OUTPUT: pre_bl22_out 
* OUTPUT: pre_bl23_out 
* OUTPUT: pre_bl24_out 
* OUTPUT: pre_bl25_out 
* OUTPUT: pre_bl26_out 
* OUTPUT: pre_bl27_out 
* OUTPUT: pre_bl28_out 
* OUTPUT: pre_bl29_out 
* OUTPUT: pre_bl30_out 
* OUTPUT: pre_bl31_out 
* OUTPUT: pre_bl32_out 
* OUTPUT: pre_bl33_out 
* OUTPUT: pre_bl34_out 
* OUTPUT: pre_bl35_out 
* OUTPUT: pre_bl36_out 
* OUTPUT: pre_bl37_out 
* OUTPUT: pre_bl38_out 
* OUTPUT: pre_bl39_out 
* OUTPUT: pre_bl40_out 
* OUTPUT: pre_bl41_out 
* OUTPUT: pre_bl42_out 
* OUTPUT: pre_bl43_out 
* OUTPUT: pre_bl44_out 
* OUTPUT: pre_bl45_out 
* OUTPUT: pre_bl46_out 
* OUTPUT: pre_bl47_out 
* OUTPUT: pre_bl48_out 
* OUTPUT: pre_bl49_out 
* OUTPUT: pre_bl50_out 
* OUTPUT: pre_bl51_out 
* OUTPUT: pre_bl52_out 
* OUTPUT: pre_bl53_out 
* OUTPUT: pre_bl54_out 
* OUTPUT: pre_bl55_out 
* OUTPUT: pre_bl56_out 
* OUTPUT: pre_bl57_out 
* OUTPUT: pre_bl58_out 
* OUTPUT: pre_bl59_out 
* OUTPUT: pre_bl60_out 
* OUTPUT: pre_bl61_out 
* OUTPUT: pre_bl62_out 
* OUTPUT: pre_bl63_out 
* OUTPUT: pre_bl64_out 
* OUTPUT: pre_bl65_out 
* OUTPUT: pre_bl66_out 
* OUTPUT: pre_bl67_out 
* OUTPUT: pre_bl68_out 
* OUTPUT: pre_bl69_out 
* OUTPUT: pre_bl70_out 
* OUTPUT: pre_bl71_out 
* OUTPUT: pre_bl72_out 
* OUTPUT: pre_bl73_out 
* OUTPUT: pre_bl74_out 
* OUTPUT: pre_bl75_out 
* OUTPUT: pre_bl76_out 
* OUTPUT: pre_bl77_out 
* OUTPUT: pre_bl78_out 
* OUTPUT: pre_bl79_out 
* OUTPUT: pre_bl80_out 
* OUTPUT: pre_bl81_out 
* OUTPUT: pre_bl82_out 
* OUTPUT: pre_bl83_out 
* OUTPUT: pre_bl84_out 
* OUTPUT: pre_bl85_out 
* OUTPUT: pre_bl86_out 
* OUTPUT: pre_bl87_out 
* OUTPUT: pre_bl88_out 
* OUTPUT: pre_bl89_out 
* OUTPUT: pre_bl90_out 
* OUTPUT: pre_bl91_out 
* OUTPUT: pre_bl92_out 
* OUTPUT: pre_bl93_out 
* OUTPUT: pre_bl94_out 
* OUTPUT: pre_bl95_out 
* INPUT : gate 
* POWER : vdd 
Xpmos_c0
+ vdd gate pre_bl0_out
+ bias_l1_precharge_cell
Xpmos_c1
+ vdd gate pre_bl1_out
+ bias_l1_precharge_cell
Xpmos_c2
+ vdd gate pre_bl2_out
+ bias_l1_precharge_cell
Xpmos_c3
+ vdd gate pre_bl3_out
+ bias_l1_precharge_cell
Xpmos_c4
+ vdd gate pre_bl4_out
+ bias_l1_precharge_cell
Xpmos_c5
+ vdd gate pre_bl5_out
+ bias_l1_precharge_cell
Xpmos_c6
+ vdd gate pre_bl6_out
+ bias_l1_precharge_cell
Xpmos_c7
+ vdd gate pre_bl7_out
+ bias_l1_precharge_cell
Xpmos_c8
+ vdd gate pre_bl8_out
+ bias_l1_precharge_cell
Xpmos_c9
+ vdd gate pre_bl9_out
+ bias_l1_precharge_cell
Xpmos_c10
+ vdd gate pre_bl10_out
+ bias_l1_precharge_cell
Xpmos_c11
+ vdd gate pre_bl11_out
+ bias_l1_precharge_cell
Xpmos_c12
+ vdd gate pre_bl12_out
+ bias_l1_precharge_cell
Xpmos_c13
+ vdd gate pre_bl13_out
+ bias_l1_precharge_cell
Xpmos_c14
+ vdd gate pre_bl14_out
+ bias_l1_precharge_cell
Xpmos_c15
+ vdd gate pre_bl15_out
+ bias_l1_precharge_cell
Xpmos_c16
+ vdd gate pre_bl16_out
+ bias_l1_precharge_cell
Xpmos_c17
+ vdd gate pre_bl17_out
+ bias_l1_precharge_cell
Xpmos_c18
+ vdd gate pre_bl18_out
+ bias_l1_precharge_cell
Xpmos_c19
+ vdd gate pre_bl19_out
+ bias_l1_precharge_cell
Xpmos_c20
+ vdd gate pre_bl20_out
+ bias_l1_precharge_cell
Xpmos_c21
+ vdd gate pre_bl21_out
+ bias_l1_precharge_cell
Xpmos_c22
+ vdd gate pre_bl22_out
+ bias_l1_precharge_cell
Xpmos_c23
+ vdd gate pre_bl23_out
+ bias_l1_precharge_cell
Xpmos_c24
+ vdd gate pre_bl24_out
+ bias_l1_precharge_cell
Xpmos_c25
+ vdd gate pre_bl25_out
+ bias_l1_precharge_cell
Xpmos_c26
+ vdd gate pre_bl26_out
+ bias_l1_precharge_cell
Xpmos_c27
+ vdd gate pre_bl27_out
+ bias_l1_precharge_cell
Xpmos_c28
+ vdd gate pre_bl28_out
+ bias_l1_precharge_cell
Xpmos_c29
+ vdd gate pre_bl29_out
+ bias_l1_precharge_cell
Xpmos_c30
+ vdd gate pre_bl30_out
+ bias_l1_precharge_cell
Xpmos_c31
+ vdd gate pre_bl31_out
+ bias_l1_precharge_cell
Xpmos_c32
+ vdd gate pre_bl32_out
+ bias_l1_precharge_cell
Xpmos_c33
+ vdd gate pre_bl33_out
+ bias_l1_precharge_cell
Xpmos_c34
+ vdd gate pre_bl34_out
+ bias_l1_precharge_cell
Xpmos_c35
+ vdd gate pre_bl35_out
+ bias_l1_precharge_cell
Xpmos_c36
+ vdd gate pre_bl36_out
+ bias_l1_precharge_cell
Xpmos_c37
+ vdd gate pre_bl37_out
+ bias_l1_precharge_cell
Xpmos_c38
+ vdd gate pre_bl38_out
+ bias_l1_precharge_cell
Xpmos_c39
+ vdd gate pre_bl39_out
+ bias_l1_precharge_cell
Xpmos_c40
+ vdd gate pre_bl40_out
+ bias_l1_precharge_cell
Xpmos_c41
+ vdd gate pre_bl41_out
+ bias_l1_precharge_cell
Xpmos_c42
+ vdd gate pre_bl42_out
+ bias_l1_precharge_cell
Xpmos_c43
+ vdd gate pre_bl43_out
+ bias_l1_precharge_cell
Xpmos_c44
+ vdd gate pre_bl44_out
+ bias_l1_precharge_cell
Xpmos_c45
+ vdd gate pre_bl45_out
+ bias_l1_precharge_cell
Xpmos_c46
+ vdd gate pre_bl46_out
+ bias_l1_precharge_cell
Xpmos_c47
+ vdd gate pre_bl47_out
+ bias_l1_precharge_cell
Xpmos_c48
+ vdd gate pre_bl48_out
+ bias_l1_precharge_cell
Xpmos_c49
+ vdd gate pre_bl49_out
+ bias_l1_precharge_cell
Xpmos_c50
+ vdd gate pre_bl50_out
+ bias_l1_precharge_cell
Xpmos_c51
+ vdd gate pre_bl51_out
+ bias_l1_precharge_cell
Xpmos_c52
+ vdd gate pre_bl52_out
+ bias_l1_precharge_cell
Xpmos_c53
+ vdd gate pre_bl53_out
+ bias_l1_precharge_cell
Xpmos_c54
+ vdd gate pre_bl54_out
+ bias_l1_precharge_cell
Xpmos_c55
+ vdd gate pre_bl55_out
+ bias_l1_precharge_cell
Xpmos_c56
+ vdd gate pre_bl56_out
+ bias_l1_precharge_cell
Xpmos_c57
+ vdd gate pre_bl57_out
+ bias_l1_precharge_cell
Xpmos_c58
+ vdd gate pre_bl58_out
+ bias_l1_precharge_cell
Xpmos_c59
+ vdd gate pre_bl59_out
+ bias_l1_precharge_cell
Xpmos_c60
+ vdd gate pre_bl60_out
+ bias_l1_precharge_cell
Xpmos_c61
+ vdd gate pre_bl61_out
+ bias_l1_precharge_cell
Xpmos_c62
+ vdd gate pre_bl62_out
+ bias_l1_precharge_cell
Xpmos_c63
+ vdd gate pre_bl63_out
+ bias_l1_precharge_cell
Xpmos_c64
+ vdd gate pre_bl64_out
+ bias_l1_precharge_cell
Xpmos_c65
+ vdd gate pre_bl65_out
+ bias_l1_precharge_cell
Xpmos_c66
+ vdd gate pre_bl66_out
+ bias_l1_precharge_cell
Xpmos_c67
+ vdd gate pre_bl67_out
+ bias_l1_precharge_cell
Xpmos_c68
+ vdd gate pre_bl68_out
+ bias_l1_precharge_cell
Xpmos_c69
+ vdd gate pre_bl69_out
+ bias_l1_precharge_cell
Xpmos_c70
+ vdd gate pre_bl70_out
+ bias_l1_precharge_cell
Xpmos_c71
+ vdd gate pre_bl71_out
+ bias_l1_precharge_cell
Xpmos_c72
+ vdd gate pre_bl72_out
+ bias_l1_precharge_cell
Xpmos_c73
+ vdd gate pre_bl73_out
+ bias_l1_precharge_cell
Xpmos_c74
+ vdd gate pre_bl74_out
+ bias_l1_precharge_cell
Xpmos_c75
+ vdd gate pre_bl75_out
+ bias_l1_precharge_cell
Xpmos_c76
+ vdd gate pre_bl76_out
+ bias_l1_precharge_cell
Xpmos_c77
+ vdd gate pre_bl77_out
+ bias_l1_precharge_cell
Xpmos_c78
+ vdd gate pre_bl78_out
+ bias_l1_precharge_cell
Xpmos_c79
+ vdd gate pre_bl79_out
+ bias_l1_precharge_cell
Xpmos_c80
+ vdd gate pre_bl80_out
+ bias_l1_precharge_cell
Xpmos_c81
+ vdd gate pre_bl81_out
+ bias_l1_precharge_cell
Xpmos_c82
+ vdd gate pre_bl82_out
+ bias_l1_precharge_cell
Xpmos_c83
+ vdd gate pre_bl83_out
+ bias_l1_precharge_cell
Xpmos_c84
+ vdd gate pre_bl84_out
+ bias_l1_precharge_cell
Xpmos_c85
+ vdd gate pre_bl85_out
+ bias_l1_precharge_cell
Xpmos_c86
+ vdd gate pre_bl86_out
+ bias_l1_precharge_cell
Xpmos_c87
+ vdd gate pre_bl87_out
+ bias_l1_precharge_cell
Xpmos_c88
+ vdd gate pre_bl88_out
+ bias_l1_precharge_cell
Xpmos_c89
+ vdd gate pre_bl89_out
+ bias_l1_precharge_cell
Xpmos_c90
+ vdd gate pre_bl90_out
+ bias_l1_precharge_cell
Xpmos_c91
+ vdd gate pre_bl91_out
+ bias_l1_precharge_cell
Xpmos_c92
+ vdd gate pre_bl92_out
+ bias_l1_precharge_cell
Xpmos_c93
+ vdd gate pre_bl93_out
+ bias_l1_precharge_cell
Xpmos_c94
+ vdd gate pre_bl94_out
+ bias_l1_precharge_cell
Xpmos_c95
+ vdd gate pre_bl95_out
+ bias_l1_precharge_cell
.ENDS bias_l1_rom_precharge_array

.SUBCKT bias_l1_rom_base_array
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 bl_0_4 bl_0_5 bl_0_6 bl_0_7 bl_0_8 bl_0_9
+ bl_0_10 bl_0_11 bl_0_12 bl_0_13 bl_0_14 bl_0_15 bl_0_16 bl_0_17
+ bl_0_18 bl_0_19 bl_0_20 bl_0_21 bl_0_22 bl_0_23 bl_0_24 bl_0_25
+ bl_0_26 bl_0_27 bl_0_28 bl_0_29 bl_0_30 bl_0_31 bl_0_32 bl_0_33
+ bl_0_34 bl_0_35 bl_0_36 bl_0_37 bl_0_38 bl_0_39 bl_0_40 bl_0_41
+ bl_0_42 bl_0_43 bl_0_44 bl_0_45 bl_0_46 bl_0_47 bl_0_48 bl_0_49
+ bl_0_50 bl_0_51 bl_0_52 bl_0_53 bl_0_54 bl_0_55 bl_0_56 bl_0_57
+ bl_0_58 bl_0_59 bl_0_60 bl_0_61 bl_0_62 bl_0_63 bl_0_64 bl_0_65
+ bl_0_66 bl_0_67 bl_0_68 bl_0_69 bl_0_70 bl_0_71 bl_0_72 bl_0_73
+ bl_0_74 bl_0_75 bl_0_76 bl_0_77 bl_0_78 bl_0_79 bl_0_80 bl_0_81
+ bl_0_82 bl_0_83 bl_0_84 bl_0_85 bl_0_86 bl_0_87 bl_0_88 bl_0_89
+ bl_0_90 bl_0_91 bl_0_92 bl_0_93 bl_0_94 bl_0_95 wl_0_0 wl_0_1 wl_0_2
+ wl_0_3 wl_0_4 wl_0_5 wl_0_6 wl_0_7 precharge vdd gnd
* OUTPUT: bl_0_0 
* OUTPUT: bl_0_1 
* OUTPUT: bl_0_2 
* OUTPUT: bl_0_3 
* OUTPUT: bl_0_4 
* OUTPUT: bl_0_5 
* OUTPUT: bl_0_6 
* OUTPUT: bl_0_7 
* OUTPUT: bl_0_8 
* OUTPUT: bl_0_9 
* OUTPUT: bl_0_10 
* OUTPUT: bl_0_11 
* OUTPUT: bl_0_12 
* OUTPUT: bl_0_13 
* OUTPUT: bl_0_14 
* OUTPUT: bl_0_15 
* OUTPUT: bl_0_16 
* OUTPUT: bl_0_17 
* OUTPUT: bl_0_18 
* OUTPUT: bl_0_19 
* OUTPUT: bl_0_20 
* OUTPUT: bl_0_21 
* OUTPUT: bl_0_22 
* OUTPUT: bl_0_23 
* OUTPUT: bl_0_24 
* OUTPUT: bl_0_25 
* OUTPUT: bl_0_26 
* OUTPUT: bl_0_27 
* OUTPUT: bl_0_28 
* OUTPUT: bl_0_29 
* OUTPUT: bl_0_30 
* OUTPUT: bl_0_31 
* OUTPUT: bl_0_32 
* OUTPUT: bl_0_33 
* OUTPUT: bl_0_34 
* OUTPUT: bl_0_35 
* OUTPUT: bl_0_36 
* OUTPUT: bl_0_37 
* OUTPUT: bl_0_38 
* OUTPUT: bl_0_39 
* OUTPUT: bl_0_40 
* OUTPUT: bl_0_41 
* OUTPUT: bl_0_42 
* OUTPUT: bl_0_43 
* OUTPUT: bl_0_44 
* OUTPUT: bl_0_45 
* OUTPUT: bl_0_46 
* OUTPUT: bl_0_47 
* OUTPUT: bl_0_48 
* OUTPUT: bl_0_49 
* OUTPUT: bl_0_50 
* OUTPUT: bl_0_51 
* OUTPUT: bl_0_52 
* OUTPUT: bl_0_53 
* OUTPUT: bl_0_54 
* OUTPUT: bl_0_55 
* OUTPUT: bl_0_56 
* OUTPUT: bl_0_57 
* OUTPUT: bl_0_58 
* OUTPUT: bl_0_59 
* OUTPUT: bl_0_60 
* OUTPUT: bl_0_61 
* OUTPUT: bl_0_62 
* OUTPUT: bl_0_63 
* OUTPUT: bl_0_64 
* OUTPUT: bl_0_65 
* OUTPUT: bl_0_66 
* OUTPUT: bl_0_67 
* OUTPUT: bl_0_68 
* OUTPUT: bl_0_69 
* OUTPUT: bl_0_70 
* OUTPUT: bl_0_71 
* OUTPUT: bl_0_72 
* OUTPUT: bl_0_73 
* OUTPUT: bl_0_74 
* OUTPUT: bl_0_75 
* OUTPUT: bl_0_76 
* OUTPUT: bl_0_77 
* OUTPUT: bl_0_78 
* OUTPUT: bl_0_79 
* OUTPUT: bl_0_80 
* OUTPUT: bl_0_81 
* OUTPUT: bl_0_82 
* OUTPUT: bl_0_83 
* OUTPUT: bl_0_84 
* OUTPUT: bl_0_85 
* OUTPUT: bl_0_86 
* OUTPUT: bl_0_87 
* OUTPUT: bl_0_88 
* OUTPUT: bl_0_89 
* OUTPUT: bl_0_90 
* OUTPUT: bl_0_91 
* OUTPUT: bl_0_92 
* OUTPUT: bl_0_93 
* OUTPUT: bl_0_94 
* OUTPUT: bl_0_95 
* INPUT : wl_0_0 
* INPUT : wl_0_1 
* INPUT : wl_0_2 
* INPUT : wl_0_3 
* INPUT : wl_0_4 
* INPUT : wl_0_5 
* INPUT : wl_0_6 
* INPUT : wl_0_7 
* INPUT : precharge 
* POWER : vdd 
* GROUND: gnd 
Xbit_r0_c0
+ bl_0_0 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c1
+ bl_int_0_1 bl_0_1 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c2
+ bl_0_2 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c3
+ bl_int_0_3 bl_0_3 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c4
+ bl_0_4 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c5
+ bl_int_0_5 bl_0_5 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c6
+ bl_0_6 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c7
+ bl_int_0_7 bl_0_7 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c8
+ bl_0_8 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c9
+ bl_int_0_9 bl_0_9 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c10
+ bl_0_10 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c11
+ bl_int_0_11 bl_0_11 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c12
+ bl_0_12 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c13
+ bl_int_0_13 bl_0_13 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c14
+ bl_0_14 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c15
+ bl_int_0_15 bl_0_15 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c16
+ bl_0_16 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c17
+ bl_int_0_17 bl_0_17 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c18
+ bl_0_18 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c19
+ bl_int_0_19 bl_0_19 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c20
+ bl_0_20 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c21
+ bl_int_0_21 bl_0_21 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c22
+ bl_0_22 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c23
+ bl_int_0_23 bl_0_23 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c24
+ bl_0_24 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c25
+ bl_int_0_25 bl_0_25 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c26
+ bl_0_26 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c27
+ bl_int_0_27 bl_0_27 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c28
+ bl_0_28 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c29
+ bl_int_0_29 bl_0_29 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c30
+ bl_0_30 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c31
+ bl_int_0_31 bl_0_31 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c32
+ bl_0_32 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c33
+ bl_int_0_33 bl_0_33 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c34
+ bl_0_34 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c35
+ bl_int_0_35 bl_0_35 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c36
+ bl_0_36 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c37
+ bl_int_0_37 bl_0_37 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c38
+ bl_0_38 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c39
+ bl_int_0_39 bl_0_39 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c40
+ bl_0_40 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c41
+ bl_int_0_41 bl_0_41 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c42
+ bl_0_42 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c43
+ bl_int_0_43 bl_0_43 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c44
+ bl_0_44 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c45
+ bl_int_0_45 bl_0_45 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c46
+ bl_0_46 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c47
+ bl_int_0_47 bl_0_47 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c48
+ bl_0_48 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c49
+ bl_int_0_49 bl_0_49 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c50
+ bl_0_50 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c51
+ bl_int_0_51 bl_0_51 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c52
+ bl_0_52 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c53
+ bl_int_0_53 bl_0_53 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c54
+ bl_0_54 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c55
+ bl_int_0_55 bl_0_55 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c56
+ bl_0_56 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c57
+ bl_int_0_57 bl_0_57 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c58
+ bl_0_58 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c59
+ bl_int_0_59 bl_0_59 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c60
+ bl_0_60 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c61
+ bl_int_0_61 bl_0_61 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c62
+ bl_int_0_62 bl_0_62 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c63
+ bl_int_0_63 bl_0_63 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c64
+ bl_int_0_64 bl_0_64 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c65
+ bl_int_0_65 bl_0_65 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c66
+ bl_0_66 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c67
+ bl_0_67 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c68
+ bl_int_0_68 bl_0_68 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c69
+ bl_0_69 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c70
+ bl_0_70 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c71
+ bl_0_71 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c72
+ bl_int_0_72 bl_0_72 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c73
+ bl_int_0_73 bl_0_73 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c74
+ bl_0_74 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c75
+ bl_0_75 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c76
+ bl_0_76 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c77
+ bl_int_0_77 bl_0_77 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c78
+ bl_int_0_78 bl_0_78 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c79
+ bl_0_79 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c80
+ bl_int_0_80 bl_0_80 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c81
+ bl_0_81 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c82
+ bl_int_0_82 bl_0_82 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c83
+ bl_0_83 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c84
+ bl_int_0_84 bl_0_84 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c85
+ bl_int_0_85 bl_0_85 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c86
+ bl_int_0_86 bl_0_86 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c87
+ bl_0_87 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c88
+ bl_int_0_88 bl_0_88 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c89
+ bl_0_89 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c90
+ bl_0_90 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c91
+ bl_int_0_91 bl_0_91 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c92
+ bl_int_0_92 bl_0_92 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c93
+ bl_int_0_93 bl_0_93 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c94
+ bl_0_94 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c95
+ bl_int_0_95 bl_0_95 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c0
+ bl_0_0 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c1
+ bl_int_0_1 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c2
+ bl_int_1_2 bl_0_2 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c3
+ bl_int_0_3 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c4
+ bl_0_4 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c5
+ bl_int_0_5 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c6
+ bl_int_1_6 bl_0_6 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c7
+ bl_int_0_7 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c8
+ bl_0_8 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c9
+ bl_int_0_9 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c10
+ bl_int_1_10 bl_0_10 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c11
+ bl_int_0_11 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c12
+ bl_0_12 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c13
+ bl_int_0_13 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c14
+ bl_int_1_14 bl_0_14 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c15
+ bl_int_0_15 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c16
+ bl_0_16 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c17
+ bl_int_0_17 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c18
+ bl_int_1_18 bl_0_18 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c19
+ bl_int_0_19 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c20
+ bl_0_20 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c21
+ bl_int_0_21 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c22
+ bl_int_1_22 bl_0_22 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c23
+ bl_int_0_23 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c24
+ bl_0_24 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c25
+ bl_int_0_25 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c26
+ bl_int_1_26 bl_0_26 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c27
+ bl_int_0_27 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c28
+ bl_0_28 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c29
+ bl_int_0_29 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c30
+ bl_int_1_30 bl_0_30 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c31
+ bl_int_0_31 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c32
+ bl_0_32 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c33
+ bl_int_0_33 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c34
+ bl_int_1_34 bl_0_34 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c35
+ bl_int_0_35 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c36
+ bl_0_36 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c37
+ bl_int_0_37 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c38
+ bl_int_1_38 bl_0_38 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c39
+ bl_int_0_39 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c40
+ bl_0_40 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c41
+ bl_int_0_41 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c42
+ bl_int_1_42 bl_0_42 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c43
+ bl_int_0_43 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c44
+ bl_0_44 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c45
+ bl_int_0_45 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c46
+ bl_int_1_46 bl_0_46 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c47
+ bl_int_0_47 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c48
+ bl_0_48 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c49
+ bl_int_0_49 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c50
+ bl_int_1_50 bl_0_50 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c51
+ bl_int_0_51 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c52
+ bl_0_52 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c53
+ bl_int_0_53 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c54
+ bl_int_1_54 bl_0_54 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c55
+ bl_int_0_55 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c56
+ bl_0_56 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c57
+ bl_int_0_57 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c58
+ bl_int_1_58 bl_0_58 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c59
+ bl_int_0_59 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c60
+ bl_0_60 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c61
+ bl_int_0_61 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c62
+ bl_int_1_62 bl_int_0_62 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c63
+ bl_int_0_63 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c64
+ bl_int_1_64 bl_int_0_64 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c65
+ bl_int_0_65 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c66
+ bl_int_1_66 bl_0_66 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c67
+ bl_0_67 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c68
+ bl_int_0_68 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c69
+ bl_0_69 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c70
+ bl_int_1_70 bl_0_70 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c71
+ bl_int_1_71 bl_0_71 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c72
+ bl_int_0_72 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c73
+ bl_int_1_73 bl_int_0_73 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c74
+ bl_0_74 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c75
+ bl_0_75 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c76
+ bl_int_1_76 bl_0_76 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c77
+ bl_int_0_77 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c78
+ bl_int_0_78 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c79
+ bl_0_79 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c80
+ bl_int_0_80 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c81
+ bl_0_81 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c82
+ bl_int_0_82 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c83
+ bl_int_1_83 bl_0_83 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c84
+ bl_int_1_84 bl_int_0_84 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c85
+ bl_int_1_85 bl_int_0_85 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c86
+ bl_int_0_86 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c87
+ bl_0_87 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c88
+ bl_int_0_88 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c89
+ bl_0_89 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c90
+ bl_0_90 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c91
+ bl_int_0_91 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c92
+ bl_int_0_92 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c93
+ bl_int_0_93 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c94
+ bl_0_94 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c95
+ bl_int_1_95 bl_int_0_95 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c0
+ bl_0_0 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c1
+ bl_int_0_1 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c2
+ bl_int_1_2 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c3
+ bl_int_0_3 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c4
+ bl_0_4 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c5
+ bl_int_0_5 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c6
+ bl_int_1_6 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c7
+ bl_int_0_7 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c8
+ bl_0_8 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c9
+ bl_int_0_9 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c10
+ bl_int_1_10 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c11
+ bl_int_0_11 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c12
+ bl_0_12 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c13
+ bl_int_0_13 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c14
+ bl_int_1_14 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c15
+ bl_int_0_15 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c16
+ bl_0_16 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c17
+ bl_int_0_17 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c18
+ bl_int_1_18 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c19
+ bl_int_0_19 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c20
+ bl_0_20 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c21
+ bl_int_0_21 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c22
+ bl_int_1_22 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c23
+ bl_int_0_23 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c24
+ bl_0_24 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c25
+ bl_int_0_25 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c26
+ bl_int_1_26 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c27
+ bl_int_0_27 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c28
+ bl_0_28 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c29
+ bl_int_0_29 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c30
+ bl_int_1_30 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c31
+ bl_int_0_31 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c32
+ bl_0_32 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c33
+ bl_int_0_33 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c34
+ bl_int_1_34 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c35
+ bl_int_0_35 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c36
+ bl_0_36 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c37
+ bl_int_0_37 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c38
+ bl_int_1_38 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c39
+ bl_int_0_39 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c40
+ bl_0_40 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c41
+ bl_int_0_41 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c42
+ bl_int_1_42 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c43
+ bl_int_0_43 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c44
+ bl_0_44 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c45
+ bl_int_0_45 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c46
+ bl_int_1_46 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c47
+ bl_int_0_47 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c48
+ bl_0_48 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c49
+ bl_int_0_49 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c50
+ bl_int_1_50 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c51
+ bl_int_0_51 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c52
+ bl_0_52 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c53
+ bl_int_0_53 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c54
+ bl_int_1_54 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c55
+ bl_int_0_55 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c56
+ bl_0_56 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c57
+ bl_int_0_57 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c58
+ bl_int_1_58 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c59
+ bl_int_0_59 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c60
+ bl_int_2_60 bl_0_60 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c61
+ bl_int_2_61 bl_int_0_61 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c62
+ bl_int_1_62 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c63
+ bl_int_0_63 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c64
+ bl_int_2_64 bl_int_1_64 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c65
+ bl_int_0_65 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c66
+ bl_int_2_66 bl_int_1_66 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c67
+ bl_0_67 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c68
+ bl_int_0_68 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c69
+ bl_0_69 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c70
+ bl_int_1_70 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c71
+ bl_int_1_71 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c72
+ bl_int_2_72 bl_int_0_72 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c73
+ bl_int_1_73 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c74
+ bl_int_2_74 bl_0_74 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c75
+ bl_int_2_75 bl_0_75 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c76
+ bl_int_2_76 bl_int_1_76 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c77
+ bl_int_2_77 bl_int_0_77 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c78
+ bl_int_0_78 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c79
+ bl_int_2_79 bl_0_79 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c80
+ bl_int_0_80 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c81
+ bl_int_2_81 bl_0_81 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c82
+ bl_int_0_82 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c83
+ bl_int_1_83 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c84
+ bl_int_1_84 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c85
+ bl_int_2_85 bl_int_1_85 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c86
+ bl_int_2_86 bl_int_0_86 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c87
+ bl_0_87 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c88
+ bl_int_2_88 bl_int_0_88 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c89
+ bl_int_2_89 bl_0_89 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c90
+ bl_int_2_90 bl_0_90 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c91
+ bl_int_0_91 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c92
+ bl_int_0_92 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c93
+ bl_int_2_93 bl_int_0_93 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c94
+ bl_int_2_94 bl_0_94 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c95
+ bl_int_1_95 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c0
+ bl_int_3_0 bl_0_0 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c1
+ bl_int_3_1 bl_int_0_1 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c2
+ bl_int_3_2 bl_int_1_2 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c3
+ bl_int_0_3 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c4
+ bl_int_3_4 bl_0_4 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c5
+ bl_int_3_5 bl_int_0_5 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c6
+ bl_int_3_6 bl_int_1_6 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c7
+ bl_int_0_7 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c8
+ bl_int_3_8 bl_0_8 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c9
+ bl_int_3_9 bl_int_0_9 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c10
+ bl_int_3_10 bl_int_1_10 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c11
+ bl_int_0_11 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c12
+ bl_int_3_12 bl_0_12 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c13
+ bl_int_3_13 bl_int_0_13 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c14
+ bl_int_3_14 bl_int_1_14 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c15
+ bl_int_0_15 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c16
+ bl_int_3_16 bl_0_16 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c17
+ bl_int_3_17 bl_int_0_17 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c18
+ bl_int_3_18 bl_int_1_18 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c19
+ bl_int_0_19 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c20
+ bl_int_3_20 bl_0_20 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c21
+ bl_int_3_21 bl_int_0_21 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c22
+ bl_int_3_22 bl_int_1_22 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c23
+ bl_int_0_23 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c24
+ bl_int_3_24 bl_0_24 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c25
+ bl_int_3_25 bl_int_0_25 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c26
+ bl_int_3_26 bl_int_1_26 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c27
+ bl_int_0_27 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c28
+ bl_int_3_28 bl_0_28 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c29
+ bl_int_3_29 bl_int_0_29 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c30
+ bl_int_3_30 bl_int_1_30 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c31
+ bl_int_0_31 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c32
+ bl_int_3_32 bl_0_32 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c33
+ bl_int_3_33 bl_int_0_33 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c34
+ bl_int_3_34 bl_int_1_34 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c35
+ bl_int_0_35 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c36
+ bl_int_3_36 bl_0_36 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c37
+ bl_int_3_37 bl_int_0_37 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c38
+ bl_int_3_38 bl_int_1_38 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c39
+ bl_int_0_39 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c40
+ bl_int_3_40 bl_0_40 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c41
+ bl_int_3_41 bl_int_0_41 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c42
+ bl_int_3_42 bl_int_1_42 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c43
+ bl_int_0_43 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c44
+ bl_int_3_44 bl_0_44 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c45
+ bl_int_3_45 bl_int_0_45 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c46
+ bl_int_3_46 bl_int_1_46 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c47
+ bl_int_0_47 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c48
+ bl_int_3_48 bl_0_48 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c49
+ bl_int_3_49 bl_int_0_49 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c50
+ bl_int_3_50 bl_int_1_50 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c51
+ bl_int_0_51 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c52
+ bl_int_3_52 bl_0_52 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c53
+ bl_int_3_53 bl_int_0_53 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c54
+ bl_int_3_54 bl_int_1_54 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c55
+ bl_int_0_55 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c56
+ bl_int_3_56 bl_0_56 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c57
+ bl_int_3_57 bl_int_0_57 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c58
+ bl_int_3_58 bl_int_1_58 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c59
+ bl_int_0_59 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c60
+ bl_int_3_60 bl_int_2_60 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c61
+ bl_int_3_61 bl_int_2_61 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c62
+ bl_int_3_62 bl_int_1_62 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c63
+ bl_int_0_63 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c64
+ bl_int_2_64 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c65
+ bl_int_3_65 bl_int_0_65 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c66
+ bl_int_3_66 bl_int_2_66 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c67
+ bl_0_67 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c68
+ bl_int_0_68 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c69
+ bl_int_3_69 bl_0_69 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c70
+ bl_int_1_70 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c71
+ bl_int_3_71 bl_int_1_71 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c72
+ bl_int_2_72 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c73
+ bl_int_1_73 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c74
+ bl_int_3_74 bl_int_2_74 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c75
+ bl_int_2_75 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c76
+ bl_int_3_76 bl_int_2_76 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c77
+ bl_int_3_77 bl_int_2_77 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c78
+ bl_int_0_78 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c79
+ bl_int_3_79 bl_int_2_79 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c80
+ bl_int_0_80 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c81
+ bl_int_3_81 bl_int_2_81 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c82
+ bl_int_3_82 bl_int_0_82 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c83
+ bl_int_1_83 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c84
+ bl_int_1_84 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c85
+ bl_int_3_85 bl_int_2_85 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c86
+ bl_int_3_86 bl_int_2_86 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c87
+ bl_int_3_87 bl_0_87 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c88
+ bl_int_3_88 bl_int_2_88 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c89
+ bl_int_3_89 bl_int_2_89 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c90
+ bl_int_2_90 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c91
+ bl_int_0_91 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c92
+ bl_int_0_92 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c93
+ bl_int_3_93 bl_int_2_93 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c94
+ bl_int_2_94 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c95
+ bl_int_3_95 bl_int_1_95 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c0
+ bl_int_4_0 bl_int_3_0 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c1
+ bl_int_3_1 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c2
+ bl_int_3_2 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c3
+ bl_int_4_3 bl_int_0_3 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c4
+ bl_int_4_4 bl_int_3_4 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c5
+ bl_int_3_5 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c6
+ bl_int_3_6 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c7
+ bl_int_4_7 bl_int_0_7 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c8
+ bl_int_4_8 bl_int_3_8 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c9
+ bl_int_3_9 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c10
+ bl_int_3_10 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c11
+ bl_int_4_11 bl_int_0_11 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c12
+ bl_int_4_12 bl_int_3_12 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c13
+ bl_int_3_13 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c14
+ bl_int_3_14 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c15
+ bl_int_4_15 bl_int_0_15 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c16
+ bl_int_4_16 bl_int_3_16 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c17
+ bl_int_3_17 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c18
+ bl_int_3_18 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c19
+ bl_int_4_19 bl_int_0_19 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c20
+ bl_int_4_20 bl_int_3_20 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c21
+ bl_int_3_21 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c22
+ bl_int_3_22 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c23
+ bl_int_4_23 bl_int_0_23 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c24
+ bl_int_4_24 bl_int_3_24 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c25
+ bl_int_3_25 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c26
+ bl_int_3_26 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c27
+ bl_int_4_27 bl_int_0_27 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c28
+ bl_int_4_28 bl_int_3_28 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c29
+ bl_int_3_29 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c30
+ bl_int_3_30 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c31
+ bl_int_4_31 bl_int_0_31 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c32
+ bl_int_4_32 bl_int_3_32 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c33
+ bl_int_3_33 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c34
+ bl_int_3_34 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c35
+ bl_int_4_35 bl_int_0_35 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c36
+ bl_int_4_36 bl_int_3_36 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c37
+ bl_int_3_37 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c38
+ bl_int_3_38 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c39
+ bl_int_4_39 bl_int_0_39 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c40
+ bl_int_4_40 bl_int_3_40 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c41
+ bl_int_3_41 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c42
+ bl_int_3_42 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c43
+ bl_int_4_43 bl_int_0_43 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c44
+ bl_int_4_44 bl_int_3_44 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c45
+ bl_int_3_45 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c46
+ bl_int_3_46 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c47
+ bl_int_4_47 bl_int_0_47 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c48
+ bl_int_4_48 bl_int_3_48 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c49
+ bl_int_3_49 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c50
+ bl_int_3_50 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c51
+ bl_int_4_51 bl_int_0_51 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c52
+ bl_int_4_52 bl_int_3_52 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c53
+ bl_int_3_53 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c54
+ bl_int_3_54 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c55
+ bl_int_4_55 bl_int_0_55 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c56
+ bl_int_4_56 bl_int_3_56 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c57
+ bl_int_3_57 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c58
+ bl_int_3_58 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c59
+ bl_int_4_59 bl_int_0_59 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c60
+ bl_int_4_60 bl_int_3_60 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c61
+ bl_int_4_61 bl_int_3_61 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c62
+ bl_int_3_62 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c63
+ bl_int_0_63 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c64
+ bl_int_4_64 bl_int_2_64 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c65
+ bl_int_4_65 bl_int_3_65 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c66
+ bl_int_4_66 bl_int_3_66 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c67
+ bl_int_4_67 bl_0_67 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c68
+ bl_int_0_68 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c69
+ bl_int_3_69 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c70
+ bl_int_4_70 bl_int_1_70 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c71
+ bl_int_3_71 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c72
+ bl_int_2_72 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c73
+ bl_int_1_73 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c74
+ bl_int_3_74 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c75
+ bl_int_4_75 bl_int_2_75 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c76
+ bl_int_4_76 bl_int_3_76 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c77
+ bl_int_3_77 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c78
+ bl_int_0_78 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c79
+ bl_int_4_79 bl_int_3_79 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c80
+ bl_int_0_80 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c81
+ bl_int_3_81 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c82
+ bl_int_4_82 bl_int_3_82 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c83
+ bl_int_4_83 bl_int_1_83 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c84
+ bl_int_4_84 bl_int_1_84 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c85
+ bl_int_4_85 bl_int_3_85 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c86
+ bl_int_4_86 bl_int_3_86 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c87
+ bl_int_3_87 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c88
+ bl_int_3_88 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c89
+ bl_int_3_89 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c90
+ bl_int_2_90 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c91
+ bl_int_0_91 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c92
+ bl_int_0_92 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c93
+ bl_int_3_93 wl_0_4 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r4_c94
+ bl_int_4_94 bl_int_2_94 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c95
+ bl_int_4_95 bl_int_3_95 wl_0_4 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c0
+ bl_int_5_0 bl_int_4_0 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c1
+ bl_int_5_1 bl_int_3_1 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c2
+ bl_int_3_2 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c3
+ bl_int_4_3 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c4
+ bl_int_5_4 bl_int_4_4 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c5
+ bl_int_5_5 bl_int_3_5 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c6
+ bl_int_3_6 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c7
+ bl_int_4_7 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c8
+ bl_int_5_8 bl_int_4_8 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c9
+ bl_int_5_9 bl_int_3_9 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c10
+ bl_int_3_10 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c11
+ bl_int_4_11 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c12
+ bl_int_5_12 bl_int_4_12 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c13
+ bl_int_5_13 bl_int_3_13 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c14
+ bl_int_3_14 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c15
+ bl_int_4_15 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c16
+ bl_int_5_16 bl_int_4_16 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c17
+ bl_int_5_17 bl_int_3_17 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c18
+ bl_int_3_18 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c19
+ bl_int_4_19 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c20
+ bl_int_5_20 bl_int_4_20 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c21
+ bl_int_5_21 bl_int_3_21 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c22
+ bl_int_3_22 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c23
+ bl_int_4_23 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c24
+ bl_int_5_24 bl_int_4_24 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c25
+ bl_int_5_25 bl_int_3_25 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c26
+ bl_int_3_26 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c27
+ bl_int_4_27 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c28
+ bl_int_5_28 bl_int_4_28 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c29
+ bl_int_5_29 bl_int_3_29 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c30
+ bl_int_3_30 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c31
+ bl_int_4_31 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c32
+ bl_int_5_32 bl_int_4_32 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c33
+ bl_int_5_33 bl_int_3_33 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c34
+ bl_int_3_34 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c35
+ bl_int_4_35 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c36
+ bl_int_5_36 bl_int_4_36 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c37
+ bl_int_5_37 bl_int_3_37 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c38
+ bl_int_3_38 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c39
+ bl_int_4_39 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c40
+ bl_int_5_40 bl_int_4_40 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c41
+ bl_int_5_41 bl_int_3_41 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c42
+ bl_int_3_42 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c43
+ bl_int_4_43 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c44
+ bl_int_5_44 bl_int_4_44 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c45
+ bl_int_5_45 bl_int_3_45 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c46
+ bl_int_3_46 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c47
+ bl_int_4_47 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c48
+ bl_int_5_48 bl_int_4_48 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c49
+ bl_int_5_49 bl_int_3_49 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c50
+ bl_int_3_50 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c51
+ bl_int_4_51 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c52
+ bl_int_5_52 bl_int_4_52 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c53
+ bl_int_5_53 bl_int_3_53 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c54
+ bl_int_3_54 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c55
+ bl_int_4_55 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c56
+ bl_int_5_56 bl_int_4_56 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c57
+ bl_int_5_57 bl_int_3_57 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c58
+ bl_int_3_58 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c59
+ bl_int_4_59 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c60
+ bl_int_5_60 bl_int_4_60 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c61
+ bl_int_5_61 bl_int_4_61 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c62
+ bl_int_5_62 bl_int_3_62 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c63
+ bl_int_0_63 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c64
+ bl_int_5_64 bl_int_4_64 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c65
+ bl_int_4_65 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c66
+ bl_int_4_66 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c67
+ bl_int_4_67 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c68
+ bl_int_0_68 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c69
+ bl_int_5_69 bl_int_3_69 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c70
+ bl_int_4_70 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c71
+ bl_int_5_71 bl_int_3_71 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c72
+ bl_int_2_72 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c73
+ bl_int_5_73 bl_int_1_73 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c74
+ bl_int_5_74 bl_int_3_74 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c75
+ bl_int_5_75 bl_int_4_75 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c76
+ bl_int_5_76 bl_int_4_76 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c77
+ bl_int_5_77 bl_int_3_77 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c78
+ bl_int_0_78 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c79
+ bl_int_4_79 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c80
+ bl_int_5_80 bl_int_0_80 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c81
+ bl_int_5_81 bl_int_3_81 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c82
+ bl_int_5_82 bl_int_4_82 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c83
+ bl_int_5_83 bl_int_4_83 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c84
+ bl_int_4_84 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c85
+ bl_int_4_85 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c86
+ bl_int_4_86 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c87
+ bl_int_5_87 bl_int_3_87 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c88
+ bl_int_5_88 bl_int_3_88 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c89
+ bl_int_5_89 bl_int_3_89 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c90
+ bl_int_2_90 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c91
+ bl_int_0_91 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c92
+ bl_int_0_92 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c93
+ bl_int_3_93 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r5_c94
+ bl_int_5_94 bl_int_4_94 wl_0_5 gnd
+ bias_l1_rom_base_one_cell
Xbit_r5_c95
+ bl_int_4_95 wl_0_5 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c0
+ bl_int_5_0 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c1
+ bl_int_5_1 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c2
+ bl_int_3_2 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c3
+ bl_int_4_3 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c4
+ bl_int_5_4 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c5
+ bl_int_5_5 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c6
+ bl_int_3_6 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c7
+ bl_int_4_7 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c8
+ bl_int_5_8 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c9
+ bl_int_5_9 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c10
+ bl_int_3_10 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c11
+ bl_int_4_11 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c12
+ bl_int_5_12 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c13
+ bl_int_5_13 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c14
+ bl_int_3_14 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c15
+ bl_int_4_15 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c16
+ bl_int_5_16 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c17
+ bl_int_5_17 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c18
+ bl_int_3_18 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c19
+ bl_int_4_19 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c20
+ bl_int_5_20 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c21
+ bl_int_5_21 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c22
+ bl_int_3_22 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c23
+ bl_int_4_23 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c24
+ bl_int_5_24 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c25
+ bl_int_5_25 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c26
+ bl_int_3_26 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c27
+ bl_int_4_27 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c28
+ bl_int_5_28 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c29
+ bl_int_5_29 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c30
+ bl_int_3_30 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c31
+ bl_int_4_31 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c32
+ bl_int_5_32 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c33
+ bl_int_5_33 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c34
+ bl_int_3_34 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c35
+ bl_int_4_35 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c36
+ bl_int_5_36 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c37
+ bl_int_5_37 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c38
+ bl_int_3_38 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c39
+ bl_int_4_39 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c40
+ bl_int_5_40 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c41
+ bl_int_5_41 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c42
+ bl_int_3_42 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c43
+ bl_int_4_43 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c44
+ bl_int_5_44 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c45
+ bl_int_5_45 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c46
+ bl_int_3_46 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c47
+ bl_int_4_47 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c48
+ bl_int_5_48 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c49
+ bl_int_5_49 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c50
+ bl_int_3_50 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c51
+ bl_int_4_51 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c52
+ bl_int_5_52 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c53
+ bl_int_5_53 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c54
+ bl_int_3_54 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c55
+ bl_int_4_55 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c56
+ bl_int_5_56 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c57
+ bl_int_5_57 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c58
+ bl_int_3_58 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c59
+ bl_int_4_59 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c60
+ bl_int_5_60 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c61
+ bl_int_5_61 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c62
+ bl_int_5_62 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c63
+ bl_int_0_63 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c64
+ bl_int_5_64 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c65
+ bl_int_6_65 bl_int_4_65 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c66
+ bl_int_4_66 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c67
+ bl_int_6_67 bl_int_4_67 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c68
+ bl_int_0_68 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c69
+ bl_int_5_69 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c70
+ bl_int_4_70 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c71
+ bl_int_6_71 bl_int_5_71 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c72
+ bl_int_6_72 bl_int_2_72 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c73
+ bl_int_6_73 bl_int_5_73 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c74
+ bl_int_5_74 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c75
+ bl_int_6_75 bl_int_5_75 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c76
+ bl_int_6_76 bl_int_5_76 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c77
+ bl_int_6_77 bl_int_5_77 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c78
+ bl_int_6_78 bl_int_0_78 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c79
+ bl_int_4_79 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c80
+ bl_int_5_80 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c81
+ bl_int_5_81 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c82
+ bl_int_5_82 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c83
+ bl_int_5_83 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c84
+ bl_int_6_84 bl_int_4_84 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c85
+ bl_int_4_85 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c86
+ bl_int_4_86 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c87
+ bl_int_5_87 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c88
+ bl_int_6_88 bl_int_5_88 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c89
+ bl_int_6_89 bl_int_5_89 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c90
+ bl_int_6_90 bl_int_2_90 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c91
+ bl_int_0_91 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c92
+ bl_int_6_92 bl_int_0_92 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c93
+ bl_int_3_93 wl_0_6 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r6_c94
+ bl_int_6_94 bl_int_5_94 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r6_c95
+ bl_int_6_95 bl_int_4_95 wl_0_6 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c0
+ bl_int_5_0 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c1
+ bl_int_5_1 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c2
+ bl_int_7_2 bl_int_3_2 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c3
+ bl_int_7_3 bl_int_4_3 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c4
+ bl_int_5_4 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c5
+ bl_int_5_5 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c6
+ bl_int_7_6 bl_int_3_6 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c7
+ bl_int_7_7 bl_int_4_7 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c8
+ bl_int_5_8 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c9
+ bl_int_5_9 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c10
+ bl_int_7_10 bl_int_3_10 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c11
+ bl_int_7_11 bl_int_4_11 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c12
+ bl_int_5_12 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c13
+ bl_int_5_13 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c14
+ bl_int_7_14 bl_int_3_14 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c15
+ bl_int_7_15 bl_int_4_15 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c16
+ bl_int_5_16 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c17
+ bl_int_5_17 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c18
+ bl_int_7_18 bl_int_3_18 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c19
+ bl_int_7_19 bl_int_4_19 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c20
+ bl_int_5_20 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c21
+ bl_int_5_21 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c22
+ bl_int_7_22 bl_int_3_22 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c23
+ bl_int_7_23 bl_int_4_23 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c24
+ bl_int_5_24 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c25
+ bl_int_5_25 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c26
+ bl_int_7_26 bl_int_3_26 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c27
+ bl_int_7_27 bl_int_4_27 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c28
+ bl_int_5_28 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c29
+ bl_int_5_29 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c30
+ bl_int_7_30 bl_int_3_30 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c31
+ bl_int_7_31 bl_int_4_31 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c32
+ bl_int_5_32 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c33
+ bl_int_5_33 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c34
+ bl_int_7_34 bl_int_3_34 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c35
+ bl_int_7_35 bl_int_4_35 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c36
+ bl_int_5_36 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c37
+ bl_int_5_37 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c38
+ bl_int_7_38 bl_int_3_38 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c39
+ bl_int_7_39 bl_int_4_39 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c40
+ bl_int_5_40 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c41
+ bl_int_5_41 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c42
+ bl_int_7_42 bl_int_3_42 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c43
+ bl_int_7_43 bl_int_4_43 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c44
+ bl_int_5_44 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c45
+ bl_int_5_45 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c46
+ bl_int_7_46 bl_int_3_46 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c47
+ bl_int_7_47 bl_int_4_47 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c48
+ bl_int_5_48 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c49
+ bl_int_5_49 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c50
+ bl_int_7_50 bl_int_3_50 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c51
+ bl_int_7_51 bl_int_4_51 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c52
+ bl_int_5_52 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c53
+ bl_int_5_53 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c54
+ bl_int_7_54 bl_int_3_54 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c55
+ bl_int_7_55 bl_int_4_55 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c56
+ bl_int_5_56 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c57
+ bl_int_5_57 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c58
+ bl_int_7_58 bl_int_3_58 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c59
+ bl_int_7_59 bl_int_4_59 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c60
+ bl_int_5_60 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c61
+ bl_int_7_61 bl_int_5_61 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c62
+ bl_int_7_62 bl_int_5_62 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c63
+ bl_int_0_63 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c64
+ bl_int_7_64 bl_int_5_64 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c65
+ bl_int_6_65 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c66
+ bl_int_7_66 bl_int_4_66 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c67
+ bl_int_7_67 bl_int_6_67 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c68
+ bl_int_0_68 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c69
+ bl_int_5_69 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c70
+ bl_int_4_70 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c71
+ bl_int_7_71 bl_int_6_71 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c72
+ bl_int_7_72 bl_int_6_72 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c73
+ bl_int_6_73 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c74
+ bl_int_5_74 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c75
+ bl_int_7_75 bl_int_6_75 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c76
+ bl_int_6_76 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c77
+ bl_int_7_77 bl_int_6_77 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c78
+ bl_int_7_78 bl_int_6_78 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c79
+ bl_int_4_79 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c80
+ bl_int_5_80 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c81
+ bl_int_7_81 bl_int_5_81 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c82
+ bl_int_7_82 bl_int_5_82 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c83
+ bl_int_5_83 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c84
+ bl_int_6_84 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c85
+ bl_int_7_85 bl_int_4_85 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c86
+ bl_int_4_86 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c87
+ bl_int_7_87 bl_int_5_87 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c88
+ bl_int_7_88 bl_int_6_88 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c89
+ bl_int_6_89 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c90
+ bl_int_7_90 bl_int_6_90 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c91
+ bl_int_7_91 bl_int_0_91 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c92
+ bl_int_6_92 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c93
+ bl_int_7_93 bl_int_3_93 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r7_c94
+ bl_int_6_94 wl_0_7 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r7_c95
+ bl_int_7_95 bl_int_6_95 wl_0_7 gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c0
+ gnd bl_int_5_0 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c1
+ gnd bl_int_5_1 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c2
+ gnd bl_int_7_2 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c3
+ gnd bl_int_7_3 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c4
+ gnd bl_int_5_4 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c5
+ gnd bl_int_5_5 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c6
+ gnd bl_int_7_6 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c7
+ gnd bl_int_7_7 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c8
+ gnd bl_int_5_8 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c9
+ gnd bl_int_5_9 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c10
+ gnd bl_int_7_10 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c11
+ gnd bl_int_7_11 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c12
+ gnd bl_int_5_12 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c13
+ gnd bl_int_5_13 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c14
+ gnd bl_int_7_14 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c15
+ gnd bl_int_7_15 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c16
+ gnd bl_int_5_16 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c17
+ gnd bl_int_5_17 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c18
+ gnd bl_int_7_18 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c19
+ gnd bl_int_7_19 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c20
+ gnd bl_int_5_20 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c21
+ gnd bl_int_5_21 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c22
+ gnd bl_int_7_22 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c23
+ gnd bl_int_7_23 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c24
+ gnd bl_int_5_24 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c25
+ gnd bl_int_5_25 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c26
+ gnd bl_int_7_26 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c27
+ gnd bl_int_7_27 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c28
+ gnd bl_int_5_28 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c29
+ gnd bl_int_5_29 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c30
+ gnd bl_int_7_30 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c31
+ gnd bl_int_7_31 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c32
+ gnd bl_int_5_32 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c33
+ gnd bl_int_5_33 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c34
+ gnd bl_int_7_34 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c35
+ gnd bl_int_7_35 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c36
+ gnd bl_int_5_36 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c37
+ gnd bl_int_5_37 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c38
+ gnd bl_int_7_38 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c39
+ gnd bl_int_7_39 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c40
+ gnd bl_int_5_40 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c41
+ gnd bl_int_5_41 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c42
+ gnd bl_int_7_42 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c43
+ gnd bl_int_7_43 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c44
+ gnd bl_int_5_44 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c45
+ gnd bl_int_5_45 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c46
+ gnd bl_int_7_46 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c47
+ gnd bl_int_7_47 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c48
+ gnd bl_int_5_48 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c49
+ gnd bl_int_5_49 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c50
+ gnd bl_int_7_50 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c51
+ gnd bl_int_7_51 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c52
+ gnd bl_int_5_52 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c53
+ gnd bl_int_5_53 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c54
+ gnd bl_int_7_54 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c55
+ gnd bl_int_7_55 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c56
+ gnd bl_int_5_56 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c57
+ gnd bl_int_5_57 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c58
+ gnd bl_int_7_58 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c59
+ gnd bl_int_7_59 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c60
+ gnd bl_int_5_60 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c61
+ gnd bl_int_7_61 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c62
+ gnd bl_int_7_62 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c63
+ gnd bl_int_0_63 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c64
+ gnd bl_int_7_64 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c65
+ gnd bl_int_6_65 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c66
+ gnd bl_int_7_66 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c67
+ gnd bl_int_7_67 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c68
+ gnd bl_int_0_68 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c69
+ gnd bl_int_5_69 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c70
+ gnd bl_int_4_70 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c71
+ gnd bl_int_7_71 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c72
+ gnd bl_int_7_72 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c73
+ gnd bl_int_6_73 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c74
+ gnd bl_int_5_74 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c75
+ gnd bl_int_7_75 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c76
+ gnd bl_int_6_76 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c77
+ gnd bl_int_7_77 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c78
+ gnd bl_int_7_78 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c79
+ gnd bl_int_4_79 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c80
+ gnd bl_int_5_80 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c81
+ gnd bl_int_7_81 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c82
+ gnd bl_int_7_82 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c83
+ gnd bl_int_5_83 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c84
+ gnd bl_int_6_84 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c85
+ gnd bl_int_7_85 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c86
+ gnd bl_int_4_86 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c87
+ gnd bl_int_7_87 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c88
+ gnd bl_int_7_88 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c89
+ gnd bl_int_6_89 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c90
+ gnd bl_int_7_90 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c91
+ gnd bl_int_7_91 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c92
+ gnd bl_int_6_92 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c93
+ gnd bl_int_7_93 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c94
+ gnd bl_int_6_94 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r8_c95
+ gnd bl_int_7_95 precharge gnd
+ bias_l1_rom_base_one_cell
Xbitcell_array_precharge
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 bl_0_4 bl_0_5 bl_0_6 bl_0_7 bl_0_8 bl_0_9
+ bl_0_10 bl_0_11 bl_0_12 bl_0_13 bl_0_14 bl_0_15 bl_0_16 bl_0_17
+ bl_0_18 bl_0_19 bl_0_20 bl_0_21 bl_0_22 bl_0_23 bl_0_24 bl_0_25
+ bl_0_26 bl_0_27 bl_0_28 bl_0_29 bl_0_30 bl_0_31 bl_0_32 bl_0_33
+ bl_0_34 bl_0_35 bl_0_36 bl_0_37 bl_0_38 bl_0_39 bl_0_40 bl_0_41
+ bl_0_42 bl_0_43 bl_0_44 bl_0_45 bl_0_46 bl_0_47 bl_0_48 bl_0_49
+ bl_0_50 bl_0_51 bl_0_52 bl_0_53 bl_0_54 bl_0_55 bl_0_56 bl_0_57
+ bl_0_58 bl_0_59 bl_0_60 bl_0_61 bl_0_62 bl_0_63 bl_0_64 bl_0_65
+ bl_0_66 bl_0_67 bl_0_68 bl_0_69 bl_0_70 bl_0_71 bl_0_72 bl_0_73
+ bl_0_74 bl_0_75 bl_0_76 bl_0_77 bl_0_78 bl_0_79 bl_0_80 bl_0_81
+ bl_0_82 bl_0_83 bl_0_84 bl_0_85 bl_0_86 bl_0_87 bl_0_88 bl_0_89
+ bl_0_90 bl_0_91 bl_0_92 bl_0_93 bl_0_94 bl_0_95 precharge vdd
+ bias_l1_rom_precharge_array
.ENDS bias_l1_rom_base_array

.SUBCKT bias_l1_rom_address_control_array_0
+ A0_in A1_in A0_out A1_out Abar0_out Abar1_out clk vdd gnd
* INPUT : A0_in 
* INPUT : A1_in 
* OUTPUT: A0_out 
* OUTPUT: A1_out 
* OUTPUT: Abar0_out 
* OUTPUT: Abar1_out 
* INPUT : clk 
* POWER : vdd 
* GROUND: gnd 
XXaddr_buf_0
+ A0_in A0_out Abar0_out clk vdd gnd
+ bias_l1_rom_address_control_buf
XXaddr_buf_1
+ A1_in A1_out Abar1_out clk vdd gnd
+ bias_l1_rom_address_control_buf
.ENDS bias_l1_rom_address_control_array_0

.SUBCKT bias_l1_rom_precharge_array_1
+ pre_bl0_out pre_bl1_out pre_bl2_out pre_bl3_out gate vdd
* OUTPUT: pre_bl0_out 
* OUTPUT: pre_bl1_out 
* OUTPUT: pre_bl2_out 
* OUTPUT: pre_bl3_out 
* INPUT : gate 
* POWER : vdd 
Xpmos_c0
+ vdd gate pre_bl0_out
+ bias_l1_precharge_cell
Xpmos_c1
+ vdd gate pre_bl1_out
+ bias_l1_precharge_cell
Xpmos_c2
+ vdd gate pre_bl2_out
+ bias_l1_precharge_cell
Xpmos_c3
+ vdd gate pre_bl3_out
+ bias_l1_precharge_cell
.ENDS bias_l1_rom_precharge_array_1

.SUBCKT bias_l1_rom_column_decode_array
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 wl_0_0 wl_0_1 wl_0_2 wl_0_3 precharge vdd
+ gnd
* OUTPUT: bl_0_0 
* OUTPUT: bl_0_1 
* OUTPUT: bl_0_2 
* OUTPUT: bl_0_3 
* INPUT : wl_0_0 
* INPUT : wl_0_1 
* INPUT : wl_0_2 
* INPUT : wl_0_3 
* INPUT : precharge 
* POWER : vdd 
* GROUND: gnd 
Xbit_r0_c0
+ bl_int_0_0 bl_0_0 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c1
+ bl_int_0_1 bl_0_1 wl_0_0 gnd
+ bias_l1_rom_base_one_cell
Xbit_r0_c2
+ bl_0_2 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r0_c3
+ bl_0_3 wl_0_0 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c0
+ bl_int_0_0 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c1
+ bl_int_0_1 wl_0_1 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r1_c2
+ bl_int_1_2 bl_0_2 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r1_c3
+ bl_int_1_3 bl_0_3 wl_0_1 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c0
+ bl_int_2_0 bl_int_0_0 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c1
+ bl_int_0_1 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r2_c2
+ bl_int_2_2 bl_int_1_2 wl_0_2 gnd
+ bias_l1_rom_base_one_cell
Xbit_r2_c3
+ bl_int_1_3 wl_0_2 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c0
+ bl_int_2_0 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c1
+ bl_int_3_1 bl_int_0_1 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r3_c2
+ bl_int_2_2 wl_0_3 gnd
+ bias_l1_rom_base_zero_cell
Xbit_r3_c3
+ bl_int_3_3 bl_int_1_3 wl_0_3 gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c0
+ gnd bl_int_2_0 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c1
+ gnd bl_int_3_1 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c2
+ gnd bl_int_2_2 precharge gnd
+ bias_l1_rom_base_one_cell
Xbit_r4_c3
+ gnd bl_int_3_3 precharge gnd
+ bias_l1_rom_base_one_cell
Xbitcell_array_precharge
+ bl_0_0 bl_0_1 bl_0_2 bl_0_3 precharge vdd
+ bias_l1_rom_precharge_array_1
.ENDS bias_l1_rom_column_decode_array

.SUBCKT bias_l1_pinv_dec_2
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 2
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u
.ENDS bias_l1_pinv_dec_2

.SUBCKT bias_l1_rom_column_decode_wordline_buffer
+ in_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3 vdd gnd
* INPUT : in_0 
* INPUT : in_1 
* INPUT : in_2 
* INPUT : in_3 
* OUTPUT: out_0 
* OUTPUT: out_1 
* OUTPUT: out_2 
* OUTPUT: out_3 
* POWER : vdd 
* GROUND: gnd 
* rows: 4 Buffer size of: 2
Xwld0
+ in_0 out_0 vdd gnd
+ bias_l1_pinv_dec_2
Xwld1
+ in_1 out_1 vdd gnd
+ bias_l1_pinv_dec_2
Xwld2
+ in_2 out_2 vdd gnd
+ bias_l1_pinv_dec_2
Xwld3
+ in_3 out_3 vdd gnd
+ bias_l1_pinv_dec_2
.ENDS bias_l1_rom_column_decode_wordline_buffer

.SUBCKT bias_l1_rom_column_decode
+ A0 A1 wl_0 wl_1 wl_2 wl_3 precharge clk vdd gnd
* INPUT : A0 
* INPUT : A1 
* OUTPUT: wl_0 
* OUTPUT: wl_1 
* OUTPUT: wl_2 
* OUTPUT: wl_3 
* INPUT : precharge 
* INPUT : clk 
* POWER : vdd 
* GROUND: gnd 
Xdecode_array_inst
+ wl_int0 wl_int1 wl_int2 wl_int3 Ab_int_1 A_int_1 Ab_int_0 A_int_0
+ precharge vdd gnd
+ bias_l1_rom_column_decode_array
Xpre_control_array
+ A0 A1 A_int_0 A_int_1 Ab_int_0 Ab_int_1 clk vdd gnd
+ bias_l1_rom_address_control_array_0
Xrom_wordline_driver
+ wl_int0 wl_int1 wl_int2 wl_int3 wl_0 wl_1 wl_2 wl_3 vdd gnd
+ bias_l1_rom_column_decode_wordline_buffer
.ENDS bias_l1_rom_column_decode

.SUBCKT bias_l1_pinv_dec_3
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 4
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=5.0 l=0.15 pd=10.30 ps=10.30 as=1.88u ad=1.88u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u
.ENDS bias_l1_pinv_dec_3

.SUBCKT bias_l1_rom_bitline_inverter
+ in_0 in_1 in_2 in_3 in_4 in_5 in_6 in_7 in_8 in_9 in_10 in_11 in_12
+ in_13 in_14 in_15 in_16 in_17 in_18 in_19 in_20 in_21 in_22 in_23
+ in_24 in_25 in_26 in_27 in_28 in_29 in_30 in_31 in_32 in_33 in_34
+ in_35 in_36 in_37 in_38 in_39 in_40 in_41 in_42 in_43 in_44 in_45
+ in_46 in_47 in_48 in_49 in_50 in_51 in_52 in_53 in_54 in_55 in_56
+ in_57 in_58 in_59 in_60 in_61 in_62 in_63 in_64 in_65 in_66 in_67
+ in_68 in_69 in_70 in_71 in_72 in_73 in_74 in_75 in_76 in_77 in_78
+ in_79 in_80 in_81 in_82 in_83 in_84 in_85 in_86 in_87 in_88 in_89
+ in_90 in_91 in_92 in_93 in_94 in_95 out_0 out_1 out_2 out_3 out_4
+ out_5 out_6 out_7 out_8 out_9 out_10 out_11 out_12 out_13 out_14
+ out_15 out_16 out_17 out_18 out_19 out_20 out_21 out_22 out_23 out_24
+ out_25 out_26 out_27 out_28 out_29 out_30 out_31 out_32 out_33 out_34
+ out_35 out_36 out_37 out_38 out_39 out_40 out_41 out_42 out_43 out_44
+ out_45 out_46 out_47 out_48 out_49 out_50 out_51 out_52 out_53 out_54
+ out_55 out_56 out_57 out_58 out_59 out_60 out_61 out_62 out_63 out_64
+ out_65 out_66 out_67 out_68 out_69 out_70 out_71 out_72 out_73 out_74
+ out_75 out_76 out_77 out_78 out_79 out_80 out_81 out_82 out_83 out_84
+ out_85 out_86 out_87 out_88 out_89 out_90 out_91 out_92 out_93 out_94
+ out_95 vdd gnd
* INPUT : in_0 
* INPUT : in_1 
* INPUT : in_2 
* INPUT : in_3 
* INPUT : in_4 
* INPUT : in_5 
* INPUT : in_6 
* INPUT : in_7 
* INPUT : in_8 
* INPUT : in_9 
* INPUT : in_10 
* INPUT : in_11 
* INPUT : in_12 
* INPUT : in_13 
* INPUT : in_14 
* INPUT : in_15 
* INPUT : in_16 
* INPUT : in_17 
* INPUT : in_18 
* INPUT : in_19 
* INPUT : in_20 
* INPUT : in_21 
* INPUT : in_22 
* INPUT : in_23 
* INPUT : in_24 
* INPUT : in_25 
* INPUT : in_26 
* INPUT : in_27 
* INPUT : in_28 
* INPUT : in_29 
* INPUT : in_30 
* INPUT : in_31 
* INPUT : in_32 
* INPUT : in_33 
* INPUT : in_34 
* INPUT : in_35 
* INPUT : in_36 
* INPUT : in_37 
* INPUT : in_38 
* INPUT : in_39 
* INPUT : in_40 
* INPUT : in_41 
* INPUT : in_42 
* INPUT : in_43 
* INPUT : in_44 
* INPUT : in_45 
* INPUT : in_46 
* INPUT : in_47 
* INPUT : in_48 
* INPUT : in_49 
* INPUT : in_50 
* INPUT : in_51 
* INPUT : in_52 
* INPUT : in_53 
* INPUT : in_54 
* INPUT : in_55 
* INPUT : in_56 
* INPUT : in_57 
* INPUT : in_58 
* INPUT : in_59 
* INPUT : in_60 
* INPUT : in_61 
* INPUT : in_62 
* INPUT : in_63 
* INPUT : in_64 
* INPUT : in_65 
* INPUT : in_66 
* INPUT : in_67 
* INPUT : in_68 
* INPUT : in_69 
* INPUT : in_70 
* INPUT : in_71 
* INPUT : in_72 
* INPUT : in_73 
* INPUT : in_74 
* INPUT : in_75 
* INPUT : in_76 
* INPUT : in_77 
* INPUT : in_78 
* INPUT : in_79 
* INPUT : in_80 
* INPUT : in_81 
* INPUT : in_82 
* INPUT : in_83 
* INPUT : in_84 
* INPUT : in_85 
* INPUT : in_86 
* INPUT : in_87 
* INPUT : in_88 
* INPUT : in_89 
* INPUT : in_90 
* INPUT : in_91 
* INPUT : in_92 
* INPUT : in_93 
* INPUT : in_94 
* INPUT : in_95 
* OUTPUT: out_0 
* OUTPUT: out_1 
* OUTPUT: out_2 
* OUTPUT: out_3 
* OUTPUT: out_4 
* OUTPUT: out_5 
* OUTPUT: out_6 
* OUTPUT: out_7 
* OUTPUT: out_8 
* OUTPUT: out_9 
* OUTPUT: out_10 
* OUTPUT: out_11 
* OUTPUT: out_12 
* OUTPUT: out_13 
* OUTPUT: out_14 
* OUTPUT: out_15 
* OUTPUT: out_16 
* OUTPUT: out_17 
* OUTPUT: out_18 
* OUTPUT: out_19 
* OUTPUT: out_20 
* OUTPUT: out_21 
* OUTPUT: out_22 
* OUTPUT: out_23 
* OUTPUT: out_24 
* OUTPUT: out_25 
* OUTPUT: out_26 
* OUTPUT: out_27 
* OUTPUT: out_28 
* OUTPUT: out_29 
* OUTPUT: out_30 
* OUTPUT: out_31 
* OUTPUT: out_32 
* OUTPUT: out_33 
* OUTPUT: out_34 
* OUTPUT: out_35 
* OUTPUT: out_36 
* OUTPUT: out_37 
* OUTPUT: out_38 
* OUTPUT: out_39 
* OUTPUT: out_40 
* OUTPUT: out_41 
* OUTPUT: out_42 
* OUTPUT: out_43 
* OUTPUT: out_44 
* OUTPUT: out_45 
* OUTPUT: out_46 
* OUTPUT: out_47 
* OUTPUT: out_48 
* OUTPUT: out_49 
* OUTPUT: out_50 
* OUTPUT: out_51 
* OUTPUT: out_52 
* OUTPUT: out_53 
* OUTPUT: out_54 
* OUTPUT: out_55 
* OUTPUT: out_56 
* OUTPUT: out_57 
* OUTPUT: out_58 
* OUTPUT: out_59 
* OUTPUT: out_60 
* OUTPUT: out_61 
* OUTPUT: out_62 
* OUTPUT: out_63 
* OUTPUT: out_64 
* OUTPUT: out_65 
* OUTPUT: out_66 
* OUTPUT: out_67 
* OUTPUT: out_68 
* OUTPUT: out_69 
* OUTPUT: out_70 
* OUTPUT: out_71 
* OUTPUT: out_72 
* OUTPUT: out_73 
* OUTPUT: out_74 
* OUTPUT: out_75 
* OUTPUT: out_76 
* OUTPUT: out_77 
* OUTPUT: out_78 
* OUTPUT: out_79 
* OUTPUT: out_80 
* OUTPUT: out_81 
* OUTPUT: out_82 
* OUTPUT: out_83 
* OUTPUT: out_84 
* OUTPUT: out_85 
* OUTPUT: out_86 
* OUTPUT: out_87 
* OUTPUT: out_88 
* OUTPUT: out_89 
* OUTPUT: out_90 
* OUTPUT: out_91 
* OUTPUT: out_92 
* OUTPUT: out_93 
* OUTPUT: out_94 
* OUTPUT: out_95 
* POWER : vdd 
* GROUND: gnd 
* rows: 96 Buffer size of: 4
Xwld0
+ in_0 out_0 vdd gnd
+ bias_l1_pinv_dec_3
Xwld1
+ in_1 out_1 vdd gnd
+ bias_l1_pinv_dec_3
Xwld2
+ in_2 out_2 vdd gnd
+ bias_l1_pinv_dec_3
Xwld3
+ in_3 out_3 vdd gnd
+ bias_l1_pinv_dec_3
Xwld4
+ in_4 out_4 vdd gnd
+ bias_l1_pinv_dec_3
Xwld5
+ in_5 out_5 vdd gnd
+ bias_l1_pinv_dec_3
Xwld6
+ in_6 out_6 vdd gnd
+ bias_l1_pinv_dec_3
Xwld7
+ in_7 out_7 vdd gnd
+ bias_l1_pinv_dec_3
Xwld8
+ in_8 out_8 vdd gnd
+ bias_l1_pinv_dec_3
Xwld9
+ in_9 out_9 vdd gnd
+ bias_l1_pinv_dec_3
Xwld10
+ in_10 out_10 vdd gnd
+ bias_l1_pinv_dec_3
Xwld11
+ in_11 out_11 vdd gnd
+ bias_l1_pinv_dec_3
Xwld12
+ in_12 out_12 vdd gnd
+ bias_l1_pinv_dec_3
Xwld13
+ in_13 out_13 vdd gnd
+ bias_l1_pinv_dec_3
Xwld14
+ in_14 out_14 vdd gnd
+ bias_l1_pinv_dec_3
Xwld15
+ in_15 out_15 vdd gnd
+ bias_l1_pinv_dec_3
Xwld16
+ in_16 out_16 vdd gnd
+ bias_l1_pinv_dec_3
Xwld17
+ in_17 out_17 vdd gnd
+ bias_l1_pinv_dec_3
Xwld18
+ in_18 out_18 vdd gnd
+ bias_l1_pinv_dec_3
Xwld19
+ in_19 out_19 vdd gnd
+ bias_l1_pinv_dec_3
Xwld20
+ in_20 out_20 vdd gnd
+ bias_l1_pinv_dec_3
Xwld21
+ in_21 out_21 vdd gnd
+ bias_l1_pinv_dec_3
Xwld22
+ in_22 out_22 vdd gnd
+ bias_l1_pinv_dec_3
Xwld23
+ in_23 out_23 vdd gnd
+ bias_l1_pinv_dec_3
Xwld24
+ in_24 out_24 vdd gnd
+ bias_l1_pinv_dec_3
Xwld25
+ in_25 out_25 vdd gnd
+ bias_l1_pinv_dec_3
Xwld26
+ in_26 out_26 vdd gnd
+ bias_l1_pinv_dec_3
Xwld27
+ in_27 out_27 vdd gnd
+ bias_l1_pinv_dec_3
Xwld28
+ in_28 out_28 vdd gnd
+ bias_l1_pinv_dec_3
Xwld29
+ in_29 out_29 vdd gnd
+ bias_l1_pinv_dec_3
Xwld30
+ in_30 out_30 vdd gnd
+ bias_l1_pinv_dec_3
Xwld31
+ in_31 out_31 vdd gnd
+ bias_l1_pinv_dec_3
Xwld32
+ in_32 out_32 vdd gnd
+ bias_l1_pinv_dec_3
Xwld33
+ in_33 out_33 vdd gnd
+ bias_l1_pinv_dec_3
Xwld34
+ in_34 out_34 vdd gnd
+ bias_l1_pinv_dec_3
Xwld35
+ in_35 out_35 vdd gnd
+ bias_l1_pinv_dec_3
Xwld36
+ in_36 out_36 vdd gnd
+ bias_l1_pinv_dec_3
Xwld37
+ in_37 out_37 vdd gnd
+ bias_l1_pinv_dec_3
Xwld38
+ in_38 out_38 vdd gnd
+ bias_l1_pinv_dec_3
Xwld39
+ in_39 out_39 vdd gnd
+ bias_l1_pinv_dec_3
Xwld40
+ in_40 out_40 vdd gnd
+ bias_l1_pinv_dec_3
Xwld41
+ in_41 out_41 vdd gnd
+ bias_l1_pinv_dec_3
Xwld42
+ in_42 out_42 vdd gnd
+ bias_l1_pinv_dec_3
Xwld43
+ in_43 out_43 vdd gnd
+ bias_l1_pinv_dec_3
Xwld44
+ in_44 out_44 vdd gnd
+ bias_l1_pinv_dec_3
Xwld45
+ in_45 out_45 vdd gnd
+ bias_l1_pinv_dec_3
Xwld46
+ in_46 out_46 vdd gnd
+ bias_l1_pinv_dec_3
Xwld47
+ in_47 out_47 vdd gnd
+ bias_l1_pinv_dec_3
Xwld48
+ in_48 out_48 vdd gnd
+ bias_l1_pinv_dec_3
Xwld49
+ in_49 out_49 vdd gnd
+ bias_l1_pinv_dec_3
Xwld50
+ in_50 out_50 vdd gnd
+ bias_l1_pinv_dec_3
Xwld51
+ in_51 out_51 vdd gnd
+ bias_l1_pinv_dec_3
Xwld52
+ in_52 out_52 vdd gnd
+ bias_l1_pinv_dec_3
Xwld53
+ in_53 out_53 vdd gnd
+ bias_l1_pinv_dec_3
Xwld54
+ in_54 out_54 vdd gnd
+ bias_l1_pinv_dec_3
Xwld55
+ in_55 out_55 vdd gnd
+ bias_l1_pinv_dec_3
Xwld56
+ in_56 out_56 vdd gnd
+ bias_l1_pinv_dec_3
Xwld57
+ in_57 out_57 vdd gnd
+ bias_l1_pinv_dec_3
Xwld58
+ in_58 out_58 vdd gnd
+ bias_l1_pinv_dec_3
Xwld59
+ in_59 out_59 vdd gnd
+ bias_l1_pinv_dec_3
Xwld60
+ in_60 out_60 vdd gnd
+ bias_l1_pinv_dec_3
Xwld61
+ in_61 out_61 vdd gnd
+ bias_l1_pinv_dec_3
Xwld62
+ in_62 out_62 vdd gnd
+ bias_l1_pinv_dec_3
Xwld63
+ in_63 out_63 vdd gnd
+ bias_l1_pinv_dec_3
Xwld64
+ in_64 out_64 vdd gnd
+ bias_l1_pinv_dec_3
Xwld65
+ in_65 out_65 vdd gnd
+ bias_l1_pinv_dec_3
Xwld66
+ in_66 out_66 vdd gnd
+ bias_l1_pinv_dec_3
Xwld67
+ in_67 out_67 vdd gnd
+ bias_l1_pinv_dec_3
Xwld68
+ in_68 out_68 vdd gnd
+ bias_l1_pinv_dec_3
Xwld69
+ in_69 out_69 vdd gnd
+ bias_l1_pinv_dec_3
Xwld70
+ in_70 out_70 vdd gnd
+ bias_l1_pinv_dec_3
Xwld71
+ in_71 out_71 vdd gnd
+ bias_l1_pinv_dec_3
Xwld72
+ in_72 out_72 vdd gnd
+ bias_l1_pinv_dec_3
Xwld73
+ in_73 out_73 vdd gnd
+ bias_l1_pinv_dec_3
Xwld74
+ in_74 out_74 vdd gnd
+ bias_l1_pinv_dec_3
Xwld75
+ in_75 out_75 vdd gnd
+ bias_l1_pinv_dec_3
Xwld76
+ in_76 out_76 vdd gnd
+ bias_l1_pinv_dec_3
Xwld77
+ in_77 out_77 vdd gnd
+ bias_l1_pinv_dec_3
Xwld78
+ in_78 out_78 vdd gnd
+ bias_l1_pinv_dec_3
Xwld79
+ in_79 out_79 vdd gnd
+ bias_l1_pinv_dec_3
Xwld80
+ in_80 out_80 vdd gnd
+ bias_l1_pinv_dec_3
Xwld81
+ in_81 out_81 vdd gnd
+ bias_l1_pinv_dec_3
Xwld82
+ in_82 out_82 vdd gnd
+ bias_l1_pinv_dec_3
Xwld83
+ in_83 out_83 vdd gnd
+ bias_l1_pinv_dec_3
Xwld84
+ in_84 out_84 vdd gnd
+ bias_l1_pinv_dec_3
Xwld85
+ in_85 out_85 vdd gnd
+ bias_l1_pinv_dec_3
Xwld86
+ in_86 out_86 vdd gnd
+ bias_l1_pinv_dec_3
Xwld87
+ in_87 out_87 vdd gnd
+ bias_l1_pinv_dec_3
Xwld88
+ in_88 out_88 vdd gnd
+ bias_l1_pinv_dec_3
Xwld89
+ in_89 out_89 vdd gnd
+ bias_l1_pinv_dec_3
Xwld90
+ in_90 out_90 vdd gnd
+ bias_l1_pinv_dec_3
Xwld91
+ in_91 out_91 vdd gnd
+ bias_l1_pinv_dec_3
Xwld92
+ in_92 out_92 vdd gnd
+ bias_l1_pinv_dec_3
Xwld93
+ in_93 out_93 vdd gnd
+ bias_l1_pinv_dec_3
Xwld94
+ in_94 out_94 vdd gnd
+ bias_l1_pinv_dec_3
Xwld95
+ in_95 out_95 vdd gnd
+ bias_l1_pinv_dec_3
.ENDS bias_l1_rom_bitline_inverter

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=2.88 l=0.15 pd=6.06 ps=6.06 as=1.08u ad=1.08u

.SUBCKT bias_l1_rom_column_mux
+ bl bl_out sel gnd
* INOUT : bl 
* INOUT : bl_out 
* INOUT : sel 
* INOUT : gnd 
Xmux_tx1 bl sel bl_out gnd sky130_fd_pr__nfet_01v8 m=1 w=2.88 l=0.15 pd=6.06 ps=6.06 as=1.08u ad=1.08u
.ENDS bias_l1_rom_column_mux

.SUBCKT bias_l1_rom_column_mux_array
+ bl_0 bl_1 bl_2 bl_3 bl_4 bl_5 bl_6 bl_7 bl_8 bl_9 bl_10 bl_11 bl_12
+ bl_13 bl_14 bl_15 bl_16 bl_17 bl_18 bl_19 bl_20 bl_21 bl_22 bl_23
+ bl_24 bl_25 bl_26 bl_27 bl_28 bl_29 bl_30 bl_31 bl_32 bl_33 bl_34
+ bl_35 bl_36 bl_37 bl_38 bl_39 bl_40 bl_41 bl_42 bl_43 bl_44 bl_45
+ bl_46 bl_47 bl_48 bl_49 bl_50 bl_51 bl_52 bl_53 bl_54 bl_55 bl_56
+ bl_57 bl_58 bl_59 bl_60 bl_61 bl_62 bl_63 bl_64 bl_65 bl_66 bl_67
+ bl_68 bl_69 bl_70 bl_71 bl_72 bl_73 bl_74 bl_75 bl_76 bl_77 bl_78
+ bl_79 bl_80 bl_81 bl_82 bl_83 bl_84 bl_85 bl_86 bl_87 bl_88 bl_89
+ bl_90 bl_91 bl_92 bl_93 bl_94 bl_95 sel_0 sel_1 sel_2 sel_3 bl_out_0
+ bl_out_1 bl_out_2 bl_out_3 bl_out_4 bl_out_5 bl_out_6 bl_out_7
+ bl_out_8 bl_out_9 bl_out_10 bl_out_11 bl_out_12 bl_out_13 bl_out_14
+ bl_out_15 bl_out_16 bl_out_17 bl_out_18 bl_out_19 bl_out_20 bl_out_21
+ bl_out_22 bl_out_23 gnd
* INOUT : bl_0 
* INOUT : bl_1 
* INOUT : bl_2 
* INOUT : bl_3 
* INOUT : bl_4 
* INOUT : bl_5 
* INOUT : bl_6 
* INOUT : bl_7 
* INOUT : bl_8 
* INOUT : bl_9 
* INOUT : bl_10 
* INOUT : bl_11 
* INOUT : bl_12 
* INOUT : bl_13 
* INOUT : bl_14 
* INOUT : bl_15 
* INOUT : bl_16 
* INOUT : bl_17 
* INOUT : bl_18 
* INOUT : bl_19 
* INOUT : bl_20 
* INOUT : bl_21 
* INOUT : bl_22 
* INOUT : bl_23 
* INOUT : bl_24 
* INOUT : bl_25 
* INOUT : bl_26 
* INOUT : bl_27 
* INOUT : bl_28 
* INOUT : bl_29 
* INOUT : bl_30 
* INOUT : bl_31 
* INOUT : bl_32 
* INOUT : bl_33 
* INOUT : bl_34 
* INOUT : bl_35 
* INOUT : bl_36 
* INOUT : bl_37 
* INOUT : bl_38 
* INOUT : bl_39 
* INOUT : bl_40 
* INOUT : bl_41 
* INOUT : bl_42 
* INOUT : bl_43 
* INOUT : bl_44 
* INOUT : bl_45 
* INOUT : bl_46 
* INOUT : bl_47 
* INOUT : bl_48 
* INOUT : bl_49 
* INOUT : bl_50 
* INOUT : bl_51 
* INOUT : bl_52 
* INOUT : bl_53 
* INOUT : bl_54 
* INOUT : bl_55 
* INOUT : bl_56 
* INOUT : bl_57 
* INOUT : bl_58 
* INOUT : bl_59 
* INOUT : bl_60 
* INOUT : bl_61 
* INOUT : bl_62 
* INOUT : bl_63 
* INOUT : bl_64 
* INOUT : bl_65 
* INOUT : bl_66 
* INOUT : bl_67 
* INOUT : bl_68 
* INOUT : bl_69 
* INOUT : bl_70 
* INOUT : bl_71 
* INOUT : bl_72 
* INOUT : bl_73 
* INOUT : bl_74 
* INOUT : bl_75 
* INOUT : bl_76 
* INOUT : bl_77 
* INOUT : bl_78 
* INOUT : bl_79 
* INOUT : bl_80 
* INOUT : bl_81 
* INOUT : bl_82 
* INOUT : bl_83 
* INOUT : bl_84 
* INOUT : bl_85 
* INOUT : bl_86 
* INOUT : bl_87 
* INOUT : bl_88 
* INOUT : bl_89 
* INOUT : bl_90 
* INOUT : bl_91 
* INOUT : bl_92 
* INOUT : bl_93 
* INOUT : bl_94 
* INOUT : bl_95 
* INOUT : sel_0 
* INOUT : sel_1 
* INOUT : sel_2 
* INOUT : sel_3 
* INOUT : bl_out_0 
* INOUT : bl_out_1 
* INOUT : bl_out_2 
* INOUT : bl_out_3 
* INOUT : bl_out_4 
* INOUT : bl_out_5 
* INOUT : bl_out_6 
* INOUT : bl_out_7 
* INOUT : bl_out_8 
* INOUT : bl_out_9 
* INOUT : bl_out_10 
* INOUT : bl_out_11 
* INOUT : bl_out_12 
* INOUT : bl_out_13 
* INOUT : bl_out_14 
* INOUT : bl_out_15 
* INOUT : bl_out_16 
* INOUT : bl_out_17 
* INOUT : bl_out_18 
* INOUT : bl_out_19 
* INOUT : bl_out_20 
* INOUT : bl_out_21 
* INOUT : bl_out_22 
* INOUT : bl_out_23 
* INOUT : gnd 
* cols: 96 word_size: 24 
XXMUX0
+ bl_0 bl_out_0 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX1
+ bl_1 bl_out_0 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX2
+ bl_2 bl_out_0 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX3
+ bl_3 bl_out_0 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX4
+ bl_4 bl_out_1 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX5
+ bl_5 bl_out_1 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX6
+ bl_6 bl_out_1 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX7
+ bl_7 bl_out_1 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX8
+ bl_8 bl_out_2 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX9
+ bl_9 bl_out_2 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX10
+ bl_10 bl_out_2 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX11
+ bl_11 bl_out_2 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX12
+ bl_12 bl_out_3 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX13
+ bl_13 bl_out_3 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX14
+ bl_14 bl_out_3 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX15
+ bl_15 bl_out_3 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX16
+ bl_16 bl_out_4 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX17
+ bl_17 bl_out_4 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX18
+ bl_18 bl_out_4 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX19
+ bl_19 bl_out_4 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX20
+ bl_20 bl_out_5 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX21
+ bl_21 bl_out_5 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX22
+ bl_22 bl_out_5 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX23
+ bl_23 bl_out_5 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX24
+ bl_24 bl_out_6 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX25
+ bl_25 bl_out_6 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX26
+ bl_26 bl_out_6 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX27
+ bl_27 bl_out_6 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX28
+ bl_28 bl_out_7 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX29
+ bl_29 bl_out_7 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX30
+ bl_30 bl_out_7 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX31
+ bl_31 bl_out_7 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX32
+ bl_32 bl_out_8 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX33
+ bl_33 bl_out_8 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX34
+ bl_34 bl_out_8 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX35
+ bl_35 bl_out_8 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX36
+ bl_36 bl_out_9 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX37
+ bl_37 bl_out_9 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX38
+ bl_38 bl_out_9 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX39
+ bl_39 bl_out_9 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX40
+ bl_40 bl_out_10 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX41
+ bl_41 bl_out_10 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX42
+ bl_42 bl_out_10 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX43
+ bl_43 bl_out_10 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX44
+ bl_44 bl_out_11 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX45
+ bl_45 bl_out_11 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX46
+ bl_46 bl_out_11 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX47
+ bl_47 bl_out_11 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX48
+ bl_48 bl_out_12 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX49
+ bl_49 bl_out_12 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX50
+ bl_50 bl_out_12 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX51
+ bl_51 bl_out_12 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX52
+ bl_52 bl_out_13 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX53
+ bl_53 bl_out_13 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX54
+ bl_54 bl_out_13 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX55
+ bl_55 bl_out_13 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX56
+ bl_56 bl_out_14 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX57
+ bl_57 bl_out_14 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX58
+ bl_58 bl_out_14 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX59
+ bl_59 bl_out_14 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX60
+ bl_60 bl_out_15 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX61
+ bl_61 bl_out_15 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX62
+ bl_62 bl_out_15 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX63
+ bl_63 bl_out_15 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX64
+ bl_64 bl_out_16 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX65
+ bl_65 bl_out_16 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX66
+ bl_66 bl_out_16 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX67
+ bl_67 bl_out_16 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX68
+ bl_68 bl_out_17 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX69
+ bl_69 bl_out_17 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX70
+ bl_70 bl_out_17 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX71
+ bl_71 bl_out_17 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX72
+ bl_72 bl_out_18 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX73
+ bl_73 bl_out_18 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX74
+ bl_74 bl_out_18 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX75
+ bl_75 bl_out_18 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX76
+ bl_76 bl_out_19 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX77
+ bl_77 bl_out_19 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX78
+ bl_78 bl_out_19 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX79
+ bl_79 bl_out_19 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX80
+ bl_80 bl_out_20 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX81
+ bl_81 bl_out_20 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX82
+ bl_82 bl_out_20 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX83
+ bl_83 bl_out_20 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX84
+ bl_84 bl_out_21 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX85
+ bl_85 bl_out_21 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX86
+ bl_86 bl_out_21 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX87
+ bl_87 bl_out_21 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX88
+ bl_88 bl_out_22 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX89
+ bl_89 bl_out_22 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX90
+ bl_90 bl_out_22 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX91
+ bl_91 bl_out_22 sel_3 gnd
+ bias_l1_rom_column_mux
XXMUX92
+ bl_92 bl_out_23 sel_0 gnd
+ bias_l1_rom_column_mux
XXMUX93
+ bl_93 bl_out_23 sel_1 gnd
+ bias_l1_rom_column_mux
XXMUX94
+ bl_94 bl_out_23 sel_2 gnd
+ bias_l1_rom_column_mux
XXMUX95
+ bl_95 bl_out_23 sel_3 gnd
+ bias_l1_rom_column_mux
.ENDS bias_l1_rom_column_mux_array

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=5 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=5 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

.SUBCKT bias_l1_pinv_3
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 12
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=5 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=5 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u
.ENDS bias_l1_pinv_3

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=1.12 l=0.15 pd=2.54 ps=2.54 as=0.42u ad=0.42u

* spice ptx X{0} {1} sky130_fd_pr__special_nfet_01v8 m=1 w=0.36 l=0.15 pd=1.02 ps=1.02 as=0.14u ad=0.14u

.SUBCKT bias_l1_pinv
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 1
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=1.12 l=0.15 pd=2.54 ps=2.54 as=0.42u ad=0.42u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__special_nfet_01v8 m=1 w=0.36 l=0.15 pd=1.02 ps=1.02 as=0.14u ad=0.14u
.ENDS bias_l1_pinv

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=3 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=3 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u

.SUBCKT bias_l1_pinv_2
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 4
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=3 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=3 w=1.68 l=0.15 pd=3.66 ps=3.66 as=0.63u ad=0.63u
.ENDS bias_l1_pinv_2

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=13 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=13 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

.SUBCKT bias_l1_pinv_4
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 36
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=13 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=13 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
.ENDS bias_l1_pinv_4

.SUBCKT bias_l1_rom_precharge_driver
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* sizes: [1, 1, 4, 12, 36]
Xbuf_inv1
+ A Zb1_int vdd gnd
+ bias_l1_pinv
Xbuf_inv2
+ Zb1_int Zb2_int vdd gnd
+ bias_l1_pinv
Xbuf_inv3
+ Zb2_int Zb3_int vdd gnd
+ bias_l1_pinv_2
Xbuf_inv4
+ Zb3_int Zb4_int vdd gnd
+ bias_l1_pinv_3
Xbuf_inv5
+ Zb4_int Z vdd gnd
+ bias_l1_pinv_4
.ENDS bias_l1_rom_precharge_driver

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=2 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=2 w=1.26 l=0.15 pd=2.82 ps=2.82 as=0.47u ad=0.47u

.SUBCKT bias_l1_pinv_0
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 2
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=2 w=1.26 l=0.15 pd=2.82 ps=2.82 as=0.47u ad=0.47u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=2 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u
.ENDS bias_l1_pinv_0

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=3 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=3 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u

.SUBCKT bias_l1_pinv_1
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 7
Xpinv_pmos Z A vdd vdd sky130_fd_pr__pfet_01v8 m=3 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
Xpinv_nmos Z A gnd gnd sky130_fd_pr__nfet_01v8 m=3 w=3.0 l=0.15 pd=6.30 ps=6.30 as=1.12u ad=1.12u
.ENDS bias_l1_pinv_1

.SUBCKT bias_l1_rom_clock_driver
+ A Z vdd gnd
* INPUT : A 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* sizes: [1, 1, 2, 7]
Xbuf_inv1
+ A Zb1_int vdd gnd
+ bias_l1_pinv
Xbuf_inv2
+ Zb1_int Zb2_int vdd gnd
+ bias_l1_pinv
Xbuf_inv3
+ Zb2_int Zb3_int vdd gnd
+ bias_l1_pinv_0
Xbuf_inv4
+ Zb3_int Z vdd gnd
+ bias_l1_pinv_1
.ENDS bias_l1_rom_clock_driver

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u

* spice ptx X{0} {1} sky130_fd_pr__pfet_01v8 m=1 w=1.12 l=0.15 pd=2.54 ps=2.54 as=0.42u ad=0.42u

* spice ptx X{0} {1} sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u

.SUBCKT bias_l1_rom_control_nand
+ A B Z vdd gnd
* INPUT : A 
* INPUT : B 
* OUTPUT: Z 
* POWER : vdd 
* GROUND: gnd 
* size: 1
Xpnand2_pmos1 vdd A Z vdd sky130_fd_pr__pfet_01v8 m=1 w=1.12 l=0.15 pd=2.54 ps=2.54 as=0.42u ad=0.42u
Xpnand2_pmos2 Z B vdd vdd sky130_fd_pr__pfet_01v8 m=1 w=1.12 l=0.15 pd=2.54 ps=2.54 as=0.42u ad=0.42u
Xpnand2_nmos1 Z B net1 gnd sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u
Xpnand2_nmos2 net1 A gnd gnd sky130_fd_pr__nfet_01v8 m=1 w=0.74 l=0.15 pd=1.78 ps=1.78 as=0.28u ad=0.28u
.ENDS bias_l1_rom_control_nand

.SUBCKT bias_l1_rom_control_logic
+ clk_in CS prechrg clk_out vdd gnd
* INPUT : clk_in 
* INPUT : CS 
* OUTPUT: prechrg 
* OUTPUT: clk_out 
* POWER : vdd 
* GROUND: gnd 
Xclk_driver
+ clk_in clk_out vdd gnd
+ bias_l1_rom_clock_driver
Xcontrol_nand
+ CS clk_out pre_drive vdd gnd
+ bias_l1_rom_control_nand
Xprecharge_driver
+ pre_drive prechrg vdd gnd
+ bias_l1_rom_precharge_driver
.ENDS bias_l1_rom_control_logic

.SUBCKT bias_l1
+ clk0 cs0 addr0[0] addr0[1] addr0[2] addr0[3] addr0[4] dout0[0]
+ dout0[1] dout0[2] dout0[3] dout0[4] dout0[5] dout0[6] dout0[7]
+ dout0[8] dout0[9] dout0[10] dout0[11] dout0[12] dout0[13] dout0[14]
+ dout0[15] dout0[16] dout0[17] dout0[18] dout0[19] dout0[20] dout0[21]
+ dout0[22] dout0[23] vccd1 vssd1
* INPUT : clk0 
* INPUT : cs0 
* INPUT : addr0[0] 
* INPUT : addr0[1] 
* INPUT : addr0[2] 
* INPUT : addr0[3] 
* INPUT : addr0[4] 
* OUTPUT: dout0[0] 
* OUTPUT: dout0[1] 
* OUTPUT: dout0[2] 
* OUTPUT: dout0[3] 
* OUTPUT: dout0[4] 
* OUTPUT: dout0[5] 
* OUTPUT: dout0[6] 
* OUTPUT: dout0[7] 
* OUTPUT: dout0[8] 
* OUTPUT: dout0[9] 
* OUTPUT: dout0[10] 
* OUTPUT: dout0[11] 
* OUTPUT: dout0[12] 
* OUTPUT: dout0[13] 
* OUTPUT: dout0[14] 
* OUTPUT: dout0[15] 
* OUTPUT: dout0[16] 
* OUTPUT: dout0[17] 
* OUTPUT: dout0[18] 
* OUTPUT: dout0[19] 
* OUTPUT: dout0[20] 
* OUTPUT: dout0[21] 
* OUTPUT: dout0[22] 
* OUTPUT: dout0[23] 
* POWER : vccd1 
* GROUND: vssd1 
Xrom_bit_array
+ bl_0 bl_1 bl_2 bl_3 bl_4 bl_5 bl_6 bl_7 bl_8 bl_9 bl_10 bl_11 bl_12
+ bl_13 bl_14 bl_15 bl_16 bl_17 bl_18 bl_19 bl_20 bl_21 bl_22 bl_23
+ bl_24 bl_25 bl_26 bl_27 bl_28 bl_29 bl_30 bl_31 bl_32 bl_33 bl_34
+ bl_35 bl_36 bl_37 bl_38 bl_39 bl_40 bl_41 bl_42 bl_43 bl_44 bl_45
+ bl_46 bl_47 bl_48 bl_49 bl_50 bl_51 bl_52 bl_53 bl_54 bl_55 bl_56
+ bl_57 bl_58 bl_59 bl_60 bl_61 bl_62 bl_63 bl_64 bl_65 bl_66 bl_67
+ bl_68 bl_69 bl_70 bl_71 bl_72 bl_73 bl_74 bl_75 bl_76 bl_77 bl_78
+ bl_79 bl_80 bl_81 bl_82 bl_83 bl_84 bl_85 bl_86 bl_87 bl_88 bl_89
+ bl_90 bl_91 bl_92 bl_93 bl_94 bl_95 wl_0 wl_1 wl_2 wl_3 wl_4 wl_5 wl_6
+ wl_7 precharge vccd1 vssd1
+ bias_l1_rom_base_array
Xrom_row_decoder
+ addr0[2] addr0[3] addr0[4] wl_0 wl_1 wl_2 wl_3 wl_4 wl_5 wl_6 wl_7
+ clk_int clk_int vccd1 vssd1
+ bias_l1_rom_row_decode
Xrom_control
+ clk0 cs0 precharge clk_int vccd1 vssd1
+ bias_l1_rom_control_logic
Xrom_column_mux
+ bl_b_0 bl_b_1 bl_b_2 bl_b_3 bl_b_4 bl_b_5 bl_b_6 bl_b_7 bl_b_8 bl_b_9
+ bl_b_10 bl_b_11 bl_b_12 bl_b_13 bl_b_14 bl_b_15 bl_b_16 bl_b_17
+ bl_b_18 bl_b_19 bl_b_20 bl_b_21 bl_b_22 bl_b_23 bl_b_24 bl_b_25
+ bl_b_26 bl_b_27 bl_b_28 bl_b_29 bl_b_30 bl_b_31 bl_b_32 bl_b_33
+ bl_b_34 bl_b_35 bl_b_36 bl_b_37 bl_b_38 bl_b_39 bl_b_40 bl_b_41
+ bl_b_42 bl_b_43 bl_b_44 bl_b_45 bl_b_46 bl_b_47 bl_b_48 bl_b_49
+ bl_b_50 bl_b_51 bl_b_52 bl_b_53 bl_b_54 bl_b_55 bl_b_56 bl_b_57
+ bl_b_58 bl_b_59 bl_b_60 bl_b_61 bl_b_62 bl_b_63 bl_b_64 bl_b_65
+ bl_b_66 bl_b_67 bl_b_68 bl_b_69 bl_b_70 bl_b_71 bl_b_72 bl_b_73
+ bl_b_74 bl_b_75 bl_b_76 bl_b_77 bl_b_78 bl_b_79 bl_b_80 bl_b_81
+ bl_b_82 bl_b_83 bl_b_84 bl_b_85 bl_b_86 bl_b_87 bl_b_88 bl_b_89
+ bl_b_90 bl_b_91 bl_b_92 bl_b_93 bl_b_94 bl_b_95 word_sel_0 word_sel_1
+ word_sel_2 word_sel_3 rom_out_prebuf_0 rom_out_prebuf_1
+ rom_out_prebuf_2 rom_out_prebuf_3 rom_out_prebuf_4 rom_out_prebuf_5
+ rom_out_prebuf_6 rom_out_prebuf_7 rom_out_prebuf_8 rom_out_prebuf_9
+ rom_out_prebuf_10 rom_out_prebuf_11 rom_out_prebuf_12
+ rom_out_prebuf_13 rom_out_prebuf_14 rom_out_prebuf_15
+ rom_out_prebuf_16 rom_out_prebuf_17 rom_out_prebuf_18
+ rom_out_prebuf_19 rom_out_prebuf_20 rom_out_prebuf_21
+ rom_out_prebuf_22 rom_out_prebuf_23 vssd1
+ bias_l1_rom_column_mux_array
Xrom_column_decoder
+ addr0[0] addr0[1] word_sel_0 word_sel_1 word_sel_2 word_sel_3
+ precharge precharge vccd1 vssd1
+ bias_l1_rom_column_decode
Xrom_bitline_inverter
+ bl_0 bl_1 bl_2 bl_3 bl_4 bl_5 bl_6 bl_7 bl_8 bl_9 bl_10 bl_11 bl_12
+ bl_13 bl_14 bl_15 bl_16 bl_17 bl_18 bl_19 bl_20 bl_21 bl_22 bl_23
+ bl_24 bl_25 bl_26 bl_27 bl_28 bl_29 bl_30 bl_31 bl_32 bl_33 bl_34
+ bl_35 bl_36 bl_37 bl_38 bl_39 bl_40 bl_41 bl_42 bl_43 bl_44 bl_45
+ bl_46 bl_47 bl_48 bl_49 bl_50 bl_51 bl_52 bl_53 bl_54 bl_55 bl_56
+ bl_57 bl_58 bl_59 bl_60 bl_61 bl_62 bl_63 bl_64 bl_65 bl_66 bl_67
+ bl_68 bl_69 bl_70 bl_71 bl_72 bl_73 bl_74 bl_75 bl_76 bl_77 bl_78
+ bl_79 bl_80 bl_81 bl_82 bl_83 bl_84 bl_85 bl_86 bl_87 bl_88 bl_89
+ bl_90 bl_91 bl_92 bl_93 bl_94 bl_95 bl_b_0 bl_b_1 bl_b_2 bl_b_3 bl_b_4
+ bl_b_5 bl_b_6 bl_b_7 bl_b_8 bl_b_9 bl_b_10 bl_b_11 bl_b_12 bl_b_13
+ bl_b_14 bl_b_15 bl_b_16 bl_b_17 bl_b_18 bl_b_19 bl_b_20 bl_b_21
+ bl_b_22 bl_b_23 bl_b_24 bl_b_25 bl_b_26 bl_b_27 bl_b_28 bl_b_29
+ bl_b_30 bl_b_31 bl_b_32 bl_b_33 bl_b_34 bl_b_35 bl_b_36 bl_b_37
+ bl_b_38 bl_b_39 bl_b_40 bl_b_41 bl_b_42 bl_b_43 bl_b_44 bl_b_45
+ bl_b_46 bl_b_47 bl_b_48 bl_b_49 bl_b_50 bl_b_51 bl_b_52 bl_b_53
+ bl_b_54 bl_b_55 bl_b_56 bl_b_57 bl_b_58 bl_b_59 bl_b_60 bl_b_61
+ bl_b_62 bl_b_63 bl_b_64 bl_b_65 bl_b_66 bl_b_67 bl_b_68 bl_b_69
+ bl_b_70 bl_b_71 bl_b_72 bl_b_73 bl_b_74 bl_b_75 bl_b_76 bl_b_77
+ bl_b_78 bl_b_79 bl_b_80 bl_b_81 bl_b_82 bl_b_83 bl_b_84 bl_b_85
+ bl_b_86 bl_b_87 bl_b_88 bl_b_89 bl_b_90 bl_b_91 bl_b_92 bl_b_93
+ bl_b_94 bl_b_95 vccd1 vssd1
+ bias_l1_rom_bitline_inverter
Xrom_output_inverter
+ rom_out_prebuf_0 rom_out_prebuf_1 rom_out_prebuf_2 rom_out_prebuf_3
+ rom_out_prebuf_4 rom_out_prebuf_5 rom_out_prebuf_6 rom_out_prebuf_7
+ rom_out_prebuf_8 rom_out_prebuf_9 rom_out_prebuf_10 rom_out_prebuf_11
+ rom_out_prebuf_12 rom_out_prebuf_13 rom_out_prebuf_14
+ rom_out_prebuf_15 rom_out_prebuf_16 rom_out_prebuf_17
+ rom_out_prebuf_18 rom_out_prebuf_19 rom_out_prebuf_20
+ rom_out_prebuf_21 rom_out_prebuf_22 rom_out_prebuf_23 dout0[0]
+ dout0[1] dout0[2] dout0[3] dout0[4] dout0[5] dout0[6] dout0[7]
+ dout0[8] dout0[9] dout0[10] dout0[11] dout0[12] dout0[13] dout0[14]
+ dout0[15] dout0[16] dout0[17] dout0[18] dout0[19] dout0[20] dout0[21]
+ dout0[22] dout0[23] vccd1 vssd1
+ bias_l1_rom_output_buffer
.ENDS bias_l1
