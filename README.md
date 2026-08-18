# model2rtl

**A compiler from a trained, quantized neural network to portable, synthesizable RTL for both FPGA and ASIC targets.**

> ## CURRENT STATUS: STAGE 2 — PARAMETER BACKENDS VERIFIED
>
> Stages 0 (training + integer golden model), 1 (the fixed Multiply-Select-Add
> compute fabric) and 2 (two interchangeable parameter-storage backends) are
> complete.
>
> `rtl/mnist_mlp_top.v` runs real MNIST images bit-exactly against the Stage-0
> integer golden model with **either** backend, and `rtl/mnist_mlp_fabric.v` is
> byte-for-byte unchanged from Stage 1.
>
> - **Portable backend** (`rtl/mnist_mlp_params_portable.v`): pure synthesizable
>   Verilog-2001, `case`/constant lookup. **FPGA and ASIC.** This is the default.
> - **OpenRAM/OpenROM backend** (`rtl/mnist_mlp_params_openram.v`): **ASIC /
>   SKY130 only**, no FPGA portability claimed. Physical macro generation is
>   **partial** — see the Stage-2 section for exactly which macros were built,
>   which are blocked by a tool limitation, and what DRC/LVS actually reported.
>
> **What does not exist yet:**
> - **No synthesis portability claim.** Only `read_verilog` / `hierarchy -check` /
>   `proc` / `check -assert` and Icarus compilation have been run. `synth_ice40`,
>   `synth_ecp5` and a generic ASIC synthesis flow have not.
> - **No FPGA gate-level verification.** None has been run.
> - **No ASIC gate-level verification.** None has been run.
> - **No clean DRC or LVS result** for any macro — including OpenRAM's own
>   reference macro, which also fails in this environment.
> - **No area, DSP, cell-area or timing number**, and no maximum clock frequency.
>
> `build/` holds generated artefacts only. Nothing here has been synthesized,
> placed, routed, or taped out.

---

## 1. Objective

Take a trained quantized MLP and emit synthesizable Verilog that implements a
**bit-exact integer inference specification**, portable across FPGA and ASIC
flows with no source changes.

The first supported network is an MNIST MLP:

```
784 uint8 inputs
  -> Dense(32)  4-bit weight indices
  -> ReLU + requantize to uint8
  -> Dense(10)  4-bit weight indices
  -> signed integer logits
  -> argmax
```

## 2. Multiply-Select-Add fabric (the architecture being targeted)

Weights are quantized to exactly **K = 16** levels, so every synapse stores only
a 4-bit index. For a given input activation `x_i` there are therefore only 16
distinct products it can ever participate in, no matter how many neurons it
feeds:

```
            x_i
             |
   +---------+---------+ ... +---------+     product bank (K = 16 generators)
   |         |         |     |         |
 x_i*a[0]  x_i*a[1]  x_i*a[2] ...   x_i*a[15]
   \_________\_________\_____/________/
                  |
        16:1 select, chosen by the synapse's 4-bit weight index
                  |
        accumulate into the destination neuron
```

The **product bank is shared across the complete fanout of that input**. There is
no multiplier per synapse.

### Source-level operator counts for this topology

| Layer | Inputs | Outputs | Naive multipliers | Shared product generators | Selectors (K:1) | Ratio naive/shared |
|-------|--------|---------|-------------------|---------------------------|-----------------|--------------------|
| 1     | 784    | 32      | 25,088            | 12,544                    | 25,088          | 2.000              |
| 2     | 32     | 10      | 320               | 512                       | 320             | 0.625              |
| Total |        |         | 25,408            | 13,056                    | 25,408          | 1.946              |

**Sharing is not universally cheaper.** In raw product-generator count, sharing
wins only when a layer's output fanout exceeds K:

- Layer 1: fanout 32 > K = 16, so sharing halves the product generators.
- Layer 2: fanout 10 < K = 16, so sharing **costs 1.6x more** product generators
  than the naive form. The crossover is at fanout = K.

**Source-level multiplier counts are not physical multiplier or DSP counts.**
Every product here has a constant 4-bit operand, so synthesis is free to
implement it as shifts, adds and negations, and a constant-weight naive
multiplier may collapse to almost nothing. Synthesized cell counts, DSP
inference and area are separate measurements and will be reported from actual
tool output in Stages 4 and 5 — not estimated from this table.

## 3. Public prior-art / IP note

This project explores a digital RTL interpretation of publicly disclosed
quantized Multiply-Select-Add concepts. It does not reproduce or claim to
implement proprietary Taalas circuit, mask-ROM, physical-design, or
manufacturing techniques.

The architectural inspiration comes from publicly disclosed high-level ideas in:

- **WO2025217724A1** — "Mask Programmable ROM using Shared Connections"
- the companion public patent application describing a
  **"Large Parameter Set Computation Accelerator"**

Only the publicly disclosed high-level idea is used here:

> precompute the products for the quantization alphabet -> select one by the
> stored parameter index -> accumulate.

This is a personal educational/demo implementation. It deliberately does **not**
attempt to reproduce proprietary physical implementation details, mask layouts,
transistor-level structures, confidential implementation details, or any
undocumented design information.

## 4. Integer golden-model philosophy

The RTL must implement a bit-exact integer specification, so the arithmetic
contract is fixed **before** any Verilog is written.

- `src/model2rtl/contract.py` defines the arithmetic contract analytically:
  alphabet, signedness, product widths, accumulator widths, bias format,
  requantization, rounding, saturation, ReLU semantics, logit format. Widths are
  **computed**, never guessed.
- `src/model2rtl/golden.py` is a pure-NumPy integer inference path. It performs
  no floating-point Dense operation: activation -> index -> alphabet lookup ->
  integer multiply -> widened integer accumulate -> bias -> requantize ->
  saturate -> activation.
- **Keras float predictions are not the RTL oracle.** The NumPy integer model
  is, for behavioral simulation, gate-level simulation and the physical ROM
  backend alike.

Training uses quantization-aware training whose forward graph simulates that
exact integer pipeline with straight-through estimators. The exported integer
model is then cross-checked against the TensorFlow graph and must agree on
**every logit of all 10,000 test images, bit for bit**, or the run fails.

## 5. The arithmetic contract

| Item | Value |
|------|-------|
| Input activation | `uint8`, range `[0, 255]`, zero-point 0, no rescaling (a raw MNIST pixel byte) |
| Weight index | `uint4`, values `0..15`, K = 16 |
| Weight alphabet | `alphabet[i] = i - 8`, i.e. the signed levels `-8 .. +7` (plain two's-complement int4) |
| Weight value | signed, 4 bits |
| Product | signed, 12 bits (`255 * -8 = -2040` .. `255 * 7 = 1785`) |
| Layer 1 dot product | signed, 22 bits (784 terms, `[-1599360, +1399440]`) |
| Layer 1 accumulator | signed, 23 bits (dot product + 22-bit bias) |
| Layer 2 dot product | signed, 17 bits (32 terms, `[-65280, +57120]`) |
| Layer 2 accumulator | signed, 18 bits (dot product + 17-bit bias) |
| Bias | signed integer **in the layer's accumulator domain**, added directly to the dot product with no pre-scaling. Width is defined as the layer's dot-product width — 22 bits (layer 1), 17 bits (layer 2) — so it too is derived from topology and alphabet, not from the trained model. Stored as `int32` in the NPZ and sign-extended |
| Hidden requantization | `h = clamp((max(acc1, 0) + 128) >> 8, 0, 255)` |
| Rounding | round-half-up: add `1 << (shift-1)`, then arithmetic right shift |
| Saturation | clamp to `[0, 255]` (unsigned 8-bit) |
| ReLU | applied to the **signed accumulator before the shift**, so the shifted operand is never negative and the shift direction is unambiguous |
| Output | raw signed logits, no requantization; `prediction = argmax(logits)`, lowest index wins ties |

### There is no multiplicative requantization scale anywhere

The only requantization operator in the datapath is a **fixed power-of-two
shift** (`HIDDEN_REQUANT_SHIFT = 8`), which is an architectural constant, not a
trained one. Consequently:

- No per-tensor scale, zero-point or multiplier constant derived from the
  trained model can leak into the compute fabric.
- The float scales `s_x`, `s_w`, `s_h` exist only as documentation of what the
  integers *mean*; they never appear in the datapath, so they cannot appear in
  the RTL.

The shift value was selected once by the `--sweep-hidden-shift` diagnostic and
then frozen. Shifts 5..10 all landed within ~1.9 percentage points on the
validation split, so the choice is not accuracy critical; 8 is used because it
is the largest shift that keeps the observed hidden activations inside `uint8`
with zero saturation, giving the cleanest hardware semantics.

## 6. Weight independence (the central design rule)

The future `rtl/mnist_mlp_fabric.v` must depend only on:

- topology (784 / 32 / 10)
- K = 16
- activation format (uint8)
- the fixed arithmetic contract above
- the fixed weight alphabet

and **must not** depend on any trained per-synapse value. Changing the trained
weight indices must not require regenerating the compute topology.

The split is enforced by the artefact layout:

| File | Contains | Fabric may depend on it? |
|------|----------|--------------------------|
| `model/quant_params.json` | the fixed contract: alphabet, widths, shift, limits, orientation | yes |
| `model/mnist_weights_indices.npz` | **model parameters only**: 4-bit synapse indices and integer biases | **no** — these belong to the weight ROM |

Stage-0 tests assert that `quant_params.json` contains no bulk tensor and no
per-synapse value, and that the computed contract is byte-identical when a
completely different random weight-index set is substituted.

## 7. Portability objective

The same two source files must synthesize unchanged through an FPGA-oriented
Yosys flow (`synth_ice40` / `synth_ecp5`) and a generic/ASIC-oriented Yosys
flow. Requirements for the emitted RTL: synthesizable Verilog-2001 subset, no
SystemVerilog, no vendor primitives, no vendor attributes, no IP cores, no
tool-specific pragmas, one clock, one synchronous reset, no latches, no
multiply-driven nets.

Weight storage sits behind a **single fixed logical interface** (`clk`, `addr`,
`data`) with identical documented timing semantics, so the top level cannot tell
which backend is underneath:

- **Backend A (default, portable):** pure synthesizable Verilog `case`/
  `localparam` lookup, usable for FPGA and ASIC alike.
- **Backend B (ASIC):** a physical ROM macro from the installed OpenRAM /
  OpenROM, targeting `~/.volare/sky130A`, behind a thin wrapper with the same
  logical interface. OpenRAM will not be vendored or modified, and only the
  views the installed version actually emits will be claimed.

## 8. Repository layout

```
model2rtl/
├── README.md
├── pyproject.toml
├── scripts/
│   ├── train_mnist_mlp.py          Stage 0: train, quantize, export, report
│   ├── gen_compute_fabric.py       Stage 1: emit the fixed compute fabric
│   ├── verify_stage1.py            Stage 1: run every check, write the report
│   ├── gen_weight_rom_portable.py  Stage 2: portable parameter backend
│   ├── gen_weight_rom_openram.py   Stage 2: OpenROM macros + wrapper + top
│   └── verify_stage2.py            Stage 2: run every check, write the report
├── src/model2rtl/
│   ├── contract.py                 fixed arithmetic contract + width analysis
│   ├── golden.py                   pure-NumPy integer golden model
│   ├── qat.py                      quantization-aware training (TensorFlow)
│   ├── data.py                     MNIST as raw uint8 activations
│   ├── storage.py                  NPZ / quant_params.json persistence
│   └── report.py                   Stage-0 report assembly
├── model/
│   ├── mnist_weights_indices.npz   trained 4-bit indices + integer biases
│   └── quant_params.json           fixed contract (weight independent)
├── reports/
│   ├── stage0_quantization.json      full Stage-0 report
│   ├── stage1_compute_fabric.json    full Stage-1 report
│   └── stage2_parameter_backends.json full Stage-2 report
├── tests/                          Stage-0 validation suite
├── rtl/                            all GENERATED
│   ├── mnist_mlp_fabric.v          weight-independent fabric (Stage 1)
│   ├── mnist_mlp_params_portable.v portable parameter backend (Stage 2)
│   ├── mnist_mlp_params_openram.v  OpenROM backend wrapper (Stage 2)
│   ├── mnist_mlp_params_sel_*.v    build-time backend selectors (Stage 2)
│   └── mnist_mlp_top.v             fabric + selected backend (Stage 2)
├── openram/                        (empty — Stage 2/5)
└── build/                          (empty — Stage 4+)
```

This project is **standalone**. It does not import from, depend on, reuse code
from, or modify `rtl2gdsagi`.

## 9. Reproducing Stage 0

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[train,test]"
.venv/bin/python scripts/train_mnist_mlp.py --sweep-hidden-shift
.venv/bin/python -m pytest tests -v
```

Seed 1234; MNIST split `train[:55000]` / `train[55000:60000]` / official 10,000-image
test set. Seeds, package versions, Python version, dataset fingerprint and
SHA-256 hashes of both artefacts are recorded in
`reports/stage0_quantization.json` under `meta`.

TensorFlow is a **training-time dependency only**. The compiler and the integer
golden model depend on NumPy alone.

## 10. Stage 0 results

See `reports/stage0_quantization.json` for the full report; the headline numbers
are summarised in the "Stage 0 results" section below, which is regenerated from
that report.

<!-- STAGE0_RESULTS_START -->
### Accuracy

| Model | Train | Test |
|-------|-------|------|
| float32 baseline (reference only) | 0.9793 | 0.9652 |
| **quantized integer golden model** | 0.9855 | **0.9645** |

Accuracy drop from float on the test set (float minus integer): **+0.0007** (+0.07 percentage points). Target was > 0.90 for the integer model.

The exported integer model was cross-checked against the TensorFlow QAT graph over all 10000 test images: max |logit difference| = 0.

### Weight index distribution

| Level (`alphabet[i]`) | -8 | -7 | -6 | -5 | -4 | -3 | -2 | -1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| layer1 (25088 synapses) | 228 | 204 | 312 | 569 | 1013 | 1696 | 2572 | 3702 | 4201 | 3876 | 2868 | 1795 | 997 | 523 | 279 | 253 |
| layer2 (320 synapses) | 23 | 11 | 8 | 21 | 18 | 24 | 16 | 29 | 22 | 32 | 28 | 28 | 26 | 16 | 10 | 8 |

- **layer1** [784, 32]: quantized weight range [-8, 7], unused levels: none, weight saturation during export: 230 (0.9168%), bias range [-327, 434] (needs 10 of the declared 22 signed bits).
- **layer2** [32, 10]: quantized weight range [-8, 7], unused levels: none, weight saturation during export: 24 (7.5000%), bias range [-106, 80] (needs 8 of the declared 17 signed bits).

### Observed integer ranges on the 10,000-image test set

| Signal | Declared | Observed |
|--------|----------|----------|
| input activation | [0, 255] | [0, 255] |
| layer 1 accumulator | [-3696512, 3496591] | [-71470, 52160] |
| hidden activation | [0, 255] | [0, 204] |
| logits | [-130816, 122655] | [-3216, 2417] |

Hidden saturation: **0 of 320000 hidden activations (0.0000%)** hit the uint8 clamp; the largest pre-saturation value observed was 204. 40.40% of hidden activations are exactly 0 (ReLU).

### Weight storage

25408 synapses (25088 + 320) x 4 bits = **101632 bits = 12704 bytes** of weight index storage. Biases add 32 + 10 integers stored as int32.

### Provenance

| Item | Value |
|------|-------|
| seed | 1234 |
| quantization method | quantisation-aware training with straight-through estimators |
| QAT epochs / float epochs | 60 / 30 |
| Python | 3.11.11 |
| NumPy | 1.26.4 |
| TensorFlow / Keras | 2.16.2 / 3.15.1 |
| dataset split | MNIST train[:55000] / train[55000:60000] / official test |
| `x_test` SHA-256 | `ba1ed81f08b0bc5f87541e3b60cc09cd` |
| `mnist_weights_indices.npz` SHA-256 | `1e231ad80e12e1045bb2941f12a84b1f` |
| `quant_params.json` SHA-256 | `2ad884b42e797bb4400ecaa2f9de46da` |
| model parameter SHA-256 | `6d54c2e75088bf85db83f83097c3a0dd` |

### Hidden requantization shift sweep (diagnostic)

| shift | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|
| val accuracy | 0.9568 | 0.9580 | 0.9562 | 0.9512 | 0.9462 | 0.9392 |

Shift **8** was frozen into the contract.
<!-- STAGE0_RESULTS_END -->

## 11. Stage 1 results — the fixed compute fabric

<!-- STAGE1_RESULTS_START -->
### Architecture: input-serial / output-parallel Multiply-Select-Add

```
                      x_i  (one activation at a time)
                       |
        +--------------+--------------+
        |              |              |
    x_i*a[0]       x_i*a[1]  ...  x_i*a[15]      <- K = 16 SHARED products
        +--------------+--------------+
                       |
      +----------------+----------------+
      |                |                |
  16:1 select      16:1 select      16:1 select   <- one per output neuron
      |                |                |
   acc[0]           acc[1]     ...   acc[N-1]
```

One product bank exists in the entire design. It is shared across every
output neuron of the active layer, reused across input cycles, and reused
by **both** layers. Yosys elaborates the fabric to exactly
**16 `$mul` cells** and **42 selector instances** (32 layer-1 + 10 layer-2).

### Three resource baselines — the same arithmetic, three organisations

| Organisation | Product generators | What it costs |
|---|---|---|
| 1. Naive fully spatial (one multiplier per synapse) | 25408 | 1 cycle, largest area |
| 2. MSA fully spatial (K per input line) | 13056 | 1 cycle, smaller than naive |
| 3. **Stage-1 input-serial MSA (implemented)** | **16** | 864 cycles per inference |

**This is not a free win.** Baseline 3 trades latency for area: one
inference takes 864 cycles instead of one. The Stage-0 operator analysis
counts a fully *unrolled* design and remains valid as an analytical
fully-spatial count; it is not superseded by this table. And because every
product has a constant 4-bit operand, none of these source-level counts is
a physical multiplier or DSP count. Stage 4 measures synthesized resources.

### Latency (architectural only — no clock frequency is claimed)

| Phase | Cycles |
|---|---|
| start accepted | 1 |
| layer-1 activation streaming | 784 |
| layer-1 pipeline drain | 1 |
| layer-1 finalisation (bias, ReLU, requantise, saturate) | 33 |
| layer-2 activation streaming | 32 |
| layer-2 pipeline drain | 1 |
| layer-2 finalisation (bias, argmax) | 11 |
| done / prediction_valid | 1 |
| **total, measured in simulation** | **864** |

Formula: `n_in + 2*n_hidden + n_out + 6`. The cycle count is data independent (verified: every image took the same 864 cycles).

| Clock | Latency | Inferences/s |
|---|---|---|
| 50 MHz | 17.28 us | 57870 |
| 100 MHz | 8.64 us | 115741 |

These are cycle counts divided by an assumed clock. **No maximum clock
frequency has been established** — that needs synthesis and timing
analysis, which is Stage 4.

### Interface

| Port group | Semantics |
|---|---|
| `clk`, `rst`, `start` | one clock; `rst` synchronous active high; `start` a one-cycle pulse while idle |
| `in_ready` / `in_valid` / `in_data[7:0]` | activation stream handshake, exactly 784 transfers in index order |
| `wmem_en` / `wmem_layer` / `wmem_addr[9:0]` / `wmem_data[127:0]` | weight-index memory, synchronous read, 1-cycle latency |
| `bmem_en` / `bmem_layer` / `bmem_addr[5:0]` / `bmem_data[21:0]` | bias memory, synchronous read, 1-cycle latency |
| `busy`, `done`, `prediction_valid`, `prediction[3:0]`, `logits[179:0]` | status and results |

**Memory read semantics (identical for both Stage-2 backends):** an address
driven during cycle *T* is captured on the posedge ending cycle *T*; the data
must be presented during cycle *T+1*.

**Weight-word packing:** `weight_index[i][j] = wmem_data[j*4 +: 4]`, where
`wmem_addr = i` is the input-feature index. This preserves the Stage-0
orientation `[in_features, out_features]`; neuron 0 occupies the least
significant nibble. Layer 1 uses bits [127:0], layer 2 uses bits [39:0].

**Bias interface:** option B, indexed read. Chosen over a wide packed port
because finalisation is already one neuron per cycle, so an indexed read
costs no extra cycles and keeps the Stage-2 ROM shape identical to the
weight interface. Biases are model parameters and are **not** compiled into
the fabric.

### Arithmetic — unchanged from the frozen Stage-0 contract

| Item | Value |
|---|---|
| product | signed 12-bit, range [-2040, 1785] |
| layer-1 accumulator | signed 23-bit (dot 22 + bias 22) |
| layer-2 accumulator | signed 18-bit (dot 17 + bias 17) |
| requantisation | `h = clamp((max(acc1, 0) + 128) >> 8, 0, 255)` |
| rounding | round-half-up (add 1 << (shift-1), then arithmetic right shift) |
| saturation | clamp to [0, 255] (unsigned 8-bit) |
| argmax ties | lowest index wins (strict > comparison), matching numpy.argmax |

Signedness is explicit everywhere: the unsigned activation is zero extended
and `$signed(...)` before the multiply, and each alphabet level is a signed
12-bit constant, so no implicit unsigned conversion is possible. The ReLU
result is carried in an unsigned 24-bit temporary purely so the
requantisation shift is unambiguously logical; the architectural accumulator
stays signed 23-bit.

### Verification performed

| Check | Result |
|---|---|
| Yosys `read_verilog` | PASS |
| Yosys `hierarchy -check -top mnist_mlp_fabric` | PASS |
| Yosys `proc` + `check -assert` | PASS (Found and reported 0 problems) |
| Yosys inferred latches | 0 |
| Yosys multiply-driven nets | False |
| Yosys undriven nets | False |
| Icarus compile, strict `-g2001 -Wall` | PASS |
| MNIST images simulated vs the integer golden model | 64 |
| logit mismatches | **0** |
| prediction mismatches | **0** |
| layer-1 dot products and hidden activations checked | True |
| second, unrelated weight set through the same fabric | 0 mismatches over 8 images |
| stalled input handshake | 0 mismatches, 975 cycles (vs 864 back-to-back) |

The oracle is the **Stage-0 NumPy integer golden model**, never Keras.

### Weight independence (mandatory Stage-1 proof)

The generator reads only topology, K and the frozen arithmetic contract.
Regenerating the fabric after substituting the trained parameters gives a
byte-identical file:

| Model parameters present | Fabric SHA-256 | Identical |
|---|---|---|
| trained weight indices | `7757362642b37fd0044bb7b323467116` | — |
| **different random weight set** | `7757362642b37fd0044bb7b323467116` | **YES** |
| **different biases** | `7757362642b37fd0044bb7b323467116` | **YES** |

Additionally: the generator is instrumented in tests to prove it never
opens an `.npz` or anything under `model/`, and every numeric literal in
the emitted Verilog is checked against the set of architecturally
explainable constants, so no trained value can hide in it.

### Reproducing Stage 1

```bash
.venv/bin/python scripts/gen_compute_fabric.py
.venv/bin/python scripts/verify_stage1.py
.venv/bin/python scripts/render_stage1_readme.py
.venv/bin/python -m pytest tests -q
```

Tool versions used: Icarus Verilog version 13.0 (stable) (v13_0); Yosys 0.68+.
<!-- STAGE1_RESULTS_END -->

## 12. Stage 2 results — parameter storage backends

<!-- STAGE2_RESULTS_START -->
Stage 2 supplies the trained parameters to the **unchanged** Stage-1
fabric through two interchangeable storage backends.

| | Portable backend | OpenRAM/OpenROM backend |
|---|---|---|
| RTL | `rtl/mnist_mlp_params_portable.v` | `rtl/mnist_mlp_params_openram.v` |
| Implementation | pure synthesizable Verilog-2001, `case`/constant lookup | wrapper over four OpenROM-shaped macros |
| Targets | **FPGA and ASIC** | **ASIC / SKY130 only** — no FPGA portability claimed |
| Physical macros | not applicable | see the macro table below |

`rtl/mnist_mlp_fabric.v` was **not modified**: its SHA-256 still matches
the Stage-1 report (`7757362642b37fd0044bb7b323467116`).

### Memory interface (transcribed from the frozen fabric, not invented)

| Signal | Backend direction | Width | Role |
|---|---|---|---|
| `clk` | input | 1 | single clock, shared with the fabric |
| `wmem_en` / `wmem_layer` / `wmem_addr` / `wmem_data` | in/in/in/out | 1/1/10/128 | weight-index memory |
| `bmem_en` / `bmem_layer` / `bmem_addr` / `bmem_data` | in/in/in/out | 1/1/6/22 | bias memory |

**Timing (identical for both backends):** Synchronous read, 1 cycle latency, enable gated with hold: an address and layer driven during cycle T are captured on the posedge that ends cycle T; the corresponding data must be presented throughout cycle T+1. When en is low the previously captured data must be held unchanged.

```verilog
always @(posedge clk) if (en) data_r <= MEM[{layer, addr}];
assign data = data_r;
```

`src/model2rtl/memif.py` re-parses the fabric's port list and fails
closed if this description ever drifts from the RTL.

### Canonical parameter images — one source of truth

Both backends are generated from these images and proved against the
same hashes, so it is impossible to physically build one dataset and
test another.

| Image | Depth | Width | Bits | SHA-256 |
|---|---|---|---|---|
| `weights_l1` | 784 | 128 | 100352 | `e7fd9a1668b71ff64616466a0ed0f77a` |
| `weights_l2` | 32 | 40 | 1280 | `b3866b5dcbd1e60e75300794786c9c75` |
| `bias_l1` | 32 | 22 | 704 | `ac8563c111b41dd72a09b55ee3136ab7` |
| `bias_l2` | 10 | 17 | 170 | `efb63bb9cc7b26d721b4fc53f19aaed4` |

Packing is the Stage-0 orientation `[in_features, out_features]`, not
transposed: `weight_index[i][j] = wmem_data[j*4 +: 4]`, neuron 0 in the
least significant nibble. Layer-2 weight words leave `wmem_data[127:40]`
at zero. Layer-2 biases are **sign extended** from 17 to 22 bits.
Invalid addresses return all zeros and never alias a valid row.

Full readback: **25408/25408 weight indices exact**, layer-1 bias exact: True,
layer-2 bias exact: True, rows 784/784 / 32/32 / 32/32 / 10/10.

### Backend equivalence

Both backends were instantiated side by side and driven with one
identical stimulus stream covering every valid address of all four
memories, plus enable-deasserted holds, layer switching on consecutive
cycles, first/last addresses, invalid addresses, and an address change
every cycle.

| Metric | Value |
|---|---|
| stimulus cycles | 969 |
| weight-bus comparisons | 969 |
| bias-bus comparisons | 969 |
| **portable vs OpenRAM mismatches** | **0** |
| **mismatches vs the canonical images** | **0** |

### Top level and backend selection

`rtl/mnist_mlp_top.v` instantiates the unchanged fabric plus the abstract
module `mnist_mlp_params`. **Backend selection is build time only** — no
runtime mux exists. Compile exactly one selector file:

```
portable : mnist_mlp_fabric.v mnist_mlp_params_portable.v mnist_mlp_params_sel_portable.v mnist_mlp_top.v
openram  : mnist_mlp_fabric.v mnist_mlp_params_openram.v mnist_mlp_params_sel_openram.v mnist_mlp_top.v
```

### Full-model inference (oracle: the Stage-0 integer golden model)

| Backend | Images | Logit mismatches | Hidden mismatches | Prediction mismatches | Accuracy | Cycles |
|---|---|---|---|---|---|---|
| portable | 200 | **0** | **0** | **0** | 0.9800 | [864] |
| OpenRAM behavioural | 200 | **0** | **0** | **0** | 0.9800 | [864] |

Backend-to-backend logit mismatches: **0**. Inference latency is
unchanged from Stage 1 at 864 cycles for both builds.

### Lint and elaboration

| Target | Yosys `check -assert` | Latches | Multi-driven | Undriven | Icarus `-g2001 -Wall` |
|---|---|---|---|---|---|
| portable backend | PASS (Found and reported 0 problems) | 0 | False | False | PASS |
| OpenRAM behavioural backend | PASS (Found and reported 0 problems) | 0 | False | False | PASS |
| top + portable | PASS (Found and reported 0 problems) | 0 | False | False | PASS |
| top + OpenRAM | PASS (Found and reported 0 problems) | 0 | False | False | PASS |

### OpenRAM / OpenROM environment (exact paths actually used)

| Item | Value |
|---|---|
| source | https://github.com/VLSIDA/OpenRAM.git |
| branch | `stable` |
| commit | `b2b069ce119d1488cbe6883b2240bceb5c7ce29a` |
| `OPENRAM_HOME` | `/home/rithwik/OpenRAM/compiler` |
| `OPENRAM_TECH` | `/home/rithwik/OpenRAM/technology` |
| `PDK_ROOT` | `/home/rithwik/pdk` |
| PDK variant | sky130A |
| PDK provenance | ciel enable --pdk sky130 e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066 (OpenRAM Makefile SKY130_CIEL), plus skywater-pdk f70d8ca and sky130_fd_bd_sram dd64256 |
| Python | Python 3.11.11 |
| DRC tool | magic 8.3.486 (conda-forge, user space) |
| LVS tool | netgen 1.5.323 (built from source, user space) |
| Nix bootstrap | disabled (use_nix = False); tools come from PATH |
| environment script | `build/openram/openram_env.sh` |

Nothing was installed system wide, no system Python was modified, and no
`sudo` was used. OpenRAM is upstream and unmodified.

**Smoke test** (official OpenRAM sample sky130 1 kbyte ROM): generation PASS in 235s, views `gds, lef, log, lvs.sp, py, sp, v`. 
DRC: **830 errors**. LVS: **MISMATCH**. The UPSTREAM REFERENCE macro itself fails DRC and LVS in this environment, so physical-verification results here are not evidence about model2rtl's data. Generation of all views works.

### Proven OpenROM data convention

OpenROM stores the input file as a big-endian bit stream, first bit first. Word A of the file lands at addr0 = A. Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e. dout0 is BIT REVERSED with respect to a Verilog [word_bits-1:0] literal. This was proven empirically against a generated SPICE netlist, not assumed.

Evidence: build/openram/diag: a 1024-word one-hot-per-byte diagnostic ROM was generated and all 8192 programmed cells in the resulting SPICE netlist matched the predicted placement exactly (0 mismatches).

### OpenROM physical macros

| Macro | Requested | Status | words/row | Physical array | Views generated | DRC | LVS | Runtime |
|---|---|---|---|---|---|---|---|---|
| `weights_l1` | — | not attempted | — | — | — | — | — | — |
| `weights_l2` | 32 x 40 | **PASS** | 4 | 8 rows x 160 cols | gds, lef, log, lvs.sp, py, sp, v | 780 errors | MISMATCH | 10.9s |
| `bias_l1` | 32 x 22 | **BLOCKED** | — | — | — | — | — | — |
| `bias_l2` | 10 x 17 | **BLOCKED** | — | — | — | — | — | — |

- **`bias_l1` is BLOCKED.** OpenROM's word_size is expressed in BYTES (rom_config.py sets word_bits = word_size * 8), so a 22-bit word cannot be requested. Generating this macro would require changing the word width, which Stage 2 forbids without explicit approval.
  Proposed fix, *not implemented without approval*: pad the word to 24 bits (3 bytes) in the physical macro and slice it back in the wrapper.
- **`bias_l2` is BLOCKED.** OpenROM's word_size is expressed in BYTES (rom_config.py sets word_bits = word_size * 8), so a 17-bit word cannot be requested. Generating this macro would require changing the word width, which Stage 2 forbids without explicit approval.
  Proposed fix, *not implemented without approval*: pad the word to 24 bits (3 bytes) in the physical macro and slice it back in the wrapper.

### What OpenROM actually generated

For the macros that built, this OpenROM version emits `.gds`, `.sp`,
`.lvs.sp`, `.lef`, `.v` and a reproduced config `.py`. **It does emit a
Verilog file**, contrary to its own documentation — but it is a byte-oriented, delay-based ($readmemb on a binary file, negedge data with #DELAY) non-synthesizable stub that does not implement this project's read contract, so it is not used.

`rtl/mnist_mlp_params_openram.v` therefore contains **our own**
behavioural read models, labelled in the file as a *model2rtl
behavioural model of the generated OpenROM contents* — **not** as
OpenROM-generated Verilog. Their contents are generated from the same
canonical images that the physical ROM data files carry, and the tests
check the ROM input data bit-for-bit against those images.

### Limitations

- The bias ROMs cannot be requested from this OpenROM version: its word_size is expressed in BYTES, so 22-bit and 17-bit words are not representable. Padding was NOT applied because that would change the physical word width without approval.
- DRC and LVS fail in this environment on the UPSTREAM REFERENCE macro as well (830 errors, LVS mismatch), so no macro here has a clean physical-verification result and none is claimed.
- No synthesis, FPGA or ASIC gate-level verification has been run; that is Stage 4.
- No area, timing or cell-area number is claimed.
- Stage 3's formal behavioural verification campaign is not implemented.
<!-- STAGE2_RESULTS_END -->

## 13. Roadmap (documented, NOT implemented)

| Stage | Content | Status |
|-------|---------|--------|
| 0 | Training, quantization, integer golden model, contract, reports, tests | **done** |
| 1 | `scripts/gen_compute_fabric.py` -> `rtl/mnist_mlp_fabric.v`, weight-independent Multiply-Select-Add fabric; elaborated and structurally checked with Yosys, compiled with Icarus, verified against the Stage-0 golden model | **done** |
| 2 | Parameter backends behind one fixed interface: portable Verilog (`gen_weight_rom_portable.py`) and OpenRAM/OpenROM (`gen_weight_rom_openram.py`); plus `rtl/mnist_mlp_top.v` | **done (OpenROM macros partial)** |
| 3 | Behavioral RTL verification of ~200 MNIST images against the Stage-0 integer golden model; plus proof that one fabric serves two different weight-index sets | not started |
| 4 | Dual-target portability: identical sources through an FPGA Yosys flow and a generic/ASIC Yosys flow, each followed by **gate-level simulation** (a clean exit code is not verification) | not started |
| 5 | OpenRAM/OpenROM ASIC backend verification and portable-ROM vs macro area comparison with a crossover estimate | not started |
| 6 | Final report | not started |

A full SKY130 GDS run through `rtl2gdsagi` is explicitly **out of scope** for
this project.

### Not claimed, because it has not happened

- No clean DRC or LVS result exists for any generated macro.
- The layer-1 and layer-2 bias ROMs have no physical macro at all.
- No synthesis has been run, so no portability claim is made.
- No FPGA synthesis or FPGA gate-level verification has been run.
- No ASIC synthesis or ASIC gate-level verification has been run.
- No OpenRAM/OpenROM integration exists; OpenRAM has not been invoked.
- No area, cell-area, DSP or timing number has been measured, and no maximum
  clock frequency is claimed. The Yosys cell counts quoted below are
  pre-synthesis elaborated generic cells, nothing more.
- Autonomous end-to-end compilation does not exist.
