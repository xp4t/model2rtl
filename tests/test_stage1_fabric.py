"""Stage-1 fabric: lint, elaboration, structure, protocol and real inference.

Every check here runs against the committed rtl/mnist_mlp_fabric.v, and every
expected value comes from the Stage-0 NumPy integer golden model -- never from
Keras and never from the RTL itself.
"""

import json
import os
import re

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl import fabric as F
from model2rtl import sim as SIM
from conftest import require_tool


def _strip_comments(src: str) -> str:
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def cycles_formula(cfg: F.FabricConfig) -> int:
    """start cycle .. done cycle inclusive."""
    return cfg.n_in + 2 * cfg.n_hidden + cfg.n_out + 6


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def test_generator_output_is_deterministic(cfg, fabric_source):
    from model2rtl.verilog_emit import emit_fabric_verilog
    a = emit_fabric_verilog(cfg)
    b = emit_fabric_verilog(cfg)
    assert a == b
    assert a == fabric_source, ("rtl/mnist_mlp_fabric.v is stale; re-run "
                               "scripts/gen_compute_fabric.py")


def test_widths_agree_with_the_frozen_stage0_contract(cfg):
    F.check_production_widths(cfg)
    w = F.derive_widths(cfg)
    l1, l2 = C.layer1_widths(), C.layer2_widths()
    assert w["product_bits"] == l1.product_bits == 12
    assert w["layer1_acc_bits"] == l1.accumulator_bits == 23
    assert w["layer2_acc_bits"] == l2.accumulator_bits == 18
    assert w["layer1_bias_bits"] == l1.bias_bits == 22
    assert w["layer2_bias_bits"] == l2.bias_bits == 17
    assert w["requant_shift"] == C.HIDDEN_REQUANT_SHIFT == 8
    assert w["round_const"] == 128


# ---------------------------------------------------------------------------
# Language-level constraints
# ---------------------------------------------------------------------------

def test_rtl_is_verilog2001_only(fabric_source):
    body = _strip_comments(fabric_source)
    banned = [
        "logic ", "always_ff", "always_comb", "always_latch", "typedef",
        "interface ", "package ", "import ", "bit ", "byte ", "shortint",
        "longint", "unique ", "priority ", "endinterface", "$display",
        "initial ", "#", "force ", "release ", "(* ", "synthesis ",
        "// synopsys", "specify", "$readmem", "wire signed [11:0] prod_16",
    ]
    for token in banned:
        assert token not in body, "banned construct %r in the fabric" % token
    # single clock, single synchronous reset
    assert body.count("posedge clk") == body.count("always @(posedge clk)")
    assert "negedge" not in body
    assert "posedge rst" not in body


def test_rtl_declares_no_vendor_or_tool_specific_content(fabric_source):
    lowered = fabric_source.lower()
    for token in ["dsp48", "sb_mac16", "altera", "xilinx", "lattice", "ice40",
                  "ecp5", "sky130", "ram_style", "rom_style", "keep_hierarchy",
                  "dont_touch", "blackbox"]:
        assert token not in lowered


def test_iverilog_compiles_the_fabric_in_strict_verilog2001(fabric_path, tmp_path):
    require_tool("iverilog")
    r = SIM.iverilog_compile([fabric_path], str(tmp_path / "f.out"),
                             str(tmp_path), std="2001")
    assert r.returncode == 0, r.output
    # -Wall must be silent too: warnings here are real problems
    assert "warning" not in r.output.lower(), r.output


# ---------------------------------------------------------------------------
# Yosys
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def yosys_result(fabric_path):
    require_tool("yosys")
    return SIM.yosys_check(fabric_path, "mnist_mlp_fabric")


def test_yosys_parses_elaborates_and_checks_clean(yosys_result):
    assert yosys_result["returncode"] == 0, yosys_result["log"][-4000:]
    assert not yosys_result["problem_markers"], yosys_result["log"][-4000:]
    assert "ERROR" not in yosys_result["log"]
    # prove the structural check actually ran, and reported zero problems
    assert "Found and reported 0 problems." in yosys_result["log"], \
        "yosys 'check -assert' did not report a clean result"
    assert not re.search(r"Found and reported ([1-9]\d*) problems",
                         yosys_result["log"])


def test_yosys_infers_no_latches(yosys_result):
    assert yosys_result["latch_lines"] == [], yosys_result["latch_lines"]
    assert "$dlatch" not in yosys_result["cells"]
    assert "$_DLATCH_" not in str(yosys_result["cells"])


def test_yosys_reports_no_multiple_drivers_or_undriven_nets(yosys_result):
    log = yosys_result["log"]
    assert "multiple conflicting drivers" not in log
    assert "used but has no driver" not in log


# ---------------------------------------------------------------------------
# Structural proof of Multiply-Select-Add sharing
# ---------------------------------------------------------------------------

def test_source_contains_exactly_K_product_generators(fabric_source, cfg):
    body = _strip_comments(fabric_source)
    prods = re.findall(r"wire signed \[\d+:0\] prod_\d+ = "
                       r"\$signed\(\{[^}]*act_pipe\}\) \* ALPHA_\d+;", body)
    assert len(prods) == cfg.k == 16, \
        "expected exactly %d shared product generators, found %d" % (cfg.k, len(prods))

    # every other '*' in the file must be an elaboration-time constant index
    # expression or an always @(*) sensitivity list -- never a datapath multiply
    stars = []
    for line in body.split("\n"):
        if "*" not in line:
            continue
        if re.search(r"prod_\d+ = ", line):
            continue
        for m in re.finditer(r"\*", line):
            ctx = line.strip()
            allowed = ("always @(*)" in ctx or
                       re.search(r"\b(gj|K)\s*\*\s*[A-Z_]+", ctx))
            stars.append((ctx, allowed))
    bad = [c for c, ok in stars if not ok]
    assert bad == [], "unexpected multiplication(s) in the fabric: %s" % bad


def test_all_selectors_read_the_same_shared_bank(fabric_source, cfg):
    body = _strip_comments(fabric_source)
    # one selector instantiation per neuron, in generate loops
    assert body.count(".bank     (prod_bank)") == 2, \
        "selectors must all bind the single shared prod_bank"
    assert "for (gj = 0; gj < N_HID; gj = gj + 1) begin : L1_SELECT" in body
    assert "for (gj = 0; gj < N_OUT; gj = gj + 1) begin : L2_SELECT" in body
    # no per-synapse product anywhere
    assert not re.search(r"act_pipe\s*\*\s*w", body)
    assert body.count("prod_bank") >= 3


def test_netlist_has_exactly_K_multipliers_and_one_selector_per_neuron(
        yosys_result, cfg):
    cells = yosys_result["cells"]
    assert cells.get("$mul") == cfg.k == 16, \
        ("the elaborated netlist must contain exactly K=%d multipliers "
         "(one shared product bank), found %s" % (cfg.k, cells.get("$mul")))
    assert cells.get("mnist_mlp_fabric_msa_select") == cfg.n_hidden + cfg.n_out == 42
    # a naive fabric would need 25408 multipliers; a fully spatial MSA 13056
    assert cells["$mul"] < cfg.n_in * cfg.n_hidden


# ---------------------------------------------------------------------------
# Real inference against the Stage-0 golden model
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def rtl_run(integer_model, mnist_test, cfg, fabric_path, tmp_path_factory):
    require_tool("iverilog")
    x, y = mnist_test
    n = 16
    d = tmp_path_factory.mktemp("rtl_mnist")
    out = SIM.simulate(str(d), cfg, integer_model.layer1_weight_indices,
                       integer_model.layer1_bias,
                       integer_model.layer2_weight_indices,
                       integer_model.layer2_bias, x[:n], fabric_path=fabric_path)
    return out, x[:n], y[:n], n


def test_rtl_logits_match_the_golden_model_bit_exactly(rtl_run, integer_model):
    out, x, y, n = rtl_run
    golden_logits = integer_model.forward(x)
    assert out.logits.shape == golden_logits.shape
    assert np.array_equal(out.logits, golden_logits), \
        "logit mismatch: %s" % (out.logits - golden_logits)


def test_rtl_predictions_match_the_golden_model(rtl_run, integer_model):
    out, x, y, n = rtl_run
    assert np.array_equal(np.array(out.predictions),
                          integer_model.predict(x))


def test_rtl_hidden_activations_match_the_golden_model(rtl_run, integer_model):
    from model2rtl.golden import alphabet_lookup, requantize_relu_u8
    out, x, y, n = rtl_run
    w1 = alphabet_lookup(integer_model.layer1_weight_indices)
    acc1 = x.astype(np.int64) @ w1
    assert np.array_equal(out.acc1, acc1), "layer-1 dot products differ"
    hidden = requantize_relu_u8(acc1 + integer_model.layer1_bias)
    assert np.array_equal(out.hidden, hidden), "hidden activations differ"


def test_rtl_cycle_count_is_deterministic_and_matches_the_architecture(rtl_run, cfg):
    out, x, y, n = rtl_run
    assert len(set(out.cycles)) == 1, "inference latency is data dependent: %s" % out.cycles
    assert out.cycles[0] == cycles_formula(cfg) == 864


def test_back_to_back_inferences_do_not_leak_state(rtl_run, integer_model):
    """16 images ran through one instance without reset in between."""
    out, x, y, n = rtl_run
    assert np.array_equal(out.logits, integer_model.forward(x))
    assert len(out.logits) == n == 16


def test_handshake_is_honoured_when_the_driver_stalls(integer_model, mnist_test,
                                                     cfg, fabric_path, tmp_path):
    require_tool("iverilog")
    x, _ = mnist_test
    out = SIM.simulate(str(tmp_path), cfg, integer_model.layer1_weight_indices,
                       integer_model.layer1_bias,
                       integer_model.layer2_weight_indices,
                       integer_model.layer2_bias, x[:3],
                       fabric_path=fabric_path, stall=7)
    assert np.array_equal(out.logits, integer_model.forward(x[:3])), \
        "results changed when the input stream stalled"
    assert out.cycles[0] > cycles_formula(cfg), \
        "stalling did not lengthen the inference: the handshake is being ignored"


# ---------------------------------------------------------------------------
# Parameterised (synthetic) topology
# ---------------------------------------------------------------------------

def test_small_synthetic_topology_matches_the_msa_reference(tmp_path):
    require_tool("iverilog")
    from model2rtl.verilog_emit import emit_fabric_verilog
    cfg = F.FabricConfig(n_in=6, n_hidden=4, n_out=3, module_name="tiny_fabric")
    w = F.derive_widths(cfg)
    rng = np.random.default_rng(4242)
    i1 = rng.integers(0, cfg.k, (cfg.n_in, cfg.n_hidden)).astype(np.int64)
    i2 = rng.integers(0, cfg.k, (cfg.n_hidden, cfg.n_out)).astype(np.int64)
    lim1 = 1 << (w["layer1_bias_bits"] - 2)
    lim2 = 1 << (w["layer2_bias_bits"] - 2)
    b1 = rng.integers(-lim1, lim1, cfg.n_hidden).astype(np.int64)
    b2 = rng.integers(-lim2, lim2, cfg.n_out).astype(np.int64)
    imgs = rng.integers(0, 256, (5, cfg.n_in)).astype(np.int64)

    src = os.path.join(str(tmp_path), "tiny_fabric.v")
    with open(src, "w") as fh:
        fh.write(emit_fabric_verilog(cfg))
    out = SIM.simulate(str(tmp_path), cfg, i1, b1, i2, b2, imgs, fabric_path=src)

    for n in range(imgs.shape[0]):
        want = F.msa_forward(imgs[n], i1, b1, i2, b2, cfg)
        assert np.array_equal(out.logits[n], want), \
            "tiny topology image %d: %s vs %s" % (n, out.logits[n], want)
        assert out.predictions[n] == int(np.argmax(want))
    assert out.cycles[0] == cycles_formula(cfg)


def test_small_synthetic_topology_elaborates_clean(tmp_path):
    require_tool("yosys")
    from model2rtl.verilog_emit import emit_fabric_verilog
    cfg = F.FabricConfig(n_in=6, n_hidden=4, n_out=3, module_name="tiny_fabric")
    src = os.path.join(str(tmp_path), "tiny_fabric.v")
    with open(src, "w") as fh:
        fh.write(emit_fabric_verilog(cfg))
    res = SIM.yosys_check(src, "tiny_fabric")
    assert res["ok"], res["log"][-3000:]
    assert res["cells"].get("$mul") == cfg.k == 16


# ---------------------------------------------------------------------------
# Stage-1 report consistency
# ---------------------------------------------------------------------------

def test_stage1_report_is_consistent_with_the_committed_fabric(
        stage1_report, fabric_path, cfg):
    import hashlib
    rep = stage1_report
    assert rep["stage"] == 1
    assert rep["status"] == "PASS", rep["failures"]
    with open(fabric_path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    assert rep["generated"]["sha256"] == sha, "report describes a different fabric"
    assert rep["generated"]["weight_rom_generated"] is False
    assert rep["generated"]["openram_invoked"] is False


def test_stage1_report_records_real_measurements(stage1_report, cfg):
    v = stage1_report["verification"]
    assert v["logit_mismatches"] == 0
    assert v["prediction_mismatches"] == 0
    assert v["alternate_weight_set_mismatches"] == 0
    assert v["stalled_handshake_mismatches"] == 0
    assert v["mnist_images_simulated"] >= 16
    assert v["yosys_check_assert"].startswith("PASS")
    assert v["icarus_compile_verilog2001"] == "PASS"
    assert v["yosys_latches_inferred"] == 0
    assert v["yosys_multiple_drivers"] is False
    assert v["yosys_undriven_nets"] is False
    assert v["oracle"].startswith("Stage-0 NumPy integer golden model")
    assert stage1_report["structure"]["elaborated_multiplier_cells"] == cfg.k
    a = stage1_report["architecture"]
    assert a["total_cycles_measured"] == cycles_formula(cfg)
    assert a["cycle_count_is_data_independent"] is True


def test_stage1_report_makes_no_unearned_claim(stage1_report):
    text = json.dumps(stage1_report).lower()
    for claim in ["synth_ice40", "synth_ecp5", "gate-level accuracy",
                  "openram macro generated", "gds"]:
        assert claim not in text or "no " in text, claim
    lims = " ".join(stage1_report["limitations"]).lower()
    for topic in ["weight rom", "openram", "fpga gate-level",
                  "asic gate-level", "clock frequency"]:
        assert topic in lims, "limitation %r not stated" % topic


def test_independence_shas_recorded_in_report(stage1_report):
    ind = stage1_report["independence"]
    assert ind["identical_after_weight_change"] is True
    assert ind["identical_after_bias_change"] is True
    assert ind["committed_matches_fresh_generation"] is True
    assert ind["trained_npz_restored"] is True
    assert ind["trained_npz_sha256_before"] == ind["trained_npz_sha256_after"]
    assert (ind["fabric_sha256_with_trained_weights"]
            == ind["fabric_sha256_with_alternate_weight_set"]
            == ind["fabric_sha256_with_alternate_biases"])
