#!/usr/bin/env python3
"""Stage 6: regenerate the README entry point from reports/final_report.json.

Everything above the first appendix is generated here.  The appendices, and the
marker-delimited results blocks inside them, are left exactly as the per-stage
renderers wrote them.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reports", "final_report.json")
README = os.path.join(ROOT, "README.md")
SPLIT = "## Appendix A —"


def n(x):
    """Thousands separators: these tables are read by humans."""
    return "{:,}".format(x)


def render(f: dict) -> str:
    m, q, a = f["model"], f["quantization"], f["architecture"]
    d = f["dual_target_portability"]
    b = f["behavioral_verification"]
    p = f["physical_openrom"]
    ar = f["area"]
    fr, gr = d["fpga"]["resources"], d["generic"]["resources"]
    gf = d["fpga"]["gate_level"]["no_stall"]
    gg = d["generic"]["gate_level"]["no_stall"]
    oc = a["operation_counts"]
    cyc = a["latency"]["nominal_cycles"]
    L = []
    add = L.append

    # ---------------------------------------------------------------- intro
    add("# model2rtl")
    add("")
    add("**Turn a trained neural network into a chip design.**")
    add("")
    add("You give it a trained Keras model. It gives you Verilog: real, "
        "synthesizable hardware that computes exactly the same answers.")
    add("")
    add("```bash")
    add("model2rtl --model my_model.h5 --output ./rtlout")
    add("```")
    add("")
    add("That is the whole idea. The rest of this page is how to actually do "
        "it, what works, and what does not.")
    add("")
    add("> **New to hardware?** You do not need an FPGA, a chip, or any "
        "expensive tools. Everything here runs on a laptop with free, "
        "open-source software. Start at [Quick start](#quick-start).")
    add("")

    # ---------------------------------------------------------------- what
    add("## What this actually does")
    add("")
    add("A neural network is multiplications and additions. A chip can do "
        "those directly, without a CPU, if you describe the circuit. That "
        "description is written in a language called **Verilog**, and writing "
        "it by hand for a whole network is slow and error-prone.")
    add("")
    add("`model2rtl` writes it for you:")
    add("")
    add("```")
    add("  my_model.h5            ->   model2rtl   ->   mlp_fabric.v")
    add("  (trained in Keras)                           mlp_params.v")
    add("                                               mlp_top.v")
    add("                                               (Verilog you can simulate")
    add("                                                or send to a chip flow)")
    add("```")
    add("")
    add("The interesting part is *how* it builds the circuit. A network with "
        "%s connections would need %s multipliers if you built one per "
        "connection. This design uses **%d**, by exploiting the fact that "
        "the weights were squeezed down to only %d possible values. More on "
        "that in [How it works](#how-it-works)."
        % (n(q["synapses"]["total"]), n(q["synapses"]["total"]),
           oc["implemented_active_shared_product_expressions"],
           len(q["weight_alphabet"])))
    add("")

    # ---------------------------------------------------------------- install
    add("## Install")
    add("")
    add("You need Python 3.9 or newer.")
    add("")
    add("```bash")
    add("git clone <this repo> && cd model2rtl")
    add("python3 -m venv .venv")
    add("source .venv/bin/activate")
    add("")
    add("pip install -e .              # the compiler (needs only numpy)")
    add("pip install -e \".[train]\"      # add this to read .h5 files (installs TensorFlow)")
    add("```")
    add("")
    add("To *simulate* the Verilog you also need two free tools:")
    add("")
    add("```bash")
    add("# Ubuntu / Debian")
    add("sudo apt install iverilog yosys")
    add("")
    add("# macOS")
    add("brew install icarus-verilog yosys")
    add("```")
    add("")
    add("| Tool | What it is | Needed for |")
    add("|---|---|---|")
    add("| Icarus Verilog (`iverilog`) | a Verilog simulator | running the generated hardware |")
    add("| Yosys | a synthesis tool | turning Verilog into logic gates |")
    add("")
    add("Neither is needed just to *generate* the Verilog.")
    add("")

    # ---------------------------------------------------------------- quick
    add("## Quick start")
    add("")
    add("Copy-paste this. It trains a small network, compiles it to hardware, "
        "and checks the hardware elaborates. Takes about a minute.")
    add("")
    add("**1. Train something to compile**")
    add("")
    add("```python")
    add("# save as train_demo.py")
    add("import numpy as np, tensorflow as tf")
    add("")
    add("(x, y), (xt, yt) = tf.keras.datasets.mnist.load_data()")
    add("x, xt = x.reshape(-1, 784) / 255.0, xt.reshape(-1, 784) / 255.0")
    add("")
    add("model = tf.keras.Sequential([")
    add("    tf.keras.layers.Input((784,)),")
    add("    tf.keras.layers.Dense(32, activation='relu'),   # hidden layer")
    add("    tf.keras.layers.Dense(10, activation='softmax') # 10 digits")
    add("])")
    add("model.compile(optimizer='adam',")
    add("              loss='sparse_categorical_crossentropy',")
    add("              metrics=['accuracy'])")
    add("model.fit(x, y, epochs=5, batch_size=128)")
    add("model.save('demo.h5')")
    add("")
    add("# save some test images for the compiler to measure against")
    add("np.savez('calib.npz', x=(xt[:2000] * 255).astype('uint8'), y=yt[:2000])")
    add("```")
    add("")
    add("```bash")
    add("python train_demo.py")
    add("```")
    add("")
    add("**2. Compile it to hardware**")
    add("")
    add("```bash")
    add("model2rtl --model demo.h5 --calibration calib.npz \\")
    add("          --output ./rtlout --check")
    add("```")
    add("")
    add("You will see something like:")
    add("")
    add("```")
    add("loaded demo.h5: 784 -> 32 -> ReLU -> 10")
    add("calibration: 2000 samples with labels")
    add("quantized: shift 8, input scale 0.0039215686")
    add("  float 0.9310 -> integer 0.9120 on calibration (-1.90 points)")
    add("")
    add("wrote ./rtlout")
    add("  mlp_fabric.v      ...")
    add("  mlp_params.v      ...")
    add("  mlp_params_sel.v  ...")
    add("  mlp_top.v         ...")
    add("  compile_report.json")
    add("")
    add("fabric is weight independent: True")
    add("latency: %d cycles per inference (architectural only)" % cyc)
    add("icarus: OK")
    add("yosys:  OK")
    add("```")
    add("")
    add("That's it. `./rtlout` now contains a working hardware design.")
    add("")
    add("> **`-1.90 points` is normal.** Squeezing weights down to %d values "
        "costs some accuracy. If that bothers you, see "
        "[Getting the accuracy back](#getting-the-accuracy-back)."
        % len(q["weight_alphabet"]))
    add("")

    # ---------------------------------------------------------------- files
    add("## What you get")
    add("")
    add("| File | What it is | Contains your weights? |")
    add("|---|---|---|")
    add("| `mlp_fabric.v` | the compute engine: multipliers, adders, control | **no** |")
    add("| `mlp_params.v` | your trained weights, as a read-only memory | yes |")
    add("| `mlp_params_sel.v` | a small file that connects the two | no |")
    add("| `mlp_top.v` | the top level, wires everything together | no |")
    add("| `compile_report.json` | every number, hash and setting used | — |")
    add("| `param_images/` | the weights in a plain, checkable format | yes |")
    add("")
    add("Only **one** of those files depends on your model. Train a different "
        "network of the same shape and `mlp_fabric.v` comes out byte-for-byte "
        "identical — the compiler checks this on every single run and refuses "
        "to finish if it is ever untrue.")
    add("")

    # ---------------------------------------------------------------- use it
    add("## Using the hardware")
    add("")
    add("The design has a simple handshake. To classify one input:")
    add("")
    add("```")
    add("  1. hold rst high for a few cycles, then drop it")
    add("  2. pulse start high for one cycle")
    add("  3. in_ready goes high -> feed one value per cycle")
    add("     (set in_valid high and put the value on in_data)")
    add("  4. wait for done to pulse high")
    add("  5. read prediction (the winning class) and logits (the raw scores)")
    add("```")
    add("")
    add("| Port | Direction | Meaning |")
    add("|---|---|---|")
    add("| `clk` | in | clock |")
    add("| `rst` | in | reset, active high, synchronous |")
    add("| `start` | in | pulse for one cycle to begin |")
    add("| `in_ready` | out | the design is ready for an input value |")
    add("| `in_valid` | in | you are providing a valid input value |")
    add("| `in_data` | in | one input value, 0-255 |")
    add("| `busy` | out | an inference is in progress |")
    add("| `done` | out | pulses high for one cycle when finished |")
    add("| `prediction` | out | the winning class index |")
    add("| `logits` | out | all raw scores, packed together |")
    add("")
    add("A minimal testbench:")
    add("")
    add("```verilog")
    add("// save as tb.v, then:")
    add("//   iverilog -g2001 -o sim tb.v rtlout/*.v && ./sim")
    add("`timescale 1ns/1ps")
    add("module tb;")
    add("    reg clk = 0;  always #5 clk = ~clk;")
    add("    reg rst = 1, start = 0, in_valid = 0;")
    add("    reg [7:0] in_data = 0;")
    add("    wire in_ready, busy, done, prediction_valid;")
    add("    wire [3:0] prediction;")
    add("    wire [179:0] logits;")
    add("    integer i;")
    add("")
    add("    mlp_top dut (.clk(clk), .rst(rst), .start(start),")
    add("        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),")
    add("        .busy(busy), .done(done), .prediction_valid(prediction_valid),")
    add("        .prediction(prediction), .logits(logits));")
    add("")
    add("    initial begin")
    add("        repeat (4) @(negedge clk);")
    add("        rst = 0;                       // 1. release reset")
    add("        @(negedge clk); start = 1;     // 2. kick it off")
    add("        @(negedge clk); start = 0;")
    add("")
    add("        i = 0;                         // 3. feed 784 pixels")
    add("        while (i < 784) begin")
    add("            if (in_ready) begin")
    add("                in_valid = 1;")
    add("                in_data  = i[7:0];     // put your real pixel here")
    add("                i = i + 1;")
    add("            end else in_valid = 0;")
    add("            @(negedge clk);")
    add("        end")
    add("        in_valid = 0;")
    add("")
    add("        while (!done) @(negedge clk);  // 4. wait")
    add('        $display("predicted class = %0d", prediction);  // 5. read')
    add("        $finish;")
    add("    end")
    add("endmodule")
    add("```")
    add("")
    add("One classification takes **%d clock cycles** for this network shape "
        "(`inputs + 2 x hidden + outputs + 6`). It processes one input value "
        "per cycle rather than all at once, which keeps the circuit small." % cyc)
    add("")

    # ---------------------------------------------------------------- models
    add("## What models are supported")
    add("")
    add("Exactly one shape, on purpose:")
    add("")
    add("```")
    add("Input -> Dense(any size) -> ReLU -> Dense(any size) -> output")
    add("```")
    add("")
    add("| Supported | Not supported |")
    add("|---|---|")
    add("| 2 `Dense` layers, any width | 3 or more `Dense` layers |")
    add("| `relu` on the hidden layer | any other hidden activation |")
    add("| `softmax`, `sigmoid` or none on the output | `tanh` etc. on the output |")
    add("| `.h5`, `.keras`, or `.npz` with `w1,b1,w2,b2` | SavedModel folders, ONNX, TFLite, PyTorch |")
    add("| `Flatten`, `Dropout`, `Input` (ignored) | convolution, pooling, batch-norm, RNN |")
    add("")
    add("If your model is not supported the compiler **stops and tells you "
        "what it found**. It never quietly compiles part of your network. "
        "Real examples from testing:")
    add("")
    add("```")
    add("$ model2rtl --model housing.keras --output ./out")
    add("model2rtl: cannot compile this model.")
    add("expected exactly 2 Dense layers, found 3. This compiler builds")
    add("input -> Dense -> ReLU -> Dense only.")
    add("Layers found: Dense(hidden_1), Dense(hidden_2), Dense(output)")
    add("")
    add("$ model2rtl --model convnet_weights.npz --output ./out")
    add("model2rtl: cannot compile this model.")
    add("inconsistent shapes: w1 (3, 3, 1, 32), w2 (1600, 10)")
    add("```")
    add("")
    add("That second one is a convolutional network. The refusal is the "
        "correct answer: compiling it anyway would produce hardware that "
        "computes something other than your model.")
    add("")

    # ---------------------------------------------------------------- accuracy
    add("## Getting the accuracy back")
    add("")
    add("Weights are stored as one of only %d values. Your model was not "
        "trained expecting that, so it loses a little accuracy. Two options:"
        % len(q["weight_alphabet"]))
    add("")
    add("**Default (fast, no training needed):**")
    add("")
    add("```bash")
    add("model2rtl --model demo.h5 --calibration calib.npz --output ./out")
    add("```")
    add("")
    add("**Fine-tuning (slower, much better):**")
    add("")
    add("```bash")
    add("model2rtl --model demo.h5 --calibration calib.npz \\")
    add("          --quantize qat --epochs 25 --output ./out")
    add("```")
    add("")
    add("This retrains the weights *while pretending they are already "
        "squeezed*, so they settle in places that survive it. Measured on a "
        "Fashion-MNIST model, held-out data:")
    add("")
    add("| | Accuracy |")
    add("|---|---|")
    add("| original float model | 83.0% |")
    add("| default quantization | 82.7% |")
    add("| with `--quantize qat` | **86.0%** |")
    add("")
    add("> **Always pass `--calibration`.** Without it the compiler cannot "
        "measure anything and has to guess a key setting. It will warn you "
        "loudly. The file is just an `.npz` with `x` (inputs) and ideally "
        "`y` (labels).")
    add("")

    # ---------------------------------------------------------------- cli
    add("## Command reference")
    add("")
    add("| Option | Meaning |")
    add("|---|---|")
    add("| `--model PATH` | trained model: `.h5`, `.keras`, or `.npz` |")
    add("| `--indices PATH` | an already-quantized model; skips quantization |")
    add("| `--output DIR` | where to write the Verilog (required) |")
    add("| `--calibration PATH` | `.npz` with `x` and ideally `y`; strongly recommended |")
    add("| `--quantize ptq\\|qat` | `ptq` (default, fast) or `qat` (fine-tune, better) |")
    add("| `--epochs N` | fine-tuning epochs, default 20 |")
    add("| `--prefix NAME` | name your modules, default `mlp` |")
    add("| `--input-scale F` | if your model expects `x/255`, this is `0.00392157`. Auto-detected by default |")
    add("| `--shift N` | force an internal setting; normally chosen by measurement |")
    add("| `--check` | run Icarus and Yosys on the result |")
    add("| `--quiet` | less output |")
    add("")

    # ---------------------------------------------------------------- results
    add("## Does it actually work?")
    add("")
    add("The reference MNIST model was checked at every level. Not "
        "\"it compiled\" — actually simulated and compared, number by number.")
    add("")
    add("| Check | Result |")
    add("|---|---|")
    add("| Original float accuracy | %.2f%% |" % (100 * m["float_test_accuracy"]))
    add("| After quantization | %.2f%% |"
        % (100 * m["quantized_integer_test_accuracy"]))
    add("| Hardware simulation vs the maths, %d images | **%d differences** |"
        % (b["images"], b["portable_backend"]["logit_mismatches"]))
    add("| Internal signals checked, cycle by cycle | %s checks, %d failures |"
        % (n(b["cycle_level_trace"]["total_checks"]),
           b["cycle_level_trace"]["failures"]))
    add("| After FPGA synthesis, %d images | **%d differences** |"
        % (gf["images"], gf["logit_mismatches"]))
    add("| After generic chip synthesis, %d images | **%d differences** |"
        % (gg["images"], gg["logit_mismatches"]))
    add("| Automated tests | 429 passing |")
    add("")
    add("Synthesized size, measured with real tools:")
    add("")
    add("| | iCE40 FPGA | Generic gates |")
    add("|---|---|---|")
    add("| logic cells | %s LUTs | %s cells |" % (n(fr["lut"]), n(gr["total_cells"])))
    add("| registers | %s | %s |" % (n(fr["ff"]), n(gr["sequential"])))
    add("| memory blocks | %d | 0 (built from gates) |" % fr["ram"])
    add("| **multipliers / DSPs** | **%d** | **%d** |"
        % (fr["dsp"], gr["arithmetic_or_multiplier_cells"]))
    add("")
    add("Zero multipliers. The tools discovered that multiplying by a fixed "
        "small number is just shifting and adding, and removed them all.")
    add("")

    # ---------------------------------------------------------------- how
    add("## How it works")
    add("")
    add("Every weight is one of %d fixed values (%s). So for any input value "
        "`x`, there are only %d possible products it can ever be involved in "
        "— no matter how many neurons it feeds."
        % (len(q["weight_alphabet"]),
           ", ".join(str(v) for v in q["weight_alphabet"][:3]) + " ... "
           + ", ".join(str(v) for v in q["weight_alphabet"][-2:]),
           len(q["weight_alphabet"])))
    add("")
    add("So compute those %d products **once**, and let every neuron pick the "
        "one it needs:" % len(q["weight_alphabet"]))
    add("")
    add("```")
    add("                          one input value x")
    add("                                |")
    add("        +-----------+-----------+-----------+-----------+")
    add("        |           |           |           |           |")
    add("      x * -8      x * -7      .....       x * +6      x * +7")
    add("        |           |           |           |           |")
    add("        +----------- 16 products, computed once ---------+")
    add("                                |")
    add("              +-----------+------+------+-----------+")
    add("              |           |             |           |")
    add("           neuron 0    neuron 1  .....  neuron N")
    add("            picks       picks           picks       <- each uses its")
    add("            one         one             one            4-bit weight")
    add("              |           |               |")
    add("            add to      add to          add to")
    add("            total       total           total")
    add("```")
    add("")
    add("This is called **Multiply-Select-Add**. Inputs are fed one per cycle "
        "and every neuron accumulates in parallel, so the same %d products "
        "serve the whole network, both layers included."
        % len(q["weight_alphabet"]))
    add("")
    add("The trade: it takes %d cycles instead of doing everything at once. "
        "You are exchanging speed for a much smaller circuit." % cyc)
    add("")

    # ---------------------------------------------------------------- trouble
    add("## Troubleshooting")
    add("")
    add("| Message | What to do |")
    add("|---|---|")
    add("| `expected exactly 2 Dense layers, found 3` | Your model is too deep. Only 2 dense layers are supported. |")
    add("| `unrecognised model format` | Save as `.h5` or `.keras`: `model.save('m.h5')` |")
    add("| `reading a Keras model needs TensorFlow` | `pip install -e \".[train]\"` |")
    add("| `no ReLU was found between the two Dense layers` | Use `activation='relu'` on the hidden layer. |")
    add("| `NO LABELLED CALIBRATION DATA` | Pass `--calibration` with an `.npz` containing `x` and `y`. |")
    add("| `bias does not fit N signed bits` | Your biases are very large relative to the weights. Retrain with a smaller learning rate or normalise your inputs. |")
    add("| Accuracy dropped a lot | Use `--quantize qat --epochs 30`. |")
    add("| `icarus: not on PATH, skipped` | Install `iverilog` if you want the check to run. |")
    add("")

    # ---------------------------------------------------------------- limits
    add("## What this is not")
    add("")
    add("Being clear about this matters more than looking impressive.")
    add("")
    add("- **Not a finished chip.** You get Verilog. Turning that into "
        "silicon needs a full manufacturing flow that is not included.")
    add("- **Not FPGA-ready-to-flash.** No place-and-route, no timing "
        "analysis, no bitstream. The design synthesizes; nobody has fitted "
        "it to a real device.")
    add("- **No speed claims.** Cycle counts are exact, clock speed is not "
        "measured. Any MHz figure here would be made up.")
    add("- **Two dense layers only.** No convolution, no transformers, no "
        "ONNX or TFLite import.")
    add("- **The SKY130 chip memories are experimental.** They generate and "
        "their contents are verified exactly, but the manufacturing checks "
        "(DRC/LVS) cannot be trusted in this environment: the vendor's own "
        "reference design fails them here too. Status: **%s**."
        % p["signoff"]["status"])
    add("")

    # ---------------------------------------------------------------- more
    add("## Going deeper")
    add("")
    add("| Document | What is in it |")
    add("|---|---|")
    add("| **[FINAL-REPORT.md](FINAL-REPORT.md)** | the full technical report: architecture, quantization, verification, area |")
    add("| [`reports/final_report.json`](reports/final_report.json) | every measurement, machine-readable |")
    add("| [`reports/results.csv`](reports/results.csv) | headline numbers with their source |")
    add("| Appendices below | stage-by-stage evidence, regenerated from the reports |")
    add("")
    add("To rebuild the reference MNIST design and re-run everything:")
    add("")
    add("```bash")
    add("python scripts/train_mnist_mlp.py --sweep-hidden-shift")
    add("python scripts/gen_compute_fabric.py")
    add("python scripts/verify_stage3.py --images 500")
    add("python -m pytest tests -q")
    add("```")
    add("")
    add("This project does not import from, depend on, or modify "
        "`rtl2gdsagi`.")
    add("")
    add("---")
    add("")
    add("The appendices below are the detailed per-stage evidence behind the "
        "numbers above. They are generated from the stage reports, not "
        "written by hand. Start with [FINAL-REPORT.md](FINAL-REPORT.md) if "
        "you want the narrative rather than the raw evidence.")
    add("")
    return "\n".join(L)


def main() -> int:
    if not os.path.exists(SRC):
        print("missing %s: run scripts/build_final_report.py first" % SRC)
        return 1
    f = json.load(open(SRC))
    text = open(README).read()
    if SPLIT not in text:
        print("README appendix marker %r missing" % SPLIT)
        return 1
    tail = text[text.index(SPLIT):]
    head = render(f)                      # render BEFORE opening for write
    tmp = README + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(head + tail)
    os.replace(tmp, README)
    print("README.md entry point regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
