"""Backend A: the portable parameter memory."""

import hashlib
import os
import re

import pytest

from model2rtl import sim as SIM
from model2rtl.fabric import FabricConfig
from model2rtl.param_verilog import emit_portable
from conftest import require_tool


def _strip(src):
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


@pytest.fixture(scope="session")
def portable_src(portable_rtl):
    return open(portable_rtl).read()


def test_generator_is_deterministic_and_the_file_is_current(param_images,
                                                            portable_src):
    a = emit_portable(param_images)
    assert a == emit_portable(param_images)
    assert a == portable_src, ("rtl/mnist_mlp_params_portable.v is stale; "
                               "re-run scripts/gen_weight_rom_portable.py")


def test_no_forbidden_construct(portable_src):
    body = _strip(portable_src)
    for token in ["$readmem", "initial ", "logic ", "always_ff", "always_comb",
                  "typedef", "import ", "interface ", "(* ", "synthesis ",
                  "specify", "RAM_STYLE", "ram_style", "force ", "release ",
                  "#", "SB_RAM", "DSP48", "sky130_fd_", "openram"]:
        assert token not in body, "forbidden construct %r in the portable backend" % token
    assert "negedge" not in body
    assert body.count("always @(posedge clk)") == 2


def test_output_is_registered_and_holds_when_disabled(portable_src):
    body = _strip(portable_src)
    # the case statements live inside clocked blocks, and there is no else, so
    # the registers hold when the enable is low
    assert re.search(r"always @\(posedge clk\) begin\s*\n\s*if \(wmem_en\)", body)
    assert re.search(r"always @\(posedge clk\) begin\s*\n\s*if \(bmem_en\)", body)


def test_every_row_is_present_exactly_once(portable_src, param_images):
    body = _strip(portable_src)
    w1 = re.findall(r"10'd(\d+): wmem_data <= 128'h", body)
    b1 = re.findall(r"6'd(\d+): bmem_data <= 22'h", body)
    # 784 layer-1 rows plus 32 layer-2 rows (the latter use a padded literal)
    w2 = re.findall(r"10'd(\d+): wmem_data <= \{88'd0, 40'h", body)
    assert len(w1) == 784 and sorted(map(int, w1)) == list(range(784))
    assert len(w2) == 32 and sorted(map(int, w2)) == list(range(32))
    assert len(b1) == 42            # 32 layer-1 biases + 10 layer-2 biases
    assert body.count("default: wmem_data <=") == 2
    assert body.count("default: bmem_data <=") == 2


def test_layer2_weight_high_bits_are_hardwired_zero(portable_src):
    assert "{88'd0, 40'h" in portable_src
    assert re.search(r"\{88'd0, 40'h[0-9a-f]{10}\}", portable_src)


def test_constants_match_the_canonical_images(portable_src, param_images):
    body = _strip(portable_src)
    for addr, val in list(enumerate(param_images["weights_l1"].rows))[:: 97]:
        assert "10'd%d: wmem_data <= 128'h%032x;" % (addr, val) in body
    for addr, val in enumerate(param_images["weights_l2"].rows):
        assert "10'd%d: wmem_data <= {88'd0, 40'h%010x};" % (addr, val) in body


def test_iverilog_compiles_in_strict_verilog2001(portable_rtl, tmp_path):
    require_tool("iverilog")
    r = SIM.iverilog_compile([portable_rtl], str(tmp_path / "a.out"),
                             str(tmp_path), std="2001")
    assert r.returncode == 0, r.output
    assert "warning" not in r.output.lower(), r.output


def test_yosys_elaborates_clean(portable_rtl):
    require_tool("yosys")
    res = SIM.yosys_check(portable_rtl, "mnist_mlp_params_portable")
    assert res["ok"], res["log"][-3000:]
    assert res["latch_lines"] == []
    assert "multiple conflicting drivers" not in res["log"]
    assert "is used but has no driver" not in res["log"]
    assert "Found and reported 0 problems." in res["log"]
