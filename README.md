# model2rtl

**Turn a trained neural network into a chip design.**

You give it a trained Keras model. It gives you Verilog: real, synthesizable hardware that computes exactly the same answers.

```bash
model2rtl --model my_model.h5 --output ./rtlout
```

That is the whole idea. The rest of this page is how to actually do it, what works, and what does not.

> **New to hardware?** You do not need an FPGA, a chip, or any expensive tools. Everything here runs on a laptop with free, open-source software. Start at [Quick start](#quick-start).

## What this actually does

A neural network is multiplications and additions. A chip can do those directly, without a CPU, if you describe the circuit. That description is written in a language called **Verilog**, and writing it by hand for a whole network is slow and error-prone.

`model2rtl` writes it for you:

```
  my_model.h5            ->   model2rtl   ->   mlp_fabric.v
  (trained in Keras)                           mlp_params.v
                                               mlp_top.v
                                               (Verilog you can simulate
                                                or send to a chip flow)
```

The interesting part is *how* it builds the circuit. A network with 25,408 connections would need 25,408 multipliers if you built one per connection. This design uses **16**, by exploiting the fact that the weights were squeezed down to only 16 possible values. More on that in [How it works](#how-it-works).

## Install

You need Python 3.9 or newer.

```bash
git clone <this repo> && cd model2rtl
python3 -m venv .venv
source .venv/bin/activate

pip install -e .              # the compiler (needs only numpy)
pip install -e ".[train]"      # add this to read .h5 files (installs TensorFlow)
```

To *simulate* the Verilog you also need two free tools:

```bash
# Ubuntu / Debian
sudo apt install iverilog yosys

# macOS
brew install icarus-verilog yosys
```

| Tool | What it is | Needed for |
|---|---|---|
| Icarus Verilog (`iverilog`) | a Verilog simulator | running the generated hardware |
| Yosys | a synthesis tool | turning Verilog into logic gates |

Neither is needed just to *generate* the Verilog.

## Quick start

Copy-paste this. It trains a small network, compiles it to hardware, and checks the hardware elaborates. Takes about a minute.

**1. Train something to compile**

```python
# save as train_demo.py
import numpy as np, tensorflow as tf

(x, y), (xt, yt) = tf.keras.datasets.mnist.load_data()
x, xt = x.reshape(-1, 784) / 255.0, xt.reshape(-1, 784) / 255.0

model = tf.keras.Sequential([
    tf.keras.layers.Input((784,)),
    tf.keras.layers.Dense(32, activation='relu'),   # hidden layer
    tf.keras.layers.Dense(10, activation='softmax') # 10 digits
])
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])
model.fit(x, y, epochs=5, batch_size=128)
model.save('demo.h5')

# save some test images for the compiler to measure against
np.savez('calib.npz', x=(xt[:2000] * 255).astype('uint8'), y=yt[:2000])
```

```bash
python train_demo.py
```

**2. Compile it to hardware**

```bash
model2rtl --model demo.h5 --calibration calib.npz \
          --output ./rtlout --check
```

You will see something like:

```
loaded demo.h5: 784 -> 32 -> ReLU -> 10
calibration: 2000 samples with labels
quantized: shift 8, input scale 0.0039215686
  float 0.9310 -> integer 0.9120 on calibration (-1.90 points)

wrote ./rtlout
  mlp_fabric.v      ...
  mlp_params.v      ...
  mlp_params_sel.v  ...
  mlp_top.v         ...
  compile_report.json

fabric is weight independent: True
latency: 864 cycles per inference (architectural only)
icarus: OK
yosys:  OK
```

That's it. `./rtlout` now contains a working hardware design.

> **`-1.90 points` is normal.** Squeezing weights down to 16 values costs some accuracy. If that bothers you, see [Getting the accuracy back](#getting-the-accuracy-back).

## What you get

| File | What it is | Contains your weights? |
|---|---|---|
| `mlp_fabric.v` | the compute engine: multipliers, adders, control | **no** |
| `mlp_params.v` | your trained weights, as a read-only memory | yes |
| `mlp_params_sel.v` | a small file that connects the two | no |
| `mlp_top.v` | the top level, wires everything together | no |
| `compile_report.json` | every number, hash and setting used | — |
| `param_images/` | the weights in a plain, checkable format | yes |

Only **one** of those files depends on your model. Train a different network of the same shape and `mlp_fabric.v` comes out byte-for-byte identical — the compiler checks this on every single run and refuses to finish if it is ever untrue.

## Using the hardware

The design has a simple handshake. To classify one input:

```
  1. hold rst high for a few cycles, then drop it
  2. pulse start high for one cycle
  3. in_ready goes high -> feed one value per cycle
     (set in_valid high and put the value on in_data)
  4. wait for done to pulse high
  5. read prediction (the winning class) and logits (the raw scores)
```

| Port | Direction | Meaning |
|---|---|---|
| `clk` | in | clock |
| `rst` | in | reset, active high, synchronous |
| `start` | in | pulse for one cycle to begin |
| `in_ready` | out | the design is ready for an input value |
| `in_valid` | in | you are providing a valid input value |
| `in_data` | in | one input value, 0-255 |
| `busy` | out | an inference is in progress |
| `done` | out | pulses high for one cycle when finished |
| `prediction` | out | the winning class index |
| `logits` | out | all raw scores, packed together |

A minimal testbench:

```verilog
// save as tb.v, then:
//   iverilog -g2001 -o sim tb.v rtlout/*.v && ./sim
`timescale 1ns/1ps
module tb;
    reg clk = 0;  always #5 clk = ~clk;
    reg rst = 1, start = 0, in_valid = 0;
    reg [7:0] in_data = 0;
    wire in_ready, busy, done, prediction_valid;
    wire [3:0] prediction;
    wire [179:0] logits;
    integer i;

    mlp_top dut (.clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits));

    initial begin
        repeat (4) @(negedge clk);
        rst = 0;                       // 1. release reset
        @(negedge clk); start = 1;     // 2. kick it off
        @(negedge clk); start = 0;

        i = 0;                         // 3. feed 784 pixels
        while (i < 784) begin
            if (in_ready) begin
                in_valid = 1;
                in_data  = i[7:0];     // put your real pixel here
                i = i + 1;
            end else in_valid = 0;
            @(negedge clk);
        end
        in_valid = 0;

        while (!done) @(negedge clk);  // 4. wait
        $display("predicted class = %0d", prediction);  // 5. read
        $finish;
    end
endmodule
```

One classification takes **864 clock cycles** for this network shape (`inputs + 2 x hidden + outputs + 6`). It processes one input value per cycle rather than all at once, which keeps the circuit small.

## What models are supported

Exactly one shape, on purpose:

```
Input -> Dense(any size) -> ReLU -> Dense(any size) -> output
```

| Supported | Not supported |
|---|---|
| 2 `Dense` layers, any width | 3 or more `Dense` layers |
| `relu` on the hidden layer | any other hidden activation |
| `softmax`, `sigmoid` or none on the output | `tanh` etc. on the output |
| `.h5`, `.keras`, or `.npz` with `w1,b1,w2,b2` | SavedModel folders, ONNX, TFLite, PyTorch |
| `Flatten`, `Dropout`, `Input` (ignored) | convolution, pooling, batch-norm, RNN |

If your model is not supported the compiler **stops and tells you what it found**. It never quietly compiles part of your network. Real examples from testing:

```
$ model2rtl --model housing.keras --output ./out
model2rtl: cannot compile this model.
expected exactly 2 Dense layers, found 3. This compiler builds
input -> Dense -> ReLU -> Dense only.
Layers found: Dense(hidden_1), Dense(hidden_2), Dense(output)

$ model2rtl --model convnet_weights.npz --output ./out
model2rtl: cannot compile this model.
inconsistent shapes: w1 (3, 3, 1, 32), w2 (1600, 10)
```

That second one is a convolutional network. The refusal is the correct answer: compiling it anyway would produce hardware that computes something other than your model.

## Getting the accuracy back

Weights are stored as one of only 16 values. Your model was not trained expecting that, so it loses a little accuracy. Two options:

**Default (fast, no training needed):**

```bash
model2rtl --model demo.h5 --calibration calib.npz --output ./out
```

**Fine-tuning (slower, much better):**

```bash
model2rtl --model demo.h5 --calibration calib.npz \
          --quantize qat --epochs 25 --output ./out
```

This retrains the weights *while pretending they are already squeezed*, so they settle in places that survive it. Measured on a Fashion-MNIST model, held-out data:

| | Accuracy |
|---|---|
| original float model | 83.0% |
| default quantization | 82.7% |
| with `--quantize qat` | **86.0%** |

> **Always pass `--calibration`.** Without it the compiler cannot measure anything and has to guess a key setting. It will warn you loudly. The file is just an `.npz` with `x` (inputs) and ideally `y` (labels).

## Command reference

| Option | Meaning |
|---|---|
| `--model PATH` | trained model: `.h5`, `.keras`, or `.npz` |
| `--indices PATH` | an already-quantized model; skips quantization |
| `--output DIR` | where to write the Verilog (required) |
| `--calibration PATH` | `.npz` with `x` and ideally `y`; strongly recommended |
| `--quantize ptq\|qat` | `ptq` (default, fast) or `qat` (fine-tune, better) |
| `--epochs N` | fine-tuning epochs, default 20 |
| `--prefix NAME` | name your modules, default `mlp` |
| `--input-scale F` | if your model expects `x/255`, this is `0.00392157`. Auto-detected by default |
| `--shift N` | force an internal setting; normally chosen by measurement |
| `--check` | run Icarus and Yosys on the result |
| `--quiet` | less output |

## Does it actually work?

The reference MNIST model was checked at every level. Not "it compiled" — actually simulated and compared, number by number.

| Check | Result |
|---|---|
| Original float accuracy | 96.52% |
| After quantization | 96.45% |
| Hardware simulation vs the maths, 500 images | **0 differences** |
| Internal signals checked, cycle by cycle | 178,840 checks, 0 failures |
| After FPGA synthesis, 500 images | **0 differences** |
| After generic chip synthesis, 500 images | **0 differences** |
| Automated tests | 429 passing |

Synthesized size, measured with real tools:

| | iCE40 FPGA | Generic gates |
|---|---|---|
| logic cells | 6,429 LUTs | 45,707 cells |
| registers | 1,614 | 1,742 |
| memory blocks | 32 | 0 (built from gates) |
| **multipliers / DSPs** | **0** | **0** |

Zero multipliers. The tools discovered that multiplying by a fixed small number is just shifting and adding, and removed them all.

## How it works

Every weight is one of 16 fixed values (-8, -7, -6 ... 6, 7). So for any input value `x`, there are only 16 possible products it can ever be involved in — no matter how many neurons it feeds.

So compute those 16 products **once**, and let every neuron pick the one it needs:

```
                          one input value x
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
      x * -8      x * -7      .....       x * +6      x * +7
        |           |           |           |           |
        +----------- 16 products, computed once ---------+
                                |
              +-----------+------+------+-----------+
              |           |             |           |
           neuron 0    neuron 1  .....  neuron N
            picks       picks           picks       <- each uses its
            one         one             one            4-bit weight
              |           |               |
            add to      add to          add to
            total       total           total
```

This is called **Multiply-Select-Add**. Inputs are fed one per cycle and every neuron accumulates in parallel, so the same 16 products serve the whole network, both layers included.

The trade: it takes 864 cycles instead of doing everything at once. You are exchanging speed for a much smaller circuit.

## Troubleshooting

| Message | What to do |
|---|---|
| `expected exactly 2 Dense layers, found 3` | Your model is too deep. Only 2 dense layers are supported. |
| `unrecognised model format` | Save as `.h5` or `.keras`: `model.save('m.h5')` |
| `reading a Keras model needs TensorFlow` | `pip install -e ".[train]"` |
| `no ReLU was found between the two Dense layers` | Use `activation='relu'` on the hidden layer. |
| `NO LABELLED CALIBRATION DATA` | Pass `--calibration` with an `.npz` containing `x` and `y`. |
| `bias does not fit N signed bits` | Your biases are very large relative to the weights. Retrain with a smaller learning rate or normalise your inputs. |
| Accuracy dropped a lot | Use `--quantize qat --epochs 30`. |
| `icarus: not on PATH, skipped` | Install `iverilog` if you want the check to run. |

## What this is not

Being clear about this matters more than looking impressive.

- **Not a finished chip.** You get Verilog. Turning that into silicon needs a full manufacturing flow that is not included.
- **Not FPGA-ready-to-flash.** No place-and-route, no timing analysis, no bitstream. The design synthesizes; nobody has fitted it to a real device.
- **No speed claims.** Cycle counts are exact, clock speed is not measured. Any MHz figure here would be made up.
- **Two dense layers only.** No convolution, no transformers, no ONNX or TFLite import.
- **The SKY130 chip memories are experimental.** They generate and their contents are verified exactly, but the manufacturing checks (DRC/LVS) cannot be trusted in this environment: the vendor's own reference design fails them here too. Status: **UNVERIFIED**.

## Going deeper

| Document | What is in it |
|---|---|
| **[FINAL-REPORT.md](FINAL-REPORT.md)** | the full technical report: architecture, quantization, verification, area |
| [`reports/final_report.json`](reports/final_report.json) | every measurement, machine-readable |
| [`reports/results.csv`](reports/results.csv) | headline numbers with their source |
| Appendices below | stage-by-stage evidence, regenerated from the reports |

To rebuild the reference MNIST design and re-run everything:

```bash
python scripts/train_mnist_mlp.py --sweep-hidden-shift
python scripts/gen_compute_fabric.py
python scripts/verify_stage3.py --images 500
python -m pytest tests -q
```

This project does not import from, depend on, or modify `rtl2gdsagi`.

---

The appendices below are the detailed per-stage evidence behind the numbers above. They are generated from the stage reports, not written by hand. Start with [FINAL-REPORT.md](FINAL-REPORT.md) if you want the narrative rather than the raw evidence.
## Appendix A — Stage 0: quantization

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

## Appendix B — Stage 1: the compute fabric

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
a physical multiplier or DSP count. Section 14 reports the synthesized
resources Stage 4 actually measured.

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
frequency has been established.** Stage 4 ran synthesis but no timing
analysis and no place-and-route, so these remain architectural latency
examples only.

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

## Appendix C — Stage 2: parameter-storage backends

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

**Prerequisites and exact install steps used on this machine:**

```bash
# 1. OpenRAM itself (upstream, unmodified)
git clone https://github.com/VLSIDA/OpenRAM.git ~/OpenRAM
cd ~/OpenRAM && python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt      # pulls ciel

# 2. SKY130 PDK + SRAM cell library, into user space
export PDK_ROOT=/home/rithwik/pdk
export PATH=~/OpenRAM/.venv/bin:$PATH
make sky130-pdk PDK_ROOT=$PDK_ROOT       # ciel fetches sky130A
make sky130-install PDK_ROOT=$PDK_ROOT   # links cells into technology/sky130

# 3. physical verification tools (user space, no sudo)
conda create -p ~/klayout_cf/magic -c conda-forge magic
git clone https://github.com/RTimothyEdwards/netgen.git ~/netgen-lvs
cd ~/netgen-lvs && ./configure --prefix=~/netgen-install \
    --with-tcl=~/klayout_cf/magic/lib --with-tk=~/klayout_cf/magic/lib
make && make install

# 4. environment for every OpenROM run
source build/openram/openram_env.sh
```

Two things this OpenRAM version needs that its docs do not mention:
`use_nix = False` must be set in every config (otherwise it aborts
demanding a Nix toolchain bootstrap), and the conda-forge package named
`netgen` is the **mesh generator**, not the LVS tool — netgen-lvs must be
built from source.

**Smoke test** (official OpenRAM sample sky130 1 kbyte ROM): generation PASS in 235s, views `gds, lef, log, lvs.sp, py, sp, v`. 
DRC: **830 errors**. LVS: **MISMATCH**. The UPSTREAM REFERENCE macro itself fails DRC and LVS in this environment, so physical-verification results here are not evidence about model2rtl's data. Generation of all views works.

### Proven OpenROM data convention

OpenROM stores the input file as a big-endian bit stream, first bit first. Word A of the file lands at addr0 = A. Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e. dout0 is BIT REVERSED with respect to a Verilog [word_bits-1:0] literal. This was proven empirically against a generated SPICE netlist, not assumed.

Evidence: build/openram/diag: a 1024-word one-hot-per-byte diagnostic ROM was generated and all 8192 programmed cells in the resulting SPICE netlist matched the predicted placement exactly (0 mismatches).

### OpenROM physical macros

| Macro | Requested | Status | words/row | Physical array | Views generated | DRC | LVS | Runtime |
|---|---|---|---|---|---|---|---|---|
| `weights_l1` | 784 x 128 | **FAIL** | — | — | — | — | — | — |
| `weights_l2` | 32 x 40 | **PASS** | 4 | 8 rows x 160 cols | gds, lef, log, lvs.sp, py, sp, v | 780 errors | MISMATCH | 10.8s |
| `bias_l1` | 32 x 22 | **BLOCKED** | — | — | — | — | — | — |
| `bias_l2` | 10 x 17 | **BLOCKED** | — | — | — | — | — | — |

- **`weights_l1` FAILED to generate.** Last lines of the tool output:
  ```
    File "/usr/lib64/python3.11/bdb.py", line 115, in dispatch_line
      if self.quitting: raise BdbQuit
                        ^^^^^^^^^^^^^
  bdb.BdbQuit
  ```
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

Two of these limitations were written at Stage 2 and have since been
addressed. Stage 4 ran both synthesis flows and gate-level simulated
both netlists (section 14). Stage 5 generated every physical macro,
using approved byte padding for the bias ROMs and four parallel banks
for the 784 x 128 layer-1 memory, and verified all 102,640 bits against
the generated netlists (section 15). What still stands: DRC and LVS
remain untrustworthy here, so physical SIGNOFF is UNVERIFIED.
<!-- STAGE2_RESULTS_END -->

## Appendix D — Stage 3: behavioral verification

<!-- STAGE3_RESULTS_START -->
Stage 3 runs the frozen production RTL against the Stage-0 NumPy integer
golden model. **Keras float output is never used as an oracle.**

### Three metrics, kept separate

These are not the same thing, and Stage 3 only gates on the first:

| Metric | Value |
|---|---|
| **1. RTL vs integer golden model (the PASS criterion)** | **0 mismatches** out of 5000 logit, 16000 hidden and 500 prediction comparisons |
| 2. Quantized integer model MNIST accuracy | 96.45% over the full 10,000-image test set (Stage 0); 98.00% on this 500-image subset |
| 3. RTL MNIST accuracy | 98.00% on the same subset |

Metrics 2 and 3 are identical *because* metric 1 is zero. An image the
integer model gets wrong is still a perfect RTL implementation.

### Test set

| Item | Value |
|---|---|
| selection | first 500 images of the official MNIST test set, in order; no filtering of any kind |
| images | 500 |
| label histogram (0-9) | [42, 67, 55, 45, 55, 50, 43, 49, 40, 54] |
| indices SHA-256 | `0c3fc3e2e8b0514136a044efedc6d6aa` |
| images SHA-256 | `33b682baf07158d5557e1e88c0093c69` |
| labels SHA-256 | `d9c1ee129708614296525e1d5d088e7f` |

### Backend results

| | Portable | OpenRAM behavioural |
|---|---|---|
| images | 500 | 500 |
| hidden values compared | 16000 | 16000 |
| logits compared | 5000 | 5000 |
| prediction comparisons | 500 | 500 |
| **hidden mismatches** | **0** | **0** |
| **logit mismatches** | **0** | **0** |
| **prediction mismatches** | **0** | **0** |
| label accuracy | 0.9800 | 0.9800 |
| cycles per inference | [864] | [864] |

Backend-to-backend: 0 hidden, 0 logit, 0 prediction and 0 cycle-count
mismatches. The OpenRAM figure is a **behavioural representation of the
canonical OpenROM contents** — it is not physical OpenROM verification.

### Cycle-level internal checkpointing

For 20 images every cycle of the fabric was captured and replayed against
the golden model, so a mismatch would be localised to a specific
(image, cycle, signal) rather than only showing up at the top level.

| Checkpoint | Comparisons |
|---|---|
| accumulator state before each update | 48320 |
| bias ROM word vs address issued one cycle earlier | 840 |
| layer-1 finalisation cycles | 640 |
| layer-2 finalisation cycles | 200 |
| final signed logits | 200 |
| layer-1 multiply-select-add cycles | 15680 |
| layer-2 multiply-select-add cycles | 640 |
| shared product-bank entries and selected products | 95360 |
| biased accumulator and requantised hidden value | 640 |
| weight ROM word vs address issued one cycle earlier | 16320 |
| **total** | **178840** |
| **failures** | **0** |

Traced neurons: layer 1 [0, 1, 31], layer 2 [0, 9]. Signals: `state`, `mac_valid`, `layer_r`, `fin_valid`, `fin_idx`, `act_pipe`, `wmem_data`, `bmem_data`, `acc1`, `l1_sel_ext`, `l1_accb`, `hid_next`, `acc2`, `l2_sel_ext`, `logit_next`, `prod_00`, `prod_09`, `prod_15`.

### Memory pipeline (no off-by-one)

The fabric pipelines its parameter reads, so every cycle in which it
consumes `wmem_data` or `bmem_data` was checked against the address it
issued exactly one cycle earlier: **16320 weight-word and 840 bias-word
alignment checks, 0 failures.** Cases covered:

- consecutive layer-1 addresses (784 per image)
- layer-1 to layer-2 transition
- consecutive layer-2 addresses
- consecutive bias addresses, both layers
- enable held low during input stalls
- layer switch on the weight and bias ports
- first address after every state transition

### Input handshake under different legal timings

| Pattern | Images | Cycles | Mismatches |
|---|---|---|---|
| no stalls | 50 | 864–864 | 0 |
| periodic (every Nth input) | 50 | 975–975 | 0 |
| deterministic pseudo-random (LFSR) | 50 | 1223–1297 | 0 |

Results are bit-identical regardless of input timing; only latency
changes. No activation was lost or duplicated.

### Synchronous reset

| Reset point | Cycles after start | Stale-state failures | Fresh inference exact |
|---|---|---|---|
| early layer 1 | 20 | 0 | logits True, hidden True |
| idle, before start | n/a (idle) | 0 | logits True, hidden True |
| late layer 1 | 700 | 0 | logits True, hidden True |
| layer 2 | 830 | 0 | logits True, hidden True |
| layer-1 finalisation | 795 | 0 | logits True, hidden True |
| layer-2 finalisation | 855 | 0 | logits True, hidden True |

After every reset, `busy`, `done`, `prediction_valid` and `in_ready` are
low and all accumulators, hidden registers and logit registers read zero.

### Back-to-back transactions

500 inferences ran consecutively in one simulator process with no reset
between them: 0 mismatches. `done` is a single-cycle pulse every time,
and `prediction_valid` holds until the next `start`.

### Argmax

15 cases, 0 failures. Tie rule: **lowest index wins, matching numpy.argmax**.
Covered: a unique maximum at every class 0-9, a two-way tie, a
three-way tie, a ten-way tie, all-negative logits, and logits at the
representable extrema.

### Arithmetic edge cases at the top level

3 activation cases and 5 special cases, 0 failures.
Covered: x = 0, 1 and 255 against every alphabet level (including -8,
-1, 0, +1, +7); a strongly negative layer-1 accumulator forced through
ReLU to hidden = 0; hidden saturating to 255; the round-half-up
boundaries; and all-negative and all-positive logits. No wraparound.

### A second parameter set on the unchanged fabric

| Item | Value |
|---|---|
| fabric SHA-256 before | `7757362642b37fd0044bb7b323467116` |
| fabric SHA-256 after | `7757362642b37fd0044bb7b323467116` |
| **identical** | **True** |
| vectors tested | 8 |
| mismatches vs the MSA integer reference | **0** |
| alternate `weights_l1` image SHA-256 | `583468a3f00c2beafd64c8dd617683c5` |

Only the parameter backend was regenerated. the real trained model was NOT retrained or modified; only a second parameter backend was generated

### Lint and elaboration of both production variants

| Build | Yosys `check -assert` | Latches | Multi-driven | Undriven | Icarus `-g2001 -Wall` |
|---|---|---|---|---|---|
| top + openram_behavioral | PASS (Found and reported 0 problems) | 0 | False | False | PASS |
| top + portable | PASS (Found and reported 0 problems) | 0 | False | False | PASS |

### No model-specific shortcuts

`mnist_mlp_fabric.v` and `mnist_mlp_top.v` were scanned for MNIST labels,
embedded test images, expected logits and hard-coded predictions: **clean**.
The only model-dependent production RTL is the parameter backend.

### OpenROM physical status as of Stage 3: PARTIAL

*Superseded by Stage 5, which generated all seven macros. Kept here as
the Stage-3 record.*

- `weights_l2`: physically generated (gds, sp, lvs.sp, lef, v, py, log)
- `weights_l1`: not generated: OpenROM fails at the directly requested organisation
- bias macros: word widths of 22 and 17 bits are not representable by this OpenROM version (word_size is in bytes)
- DRC/LVS: no trustworthy signoff in this environment: the upstream reference macro also fails DRC and LVS here
- Banking: not attempted in Stage 3, as instructed

### Not claimed

- FPGA portability verified
- FPGA gate-level equivalence
- ASIC gate-level equivalence
- physical OpenROM signoff

These four statements were written at Stage 3. Stage 4 has since
verified FPGA-oriented and generic/ASIC-oriented synthesis portability
and gate-level simulated both netlists against the Stage-0 integer
golden model — see section 14. Formal gate-level *equivalence
checking* and physical OpenROM signoff are still not claimed, and
neither is place-and-route or timing closure on either target.
<!-- STAGE3_RESULTS_END -->

## Appendix E — Stage 4: dual-target synthesis portability

<!-- STAGE4_RESULTS_START -->
The same portable Verilog source was synthesized through an
FPGA-oriented Yosys flow and a generic/ASIC-oriented Yosys flow, and
both synthesized netlists were gate-level simulated against the Stage-0
integer golden model.

Stage 4 uses the **portable backend only**. The OpenRAM behavioural
backend and the physical OpenROM macros are deliberately out of scope
here — the point is that one vendor-neutral source targets both flows.

### Same source, two targets

| File | SHA-256 | Read by FPGA flow | Read by generic flow |
|---|---|---|---|
| `rtl/mnist_mlp_fabric.v` | `7757362642b37fd0044bb7b323467116` | yes | yes |
| `rtl/mnist_mlp_params_portable.v` | `d9c1aecd5f15872e1fb8011824d95776` | yes | yes |
| `rtl/mnist_mlp_params_sel_portable.v` | `902994346f1ad992427c1d83dbb00395` | yes | yes |
| `rtl/mnist_mlp_top.v` | `0763242015ce86e8b6edc3681d1e9834` | yes | yes |

| Invariant | Result |
|---|---|
| identical source hashes on both targets | **True** |
| every file read straight out of `rtl/` | **True** |
| source patched or copy-edited before synthesis | **False** |
| production RTL byte-identical before and after Stage 4 | **True** |

### Target A — FPGA-oriented (`ice40`)

synth_ice40 is present in the installed Yosys and the matching official simulation library <datdir>/ice40/cells_sim.v exists and is complete, so the synthesized netlist can be simulated with the vendor-equivalent cell models rather than hand-written stand-ins.  ECP5 was therefore not needed.

```
read_verilog -defer /home/rithwik/model2rtl/rtl/mnist_mlp_fabric.v
read_verilog -defer /home/rithwik/model2rtl/rtl/mnist_mlp_params_portable.v
read_verilog -defer /home/rithwik/model2rtl/rtl/mnist_mlp_params_sel_portable.v
read_verilog -defer /home/rithwik/model2rtl/rtl/mnist_mlp_top.v
synth_ice40 -top mnist_mlp_top
check -assert
stat
write_json /home/rithwik/model2rtl/build/stage4/fpga/fpga_netlist.json
write_verilog -noattr -noexpr /home/rithwik/model2rtl/build/stage4/fpga/fpga_netlist.v
```

| Item | Value |
|---|---|
| status | **PASS** |
| Yosys `check` problems | 0 |
| unresolved blackboxes | none |
| inferred latches | 0 |
| netlist | `build/stage4/fpga/fpga_netlist.v` |
| netlist SHA-256 | `bf0c87a67504a532e27c529997727e2b` |
| synthesis time | 25.3 s |

| iCE40 resource | Count |
|---|---|
| `SB_LUT4` | 6429 |
| `SB_CARRY` | 1004 |
| flip-flops (`SB_DFF*`) | 1614 |
| `SB_RAM40_4K` | 32 |
| `SB_MAC16` (DSP) | 0 |
| **total cells** | **9079** |

### Target B — generic / ASIC-oriented

Standard Yosys logic synthesis down to the Yosys generic gate
vocabulary. This is **not** a SKY130 flow and **not** ASIC signoff; it
exists to prove the source is not FPGA-shaped.

```
read_verilog /home/rithwik/model2rtl/rtl/mnist_mlp_fabric.v
read_verilog /home/rithwik/model2rtl/rtl/mnist_mlp_params_portable.v
read_verilog /home/rithwik/model2rtl/rtl/mnist_mlp_params_sel_portable.v
read_verilog /home/rithwik/model2rtl/rtl/mnist_mlp_top.v
hierarchy -check -top mnist_mlp_top
proc
flatten
opt -full
memory
opt -full
techmap
opt -full
simplemap
dfflegalize -cell $_DFF_P_ 01
abc -g simple
setundef -zero
opt_clean -purge
check -assert
stat
write_json /home/rithwik/model2rtl/build/stage4/generic/generic_netlist.json
write_verilog -noattr -noexpr /home/rithwik/model2rtl/build/stage4/generic/generic_netlist.v
```

| Item | Value |
|---|---|
| status | **PASS** |
| Yosys `check` problems | 0 |
| unresolved blackboxes | none |
| inferred latches | 0 |
| netlist | `build/stage4/generic/generic_netlist.v` |
| netlist SHA-256 | `725723fa6b9e9bf122b420e60e779356` |
| synthesis time | 11.8 s |

| Generic cell | Count |
|---|---|
| `$_AND_` | 20159 |
| `$_DFF_P_` | 1742 |
| `$_MUX_` | 1351 |
| `$_NOT_` | 2439 |
| `$_OR_` | 18603 |
| `$_XOR_` | 1413 |
| **total cells** | **45707** |

Physical area is **not available at this stage**: no characterized
standard-cell library was used, so these counts cannot be converted to
area, and no timing analysis was performed.

### Gate-level simulation — the part that proves it

Both netlists were simulated with the official Yosys cell models. The
testbench observes **top-level ports only**, because synthesis
legitimately destroys internal names; the production RTL was never
compiled into these simulations.

| Item | Value |
|---|---|
| images | 500 |
| selection | first 500 images of the official MNIST test set, in order; no filtering of any kind |
| reused from Stage 3 | True |
| images SHA-256 | `33b682baf07158d5557e1e88c0093c69` |
| oracle | Stage-0 NumPy integer golden model |
| integer golden accuracy on this set | 98.00% |

| Measurement | FPGA netlist | Generic netlist |
|---|---|---|
| logits compared | 5000 | 5000 |
| prediction comparisons | 500 | 500 |
| **logit mismatches** | **0** | **0** |
| **prediction mismatches** | **0** | **0** |
| label accuracy | 98.00% | 98.00% |
| cycles per inference (no stalls) | [864] | [864] |
| back-to-back inferences, mismatches | 12, 0 | 12, 0 |
| stalled traffic cycles, mismatches | [975], 0 | [975], 0 |
| reset points, stale-state failures | 2, 0 | 2, 0 |
| simulation runtime | 2287 s | 1604 s |

The architectural latency contract of **864 cycles** per inference
survived both flows unchanged: synthesis added no pipeline stage.

The two netlists also agree with **each other** bit for bit: 0 logit,
0 prediction and 0 cycle-count differences.

| Guard | FPGA | Generic |
|---|---|---|
| top module comes from | `build/stage4/fpga/fpga_netlist.v` | `build/stage4/generic/generic_netlist.v` |
| production RTL in the source list | False | False |
| cell library | `cells_sim.v` | `simcells.v` |

### What synthesis did to the 16 constant multiplications

The fabric writes 16 multiplications, but one operand is always a fixed
alphabet level, so nothing forces them to become multipliers. Measured,
not assumed:

| Observation | FPGA | Generic |
|---|---|---|
| `*` operators in the source | 16 | 16 |
| multiplier / DSP cells surviving | **0** | **0** |
| product-bank bits that are literal constants | 37 / 192 | 33 / 192 |
| product-bank bits that are plain wires from the activation register | 41 | 41 |
| product-bank bits fused into downstream select logic | 114 | 118 |

**No multiplier cell exists in either netlist.** Where the FPGA flow
kept the product wire names, the drivers show exactly what happened:

| Product | Level | Driver in the FPGA netlist |
|---|---|---|
| `prod_00` | x * -8 | `{ bank[11:3], 3'h0 }` |
| `prod_01` | x * -7 | `{ bank[23:15], x[2], bank[26], bank[3] }` |
| `prod_02` | x * -6 | `{ bank[35:26], bank[3], 1'h0 }` |
| `prod_03` | x * -5 | `{ bank[47:37], bank[3] }` |
| `prod_04` | x * -4 | `{ bank[58], bank[58:51], bank[3], 2'h0 }` |
| `prod_05` | x * -3 | `{ bank[70], bank[70:63], bank[27:26], bank[3] }` |
| `prod_06` | x * -2 | `{ bank[81], bank[81], bank[81:74], bank[3], 1'h0 }` |
| `prod_07` | x * -1 | `{ bank[92], bank[92], bank[92], bank[92:85], bank[3] }` |
| `prod_08` | x * +0 | `12'h000` |
| `prod_09` | x * +1 | `{ 4'h0, x[7:2], bank[26], bank[3] }` |
| `prod_10` | x * +2 | `{ 3'h0, x[7:2], bank[26], bank[3], 1'h0 }` |
| `prod_11` | x * +3 | `{ 2'h0, bank[141:133], bank[3] }` |
| `prod_12` | x * +4 | `{ 2'h0, x[7:2], bank[26], bank[3], 2'h0 }` |
| `prod_13` | x * +5 | `{ 1'h0, bank[166:159], bank[27:26], bank[3] }` |
| `prod_14` | x * +6 | `{ 1'h0, bank[141:133], bank[3], 1'h0 }` |
| `prod_15` | x * +7 | `{ 1'h0, bank[190:182], bank[37], bank[3] }` |

`x * 0` folded to a literal zero; `x * 1`, `x * 2` and `x * 4` are pure
wiring (a shift with constant zero fill); `x * -8` is a shift of a
shared negated value. The remaining levels reuse shared adder logic,
and their bank bits no longer exist as separate signals at all — the
product generation was fused into the 16:1 selection.

### Resources: source-level counts vs synthesized cells

| Quantity | Value | Kind |
|---|---|---|
| naive fully spatial synapse multiplications | 25408 | source-level operation count |
| fully spatial MSA product generators | 13056 | source-level operation count |
| Stage-1 time-multiplexed MSA product expressions | 16 | source-level operation count |
| iCE40 total cells (whole design) | 9079 | **measured, synthesized** |
| generic total cells (whole design) | 45707 | **measured, synthesized** |

The first three numbers and the last two are **different kinds of
quantity**. No ratio between them is an area ratio, and no area
conclusion is drawn here: that would require synthesizing comparable
implementations of each baseline, which Stage 4 does not do.

As a diagnostic only, `rtl/mnist_mlp_fabric.v` was also synthesized on
its own, with no parameter backend attached, to separate the compute
datapath from the parameter ROM:

| | Whole design | Fabric only | Difference (the ROM) |
|---|---|---|---|
| iCE40 `SB_LUT4` | 6429 | 6126 | +303 |
| iCE40 flip-flops | 1614 | 1418 | +196 |
| iCE40 `SB_RAM40_4K` | 32 | 0 | +32 |
| generic total cells | 45707 | 25505 | +20202 |

On iCE40 the 102,506 parameter bits landed in 32 block RAMs, so the ROM
costs almost no logic. With no block RAM available the generic flow had
to build the same ROM out of gates, which is where its 20202 extra cells go.

### Reproducibility

| Item | Value |
|---|---|
| Python | 3.11.11 |
| Yosys | Yosys 0.68+ |
| Icarus Verilog | Icarus Verilog version 13.0 (stable) (v13_0) |
| Yosys data directory | `/home/rithwik/klayout_cf/yosys/share/yosys` |
| fpga cell library | `/home/rithwik/klayout_cf/yosys/share/yosys/ice40/cells_sim.v` (`b5b2bcd86c0d6eea`) |
| generic cell library | `/home/rithwik/klayout_cf/yosys/share/yosys/simcells.v` (`63918d5fd356ffcd`) |
| fpga synthesis repeated from a clean directory | netlist SHA identical: **True** |
| generic synthesis repeated from a clean directory | netlist SHA identical: **True** |

Both flows are byte-deterministic: a second run from an empty output
directory produced an identical netlist.

### Not claimed by Stage 4

- No FPGA place-and-route was run: synth_ice40 output was not passed to nextpnr and no bitstream exists.
- No FPGA timing analysis and no Fmax was measured. The Stage-1 50/100 MHz figures remain architectural latency examples only.
- No ASIC physical implementation: the generic flow maps to the Yosys generic gate vocabulary, not to a SKY130 standard-cell library, and no floorplan, placement, routing or extraction was performed.
- No ASIC timing analysis and no characterized-library area.
- Stage-2 physical OpenROM backend remains PARTIAL and was not touched in Stage 4; the OpenRAM behavioural backend was deliberately excluded from Stage 4, which uses the portable backend only.
- No formal RTL-vs-netlist equivalence check was run. It is optional
  supplemental evidence; gate-level simulation against the integer
  oracle is the mandatory check and is what was done.
<!-- STAGE4_RESULTS_END -->

## Appendix F — Stage 5: physical OpenROM backend

<!-- STAGE5_RESULTS_START -->
Stage 5 completes the physical OpenROM parameter backend: every macro
now exists on disk as GDS, and every bit in it is proved to be the bit
the Stage-0 integer model uses.

**Physical generation: PASS. Physical signoff: UNVERIFIED.** Those are
two different claims and this section keeps them apart — see the DRC/LVS
subsection for why the second one cannot be made here.

### Two representations, one source of truth

The canonical Stage-2 *logical* images stay authoritative and were not
redefined. Stage 5 adds a *physical* representation derived from them by
two transformations, both approved and both exactly reversible:

| Logical memory | Logical shape | Physical form | Transformation |
|---|---|---|---|
| `weights_l1` | 784 x 128 | 4 macros of 784 x 32 | banked into 4 parallel macros of 784 x 32; all banks share one address and are read together, so the external latency stays one cycle |
| `weights_l2` | 32 x 40 | 32 x 40 | identity: already byte granular |
| `bias_l1` | 32 x 22 signed | 32 x 24 signed | sign extended 22 -> 24 bits |
| `bias_l2` | 10 x 17 signed | 10 x 24 signed | sign extended 17 -> 24 bits, then recovered and sign extended 17 -> 22 on the bus |

Why each one is needed: this OpenROM revision expresses `word_size` in
**bytes**, so 22-bit and 17-bit words cannot be requested at all, and it
cannot route the direct 784 x 128 array — `signal_escape_router` fails on
`clk0`. Neither the logical memories, the bit packing, nor the Stage-1
fabric interface changed.

| Physical macro | Shape | Logical slice | Image SHA-256 |
|---|---|---|---|
| `weights_l1_b0` | 784 x 32 | `weights_l1` `[31:0]` | `53ac6dd7e7011873f8648240` |
| `weights_l1_b1` | 784 x 32 | `weights_l1` `[63:32]` | `9fcbdaed9ac116404d64602c` |
| `weights_l1_b2` | 784 x 32 | `weights_l1` `[95:64]` | `b676a3b5f89cb4f054730f05` |
| `weights_l1_b3` | 784 x 32 | `weights_l1` `[127:96]` | `8c38b42b18a653797f39ea84` |
| `weights_l2` | 32 x 40 | `weights_l2` `[39:0]` | `0f475f7ea7b7dff0fd6f14cf` |
| `bias_l1` | 32 x 24 | `bias_l1` `[21:0]` | `bd8e7f6a00b5e5530cf80dd0` |
| `bias_l2` | 10 x 24 | `bias_l2` `[16:0]` | `86d4111b7cb6b5d8291d0f99` |

The reverse map is an automated invariant: `decode(physical) ==
canonical logical image` for **858 / 858 rows**, 0 mismatches.

### The macros

| Macro | Shape | words/row | Array | Runtime | Views | Bits verified | GDS bbox |
|---|---|---|---|---|---|---|---|
| `weights_l1_b0` | 784 x 32 | 4 | 196 x 128 | 205.9 s | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 194.17 x 276.40 um = **53668.6 um²** |
| `weights_l1_b1` | 784 x 32 | 4 | 196 x 128 | 204.2 s | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 194.17 x 276.40 um = **53668.6 um²** |
| `weights_l1_b2` | 784 x 32 | 4 | 196 x 128 | 199.6 s | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 194.17 x 276.40 um = **53668.6 um²** |
| `weights_l1_b3` | 784 x 32 | 4 | 196 x 128 | 201.2 s | gds, lef, log, lvs.sp, py, sp, v | **25088 / 25088** | 194.17 x 276.40 um = **53668.6 um²** |
| `weights_l2` | 32 x 40 | 4 | 8 x 160 | 10.3 s | gds, lef, log, lvs.sp, py, sp, v | **1280 / 1280** | 218.93 x 75.36 um = **16498.6 um²** |
| `bias_l1` | 32 x 24 | 4 | 8 x 96 | 6.9 s | gds, lef, log, lvs.sp, py, sp, v | **768 / 768** | 148.91 x 68.96 um = **10268.8 um²** |
| `bias_l2` | 10 x 24 | 5 | 2 x 120 | 6.4 s | gds, lef, log, lvs.sp, py, sp, v | **240 / 240** | 171.31 x 63.86 um = **10939.9 um²** |
| **total** | | | | | | **102640 / 102640** | **252381.6 um²** |

`words_per_row` is an internal folding choice and was picked from
measured behaviour, not reused: every attempt is recorded, including
the failures. For the 784 x 32 banks `words_per_row = 2` fails in
`signal_escape_router`; 4 and 8 both generate and 4 measured smaller
(53,669 um² against 56,817 um²). `bias_l2` needed 5 because 2 failed.

Bounding boxes are measured **from the GDS** with KLayout, hierarchy
resolved — not taken from a log line. The LEF abstract outline is
recorded alongside as a cross-check and is smaller, because the GDS also
contains the supply ring and labels.

### The central proof: the GDS holds the model's bits

For every macro, the programmed cells were read back out of the
**generated SPICE netlist** and compared against the physical image.
The cell map was derived empirically from the Stage-2 macro, whose
contents are known, and confirmed on all 1,280 of its bits:

```
row = addr // words_per_row
col = bit * words_per_row + addr %% words_per_row   (bit numbered MSB first)
rom_base_one_cell = 1, rom_base_zero_cell = 0
```

| Check | Count | Mismatches |
|---|---|---|
| programmed bit cells vs the physical image | 102640 | **0** |
| logical rows rebuilt from the physical macros | 858 | **0** |
| weight indices after unpacking | 25408 | **0** |
| bias values through the full path | 42 | **0** |
| bias special values (0, +1, -1, both extremes, min/max present) | 14 | **0** |

All 784 layer-1 rows reassemble from the four banks, and all
**25,408 / 25,408** weight indices survive banking unchanged.

### Functional equivalence: the physical form changes nothing

| Comparison | Result |
|---|---|
| portable vs canonical image | 0 weight + 0 bias mismatches |
| OpenRAM behavioural vs canonical image | 0 + 0 |
| **physical wrapper vs canonical image** | **0 + 0** |
| backend to backend, all three pairs | 0 |

969 stimulus cycles, 2907 weight and 2907 bias comparisons, covering every valid address of every logical memory, plus holds, layer switches, invalid addresses, first/last address and a new address every cycle.

Full model, the same 500 MNIST images Stages 3 and 4 used:

| | Physical backend | Portable backend |
|---|---|---|
| hidden mismatches | **0** / 16000 | **0** / 16000 |
| logit mismatches | **0** / 5000 | **0** / 5000 |
| prediction mismatches | **0** | **0** |
| cycles per inference | [864] | [864] |
| label accuracy | 98.00% | 98.00% |

Backend to backend: 0 hidden, 0 logit, 0 prediction mismatches. The
four banks share one address and are read in parallel, so the external
read latency is still one cycle and the inference is still 864 cycles.

### Area

| Storage | Measurement | Area |
|---|---|---|
| OpenROM hard macros (7 total) | GDS bounding boxes, summed | **252381.6 um²** |
| of which the four `weights_l1` banks | | 214674.4 um² |
| `mnist_mlp_params_portable.v` on SKY130 | liberty cell area | **58335.9 um²** |
| | of which sequential | 4144.0 um² (138 cells) |
| | of which combinational | 54192.0 um² (9268 cells) |

Library: `sky130_fd_sc_hd__tt_025C_1v80.lib`, corner sky130_fd_sc_hd, tt, 25 C, 1.80 V. 9406 mapped cells, no blackboxes.

**These are not the same kind of area.** The macro figure is a hard
block's bounding box, already containing its decoders, column mux,
precharge and supply ring. The portable figure is a standard-cell area
sum with no placement utilisation and no routing overhead, because no
place-and-route was run. The raw macro sum is also not a floorplanned
area: there is no floorplan, and no placement density is claimed.

### Storage crossover — none was measured

| Point | Bits | OpenROM bbox | Portable cells | Portable cell area | Ratio | Smaller |
|---|---|---|---|---|---|---|
| 32x32 | 1024 | 13275.3 um² | 203 | 1964.4 um² | 6.76 | portable |
| 64x32 | 2048 | 15037.0 um² | 375 | 2916.5 um² | 5.16 | portable |
| 128x32 | 4096 | 18466.5 um² | 679 | 4773.3 um² | 3.87 | portable |
| 256x32 | 8192 | 25266.8 um² | 1194 | 8165.3 um² | 3.09 | portable |
| 512x32 | 16384 | 38879.4 um² | 2150 | 13753.2 um² | 2.83 | portable |
| 784x32 | 25088 | 53668.6 um² | 3032 | 18433.9 um² | 2.91 | portable |
| 1568x32 | 50176 | 92011.5 um² | 5213 | 30934.7 um² | 2.97 | portable |

Both implementations at each point hold **identical deterministic
contents**, and the OpenROM side of every sweep point had its bits
verified against the generated netlist the same way the real macros did.

No crossover was measured. The OpenROM bounding box exceeds the portable mapped cell area at all 7 points, and the ratio is 6.76 at the smallest point and 2.97 at the largest, so it flattens rather than converging towards 1. Any statement about sizes beyond 50176 bits would be extrapolation and is not made.

For scale rather than as a claim: a placed portable block occupies
cell area divided by its utilisation, so at the deepest measured
point the two would only break even if the portable block placed at
**34% utilisation or worse**. That is a derived sensitivity, not
a measurement.

### DRC / LVS: signoff is UNVERIFIED

The local physical-verification environment is not trustworthy for this
OpenROM revision, and Stage 5 did not try to repair it. A control was
run under identical settings: OpenRAM's own upstream reference ROM (rom_configs/example_1kbyte.bin, word_size 1, the settings sky130_rom_1kbyte.py uses). Nothing in the OpenRAM tree was modified; only the output directory was redirected.

| Macro | DRC | LVS |
|---|---|---|
| **control — OpenRAM's own reference ROM** | **830 errors** | **MISMATCH** |
| `weights_l1_b0` | 1244 errors | MISMATCH |
| `weights_l1_b1` | 1244 errors | MISMATCH |
| `weights_l1_b2` | 1244 errors | MISMATCH |
| `weights_l1_b3` | 1244 errors | MISMATCH |
| `weights_l2` | 780 errors | MISMATCH |
| `bias_l1` | 500 errors | MISMATCH |
| `bias_l2` | 615 errors | MISMATCH |

The upstream reference macro fails here too, so **no DRC or LVS result
produced in this environment is evidence about model2rtl's macros** —
in either direction. Therefore:

| Verdict | Status |
|---|---|
| physical generation | **PASS** |
| physical signoff | **UNVERIFIED** |

### Toolchain (unchanged from Stage 2)

| Item | Value |
|---|---|
| OpenRAM | `b2b069ce119d1488cbe6883b2240bceb5c7ce29a` branch `stable` |
| OpenRAM tracked files modified | False |
| PDK | `/home/rithwik/pdk`, sky130A present: True |
| magic | 8.3.486 |
| netgen | Netgen 1.5.323 compiled on Tue Aug 18 15:41:47 IST 2026 |
| KLayout (area measurement) | KLayout 0.28.17 |

### Not claimed by Stage 5

- No macro is DRC-clean or LVS-clean: the environment's control fails, so no physical-verification result here is evidence.
- No full-chip GDS, no floorplan, no placement, no routing.
- No timing analysis and no maximum clock frequency.
- The area comparison is between two different kinds of area and is not a finished-chip ratio.
- No crossover point is claimed beyond the measured data.
- No full-chip flow of any kind: the fabric was not placed, nothing was
  routed, no hard macro was integrated into a floorplan, and
  `rtl2gdsagi` was not used.
<!-- STAGE5_RESULTS_END -->
