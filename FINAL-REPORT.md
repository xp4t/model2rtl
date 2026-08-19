# model2rtl — final technical report

> model2rtl demonstrates that a trained quantized neural network can be compiled into a portable RTL implementation using a shared Multiply-Select-Add architecture, verified behaviourally and after independent FPGA-oriented and generic/ASIC-oriented synthesis, with an optional ASIC physical ROM representation of its parameters.
>
> The claim covers the demonstrated MNIST 784-32-10 MLP only. It is not a claim of production ASIC readiness, timing closure, full-chip physical implementation, DRC- or LVS-clean macros, arbitrary-model compilation, or reproduction of any proprietary implementation.

| Stage | Scope | Status |
|---|---|---|
| 0 | training, quantization, integer golden model, arithmetic contract | **PASS** |
| 1 | weight-independent Multiply-Select-Add compute fabric | **PASS** |
| 2 | two interchangeable parameter-storage backends | **PARTIAL** |
| 3 | behavioral RTL verification against the integer golden model | **PASS** |
| 4 | dual-target synthesis portability + gate-level verification | **PASS** |
| 5 | physical OpenROM generation | **PASS** |
| 5 | physical DRC/LVS signoff | **UNVERIFIED** |

Stage 2 closed as PARTIAL because two of the four logical memory shapes could not be built by the installed OpenROM at that time. Stage 5 completed them under approved physical transformations; the Stage-2 verdict is left as it was recorded rather than restated.

---

## 1. Project summary

**Input** — a trained MNIST MLP, topology **784 -> 32 -> ReLU -> 10**, quantized to **4-bit weight indices** (16 levels) and **uint8 activations**.

**Output** — portable synthesizable Verilog-2001 that reproduces the integer model bit-exactly.

The architectural idea, per input activation `x_i`:

```
compute x_i * every one of the 16 alphabet levels   -- once
        |
share those 16 products across all active output neurons
        |
select the one each synapse needs, using its 4-bit weight index
        |
accumulate
```

Execution is **input-serial, output-parallel**. One 16-product bank is reused across all neurons, across input cycles and across both layers.

## 2. Public prior-art / IP note

This project explores a digital RTL interpretation of publicly disclosed high-level Multiply-Select-Add ideas associated with public Taalas patent material. No Taalas source code, netlist, layout or transistor-level mask-ROM detail was used, consulted or reproduced, and nothing here is claimed to be equivalent to Taalas hardware.

## 3. Quantization results

| Metric | Value |
|---|---|
| Float test accuracy | 96.52% |
| Quantized integer test accuracy | 96.45% |
| Accuracy change | **quantization loses 0.07 percentage points of test accuracy relative to float** |

The integer model is the **only** oracle used anywhere in this project. Keras float output is a reference number and was never used to check RTL arithmetic.

| Contract item | Value |
|---|---|
| weight alphabet | `-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7` |
| weight index | 4 bits |
| activations | uint8, zero point 0, range [0, 255] |
| requantization | `hidden: h = clamp((max(acc1, 0) + 128) >> 8, 0, 255); output: none (raw signed logits)` |
| rounding | round-half-up (add 1 << (shift-1), then arithmetic right shift) |
| saturation | clamp to [0, 255] (unsigned 8-bit) |
| prediction | argmax over the 10 signed logits; lowest index wins ties |

There is **no multiplicative requantization scale anywhere in the datapath** — the only requantization operator is a fixed power-of-two shift of 8. That is what makes the fabric provably free of trained values.

| Synapses | Count |
|---|---|
| layer 1 (784 x 32) | 25088 |
| layer 2 (32 x 10) | 320 |
| **total** | **25408** |

**All 16 levels are used** in both layers — no level is dead: confirmed.

| Level | Layer 1 | Layer 2 |
|---|---|---|
| -8 | 228 | 23 |
| -7 | 204 | 11 |
| -6 | 312 | 8 |
| -5 | 569 | 21 |
| -4 | 1013 | 18 |
| -3 | 1696 | 24 |
| -2 | 2572 | 16 |
| -1 | 3702 | 29 |
| +0 | 4201 | 22 |
| +1 | 3876 | 32 |
| +2 | 2868 | 28 |
| +3 | 1795 | 28 |
| +4 | 997 | 26 |
| +5 | 523 | 16 |
| +6 | 279 | 10 |
| +7 | 253 | 8 |

Weight saturation during quantization-aware training: layer 1 **0.92%**, layer 2 **7.5%**. Weights clipped to the alphabet extremes during quantization-aware training. layer 2 saturates more often because it has only 320 synapses and a wider dynamic range per synapse; final integer accuracy is unaffected at 96.45%.

## 4. Architecture

Three different counts get confused easily, so they are kept apart:

| Quantity | Count | Kind |
|---|---|---|
| naive fully spatial synapse multiplications | 25408 | source-level operation count |
| fully spatial MSA product generators | 13056 | source-level operation count |
| **implemented** active shared product expressions | **16** | source-level operation count |

The implemented count is 16 because execution is input-serial: the same bank is recomputed each cycle for the current activation instead of being unrolled across all inputs. **Area and parallelism are exchanged for latency: one inference costs 864 cycles instead of one.**

None of these three is a physical multiplier count — see section 11.

| Latency | Value |
|---|---|
| nominal cycles per inference | **864** (`n_in + 2*n_hidden + n_out + 6`) |
| at an assumed 50 MHz | 17.28 us |
| at an assumed 100 MHz | 8.64 us |

**These are architectural calculations, not measured timing.** These are cycle counts divided by an assumed clock. No timing analysis was run at any stage and no Fmax is claimed.

Structure confirmed in the elaborated netlist: 16 `$mul` cells and 42 selector instances — exactly K products shared by every neuron of the active layer.

## 5. Portable RTL

| Property | Value |
|---|---|
| file | `rtl/mnist_mlp_fabric.v` |
| SHA-256 | `7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c` |
| language | Verilog-2001, vendor-neutral |
| clocks / resets | 1 clock, 1 synchronous |
| vendor primitives, IP cores, tool pragmas | none |

**The fabric contains no trained value.** This is proved, not asserted: regenerating it with a completely different weight set and with different biases produces a byte-identical file.

| Generation input | Fabric SHA-256 |
|---|---|
| trained weights | `7757362642b37fd0044bb7b323467116` |
| alternate weight set | `7757362642b37fd0044bb7b323467116` |
| alternate biases | `7757362642b37fd0044bb7b323467116` |
| **identical** | **True** |

The fabric has not changed a byte since Stage 1, across three subsequent stages of verification, synthesis and physical work.

## 6. Parameter-storage backends

Both backends sit behind **one fixed logical interface** with identical timing semantics, so the fabric cannot tell which is attached. Backend choice is a build-time source-list decision: no runtime mux, no parameter.

### Portable

`rtl/mnist_mlp_params_portable.v` — pure synthesizable Verilog-2001, synchronous one-cycle enable-gated read, case/constant representation; the same source feeds both synthesis targets

### OpenROM physical (ASIC / SKY130 only)

`rtl/mnist_mlp_params_openrom_phys.v`. The installed OpenROM cannot express a 22- or 17-bit word (`word_size` is in **bytes**) and cannot route a 784 x 128 array, so the parameters get a *physical* representation distinct from the logical one:

| Logical memory | Logical | Physical | Transformation |
|---|---|---|---|
| `weights_l1` | 784 x 128 | 4 banks of 784 x 32 | banked into 4 parallel macros of 784 x 32; all banks share one address and are read together, so the external latency stays one cycle |
| `weights_l2` | 32 x 40 | 32 x 40 | identity: already byte granular |
| `bias_l1` | 32 x 22 signed | 32 x 24 signed | sign extended 22 -> 24 bits |
| `bias_l2` | 10 x 17 signed | 10 x 24 signed | sign extended 17 -> 24 bits, then recovered and sign extended 17 -> 22 on the bus |

**All transformations are PHYSICAL REPRESENTATION ONLY. The logical memories, the bit packing and the fabric interface never changed.**

## 7. Behavioral verification

500 MNIST test images, the first 500 of the official test set in order, no filtering of any kind.

| | Portable | OpenRAM behavioural |
|---|---|---|
| hidden activations compared | 16000 | 16000 |
| logits compared | 5000 | 5000 |
| **hidden mismatches** | **0** | **0** |
| **logit mismatches** | **0** | **0** |
| **prediction mismatches** | **0** | **0** |

Cycle-level internal checkpointing over 20 images: **178840 checks, 0 failures** — every accumulator update, every requantization, every ROM word checked against the address issued one cycle earlier.

| Stress test | Result |
|---|---|
| input stall patterns (none / periodic / pseudo-random) | 3 patterns, 0 mismatches; only latency changes |
| synchronous reset | 6 points, 0 stale-state failures |
| back-to-back inferences | 500 consecutive, 0 mismatches |
| argmax including ties | 15 cases, 0 failures (lowest index wins, matching numpy.argmax) |
| arithmetic edge cases | 3 + 5 cases, 0 failures |
| second parameter set on the unchanged fabric | 8 vectors, 0 mismatches, fabric identical |
| model-specific shortcut scan | clean |

## 8. Dual-target synthesis portability

**The exact same RTL source was synthesized through an FPGA-oriented Yosys flow and a generic/ASIC-oriented Yosys flow with no source patching, and BOTH synthesized netlists were gate-level simulated against the Stage-0 integer golden model.**

| Invariant | Result |
|---|---|
| identical source hashes on both targets | **True** |
| source patched before synthesis | **False** |

| Post-synthesis gate-level result | FPGA netlist | Generic netlist |
|---|---|---|
| images | 500 | 500 |
| logits compared | 5000 | 5000 |
| **logit mismatches** | **0** | **0** |
| **prediction mismatches** | **0** | **0** |
| cycles per inference | [864] | [864] |

The two netlists also agree with each other bit for bit: 0 logit, 0 prediction, 0 cycle-count differences.

**This proves synthesis portability and post-synthesis functional equivalence for this RTL. It does NOT prove place-and-route or timing portability; neither was run.**

## 9. FPGA-oriented synthesis result

Target: **ice40** (`synth_ice40`). synth_ice40 is present in the installed Yosys and the matching official simulation library <datdir>/ice40/cells_sim.v exists and is complete, so the synthesized netlist can be simulated with the vendor-equivalent cell models rather than hand-written stand-ins.  ECP5 was therefore not needed.

| Resource | Count |
|---|---|
| total cells | 9079 |
| `SB_LUT4` | 6429 |
| flip-flops | 1614 |
| `SB_CARRY` | 1004 |
| `SB_RAM40_4K` | 32 |
| `SB_MAC16` (DSP) | **0** |

The interpretation that matters: **inferred as 32 SB_RAM40_4K block RAMs holding 131072 bits of INIT data; the ROM did not become LUT or mux logic** — no FPGA-specific memory RTL, no vendor macro and no synthesis pragma was needed to get there.

This is **not** a completed FPGA implementation: no place-and-route, no device fit, no bitstream and no timing analysis were run.

## 10. Generic / ASIC-oriented synthesis result

| Cell | Count |
|---|---|
| `$_AND_` | 20159 |
| `$_DFF_P_` | 1742 |
| `$_MUX_` | 1351 |
| `$_NOT_` | 2439 |
| `$_OR_` | 18603 |
| `$_XOR_` | 1413 |
| **total** | **45707** |

Multiplier / arithmetic cells remaining: **0**.

No physical ASIC area is claimed from a generic gate count. The generic vocabulary has no memory primitive, so the generic gate vocabulary has no memory primitive, so the ROM was synthesized into constant combinational logic

## 11. What synthesis did to the constant multiplications

| | Value |
|---|---|
| `*` operators in the source | 16 |
| multiplier / DSP cells in the FPGA netlist | **0** |
| multiplier / arithmetic cells in the generic netlist | **0** |

Each of the 16 products has a fixed small integer constant as one operand, so synthesis replaces them with wiring, shifts, negation, add/subtract and LUT/carry logic, and fuses the shared product logic into the selector logic.

Where the FPGA flow preserved the product wire names, the drivers show it directly:

| Product | Driver |
|---|---|
| `prod_08` | `12'h000` |
| `prod_09` | `{ 4'h0, x[7:2], bank[26], bank[3] }` |
| `prod_10` | `{ 3'h0, x[7:2], bank[26], bank[3], 1'h0 }` |
| `prod_12` | `{ 2'h0, x[7:2], bank[26], bank[3], 2'h0 }` |
| `prod_00` | `{ bank[11:3], 3'h0 }` |

`x * 0` folded to a literal zero; `x * 1`, `x * 2` and `x * 4` became pure wiring; `x * -8` is a shift of a shared negated value.

> **Correct wording:** The architecture exposes only sixteen constant-weight product alternatives per activation, and synthesis further eliminates explicit multiplier hardware.
>
> **Wording to avoid:** 'we reduced 25,408 physical multipliers to 16 physical multipliers' -- that is NOT what synthesis showed. The three operation counts are source-level quantities and the synthesized results are a different kind of measurement.

## 12. Physical OpenROM experiment

| Macro | Shape | Views | Bits verified | GDS bbox |
|---|---|---|---|---|
| `weights_l1_b0` | 784 x 32 | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 53668.6 um² |
| `weights_l1_b1` | 784 x 32 | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 53668.6 um² |
| `weights_l1_b2` | 784 x 32 | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 53668.6 um² |
| `weights_l1_b3` | 784 x 32 | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 53668.6 um² |
| `weights_l2` | 32 x 40 | gds, lef, log, lvs.sp, py, sp, v | **1280 / 1280** | 16498.6 um² |
| `bias_l1` | 32 x 24 | gds, lef, log, lvs.sp, py, sp, v | **768 / 768** | 10268.8 um² |
| `bias_l2` | 10 x 24 | gds, lef, log, lvs.sp, py, sp, v | **240 / 240** | 10939.9 um² |
| **total** | | | **102640 / 102640** | **252381.6 um²** |

Layer-1 weights: four 784 x 32 banks, total **214674.4 um²**. Bounding boxes measured from the GDS with KLayout, hierarchy resolved — never from a log line.

The central proof is that the macros hold the model's bits. Every programmed cell was read back out of the **generated SPICE netlist** and compared against the physical image:

| Check | Count | Mismatches |
|---|---|---|
| programmed cells | 102640 | **0** |
| logical rows rebuilt from the macros | 858 | **0** |
| weight indices after unpacking | 25408 | **0** |
| bias values through the full path | 42 | **0** |

The physical form has **zero functional effect**: over the same 500 images the physical backend produced 0 hidden, 0 logit and 0 prediction mismatches, still [864] cycles per inference.

## 13. Physical signoff

| Verdict | Status |
|---|---|
| physical generation | **PASS** |
| physical signoff | **UNVERIFIED** |

The reason is the environment, not the macros. A control was run under identical settings — OpenRAM's **own** upstream reference ROM:

| | DRC | LVS |
|---|---|---|
| **control (upstream reference ROM)** | **830 errors** | **MISMATCH** |
| `weights_l1_b0` | 1244 errors | MISMATCH |
| `weights_l1_b1` | 1244 errors | MISMATCH |
| `weights_l1_b2` | 1244 errors | MISMATCH |
| `weights_l1_b3` | 1244 errors | MISMATCH |
| `weights_l2` | 780 errors | MISMATCH |
| `bias_l1` | 500 errors | MISMATCH |
| `bias_l2` | 615 errors | MISMATCH |

Because the reference macro fails here too, **no DRC or LVS result produced in this environment is evidence about these macros in either direction**. No generated macro is called DRC-clean, LVS-clean or signoff-ready.

## 14. Area results

| Storage implementation | Measurement | Area |
|---|---|---|
| OpenROM hard macros (7) | GDS bounding boxes, summed | **252381.6 um²** |
| portable backend on SKY130 | liberty cell-area sum | **58335.9 um²** |
| | of which sequential | 4144.0 um² (138 cells) |
| | of which combinational | 54192.0 um² (9268 cells) |
| raw ratio | OpenROM / portable | **4.33x** |

**That ratio is a raw storage-implementation comparison, not a finished-block physical area ratio.** The two numbers are different kinds of area:

- **OpenROM**: hard-macro GDS bounding box, measured with KLayout (hierarchy resolved). It already contains the decoders, column mux, precharge and the supply ring.
- **portable**: synthesized standard-cell area: the sum of the sky130_fd_sc_hd liberty cell areas after ABC mapping. It excludes placement utilisation and routing overhead.

The portable figure excludes placement whitespace, routing and utilization overhead, because no place-and-route was run. The macro figure is a raw sum of bounding boxes, not a floorplanned area; no placement density is claimed.

## 15. Storage crossover

| Point | Bits | OpenROM bbox | Portable cell area | Ratio | Smaller |
|---|---|---|---|---|---|
| 32x32 | 1024 | 13275.3 um² | 1964.4 um² | 6.76 | portable |
| 64x32 | 2048 | 15037.0 um² | 2916.5 um² | 5.16 | portable |
| 128x32 | 4096 | 18466.5 um² | 4773.3 um² | 3.87 | portable |
| 256x32 | 8192 | 25266.8 um² | 8165.3 um² | 3.09 | portable |
| 512x32 | 16384 | 38879.4 um² | 13753.2 um² | 2.83 | portable |
| 784x32 | 25088 | 53668.6 um² | 18433.9 um² | 2.91 | portable |
| 1568x32 | 50176 | 92011.5 um² | 30934.7 um² | 2.97 | portable |

Measured range: **1024 to 50176 bits**. At every measured point the portable mapped-cell area is smaller than the OpenROM bounding box, and the ratio flattens near **~2.9x** at the larger points. **No crossover was measured.**

This does **not** establish that a hard ROM never wins. The experiment proves only that *no OpenROM area advantage was observed over the measured range with this tool and library configuration*. No crossover point is extrapolated.

Contextual arithmetic, **not a measurement**: a placed portable block occupies cell area divided by its utilization, so at the deepest measured point the two would break even only if the portable block placed at **34% utilization or worse**.

## 16. What worked

- **The weight-independence discipline.** Fixing the arithmetic contract analytically before writing any RTL, with no multiplicative requantization scale, made the fabric provably free of trained values — byte-identical under substituted weights and biases, and unchanged for the rest of the project.
- **One canonical parameter image.** Both backends consume the same hashed images, so it is structurally impossible to physically build one dataset while testing another.
- **The integer golden model as sole oracle.** Every stage compared against the same NumPy integer model, which is why behavioral, post-synthesis and physical results are directly comparable.
- **Dual-target portability.** The same four files synthesized through two independent flows with zero source changes and zero post-synthesis mismatches.
- **Automatic BRAM inference.** The portable case-ROM mapped into 32 iCE40 block RAMs with no FPGA-specific RTL.
- **Physical content verification.** Deriving the OpenROM bit-cell map empirically and checking every programmed cell in the SPICE netlist turned 'the macro was generated' into 'the macro holds exactly these bits'.

## 17. What did not work

- **OpenROM could not build two of the four logical shapes directly.** `word_size` is expressed in bytes, so 22- and 17-bit words are not expressible; and the 784 x 128 array fails in `signal_escape_router`. Both needed approved physical transformations rather than a tool fix.
- **DRC and LVS are unusable in this environment.** OpenRAM's own reference macro fails, so no physical-verification result here means anything. This was not repaired; it was measured and reported.
- **The hard ROM did not win on area.** Across the whole measured range the synthesized standard-cell storage was smaller. That is the opposite of the expected motivation for a hard ROM and is reported as measured.
- **`words_per_row = 1` crashes the tool**, and several folding choices fail per shape; each usable value had to be found by measurement rather than assumption.
- **Yosys's per-cell-type area column is a display value** printed in 3-significant-digit scientific notation for large counts. Summing it produced a wrong total until the exact figures Yosys prints separately were used instead.

## 18. Limitations

- MNIST only; no other dataset or task was attempted.
- The compiler is fixed to the 784-32-10 topology it was written for; there is no general topology support.
- Weights are 4-bit, 16 fixed levels; activations are uint8.
- No convolution support of any kind.
- No ONNX or TFLite ingestion exists; the model comes from this project's own training script.
- Input-serial execution trades latency for area: 864 cycles per inference.
- No FPGA place-and-route, no device fit, no bitstream, no FPGA timing analysis.
- No ASIC place-and-route, no floorplan, no full-chip physical implementation, no ASIC timing analysis.
- OpenROM physical signoff is UNVERIFIED: the environment's own control macro fails DRC and LVS.
- The hard ROM did not beat portable synthesized storage in area anywhere in the measured range.
- The physical banking scheme is specific to the demonstrated ROM shape; it is not a general banking compiler.
- No claim is made of reproducing any proprietary implementation.

### Not claimed

- No claim of production ASIC readiness.
- No claim of timing closure or any maximum clock frequency.
- No claim of full-chip physical implementation.
- No claim of DRC-clean OpenROM macros.
- No claim of LVS-clean OpenROM macros.
- No claim of general arbitrary-model compilation.
- No claim of support beyond the demonstrated MNIST MLP.
- No claim of reproduction of any proprietary implementation.

## 19. Reproducibility

| Tool | Version / provenance |
|---|---|
| Python | 3.11.11 |
| Yosys | Yosys 0.68+ |
| Icarus Verilog | Icarus Verilog version 13.0 (stable) (v13_0) |
| OpenRAM | `b2b069ce119d1488cbe6883b2240bceb5c7ce29a`, branch `stable`, tracked files modified: False |
| PDK | installed with ciel into PDK_ROOT; the old ~/.volare/sky130A layout does not exist on this machine (`/home/rithwik/pdk`) |
| magic | 8.3.486 |
| netgen | Netgen 1.5.323 compiled on Tue Aug 18 15:41:47 IST 2026 |
| KLayout | KLayout 0.28.17 |
| SKY130 liberty | `sky130_fd_sc_hd__tt_025C_1v80.lib` |

**This environment is NOT one-click portable. The functional flow needs only Python, Yosys and Icarus; the physical OpenROM flow additionally needs a user-space OpenRAM checkout, the SKY130 PDK, magic, netgen and KLayout at the exact paths recorded above.**

### Lightweight functional flow (Python + Yosys + Icarus only)

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[train,test]"

.venv/bin/python scripts/train_mnist_mlp.py --sweep-hidden-shift   # Stage 0
.venv/bin/python scripts/gen_compute_fabric.py                     # Stage 1
.venv/bin/python scripts/verify_stage1.py
.venv/bin/python scripts/gen_weight_rom_portable.py                # Stage 2
.venv/bin/python scripts/verify_stage3.py --images 500             # Stage 3
.venv/bin/python scripts/synth_stage4.py                           # Stage 4
.venv/bin/python scripts/verify_stage4.py --images 500
```

### Heavy physical flow (adds OpenRAM + SKY130 + magic + netgen + KLayout)

```bash
source build/openram/openram_env.sh
.venv/bin/python scripts/gen_weight_rom_openram.py                 # Stage 2 backend B
.venv/bin/python scripts/gen_openrom_stage5.py                     # Stage 5
.venv/bin/python scripts/gen_openrom_phys_rtl.py
.venv/bin/python scripts/sweep_stage5.py
.venv/bin/python scripts/verify_physical_stage5.py
.venv/bin/python scripts/verify_stage5.py --images 500
```

Seed 1234; MNIST split `MNIST train[:55000] / train[55000:60000] / official test`. Determinism was checked, not assumed: both Stage-4 synthesis flows produce byte-identical netlists when re-run from clean directories.

## 20. Future work

Ranked by how much they extend what exists, not by difficulty:

1. generic model importer (ONNX / TFLite)
2. arbitrary dense-layer topology compiler
3. configurable K, activation width and layer sizes
4. convolution lowering
5. architecture selection: fully spatial, input-serial, tiled
6. FPGA place-and-route plus timing analysis
7. full SKY130 ASIC implementation
8. a trustworthy OpenROM DRC/LVS environment
9. memory-architecture exploration: portable ROM, SRAM, hard ROM, banking
10. model and architecture co-optimization

None of these is implemented.

## 21. Test evolution

| Stage | Cumulative tests |
|---|---|
| Stage 0 | 35 |
| Stage 1 | 79 |
| Stage 2 | 137 |
| Stage 3 | 174 |
| Stage 4 | 245 |
| Stage 5 | 381 |
| **final (Stage 6 run)** | **408 passed, 0 failed, 0 skipped** |

Cumulative pytest count at the close of each stage. The per-stage figures are the baselines recorded at the time; the final figure is measured by the Stage-6 run.

---

## Cross-stage consistency

Every number in this report was extracted programmatically from the six stage reports. Quantities recorded by more than one stage were compared rather than reconciled: **13 checks, 0 disagreements**.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `model/mnist_weights_indices.npz` | `1e231ad80e12e1045bb2941f12a84b1f8f1fa6ff4e93c3f7cd2077ebb4337e46` |
| `model/quant_params.json` | `2ad884b42e797bb4400ecaa2f9de46da7aa16b5abf32fe21e77a657bdd82eec7` |
| `reports/stage0_quantization.json` | `c0c4fa1f89fe279559f82e429660d59327c3fbe1f607fc186d94611d8f6da9a0` |
| `reports/stage1_compute_fabric.json` | `9a7a501a89c15b42e00361c8096f184a6d7b9db5aa16342119aa3c921b282786` |
| `reports/stage2_parameter_backends.json` | `3ef8042d8134e8541961e105f9e585130b6bfbe91fb52cddce64e1f9447f798b` |
| `reports/stage3_behavioral_verification.json` | `d433742d54461c9d66677b49e9ce187e12383baf72c0856544ffd7f186b7518d` |
| `reports/stage4_dual_target_portability.json` | `6d5829c0f05aceae87e09e70f294dbaa8e1d93cdf3ed8be890e5f872c2174941` |
| `reports/stage5_openrom_physical.json` | `e24fb00fd59605dfab6eb539ad431e2a8c8761c890172abb1b96318c4c778f5b` |
| `rtl/mnist_mlp_fabric.v` | `7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c` |
| `rtl/mnist_mlp_params_openram.v` | `0e52cd13324b6b8fcec830440cb9018bfdc5d05a26a1e869be28a02ccbb6e395` |
| `rtl/mnist_mlp_params_openrom_phys.v` | `5d320cef91fe7c5c159d8b6ea717db781fa37ba2811b12bc3249e291d9abf24f` |
| `rtl/mnist_mlp_params_portable.v` | `d9c1aecd5f15872e1fb8011824d957766ad93f2b3598d2d9bc9df4f88dca9ebe` |
| `rtl/mnist_mlp_params_sel_openram.v` | `0e820585cb6230cbf39570d9f38269e9bbdd71c0fd2f6d43b35f6df0132d3cb0` |
| `rtl/mnist_mlp_params_sel_openrom_phys.v` | `b8126c459178284b9cac48e3fd3063958b7d178ac7674051325d148223298d3c` |
| `rtl/mnist_mlp_params_sel_portable.v` | `902994346f1ad992427c1d83dbb00395c8efe7689e0bd1c94d6dcc92015c814f` |
| `rtl/mnist_mlp_top.v` | `0763242015ce86e8b6edc3681d1e9834f5e9a5d3199f233bce0f3c17ae701eeb` |
| `src/model2rtl/contract.py` | `0fbe4877f7f49b9b8da6d3947a49ba7bab85e4b36ba011e4337f5fc3d3480b12` |
| `src/model2rtl/fabric.py` | `ae7e8d93660a6f141fdc9b1ee59130f7c93c0098c9995b66426d153913ff7981` |
| `src/model2rtl/golden.py` | `e10eb33a952c6ae5fd67ad33791985c3a62a7d5d25fd3b5edc13819cb20e5270` |
| `src/model2rtl/param_image.py` | `5a0e883f7e7216c9e910ba2c75310d80c095686cd6b325411f989be4d8563a76` |
| `src/model2rtl/param_verilog.py` | `3c89ad83caed752b3b4c19ea0d62b7c56b97febb74772ddb351aa24423e8026b` |
| `src/model2rtl/phys_image.py` | `4ff5d86b524296fa1dfa4906c4a9a4c7c2bbb2a3dfc804a35adf8e5998766ec7` |
| `src/model2rtl/phys_verilog.py` | `e5e62c1e5886a643b3bf0fb270a57ad0048ab2306231e01962e1317b55287727` |
| `src/model2rtl/storage.py` | `57618e982731c334bae76811d386b018e031b88f910fafad92a5656fdaed6b47` |
| `src/model2rtl/verilog_emit.py` | `4ee554f39c53185d9aeb2189e392ad6955c14c9bd449b0e58c0467621f225a97` |

