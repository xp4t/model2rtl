"""The parameter-memory interface is a transcription of the frozen fabric."""

import hashlib
import os

import pytest

from model2rtl import memif
from model2rtl.fabric import FabricConfig, derive_widths


def test_interface_matches_the_frozen_fabric_rtl(fabric_path):
    memif.verify_against_rtl(fabric_path)          # fails closed on any drift


def test_fabric_was_not_modified_by_stage2(fabric_path, stage1_report):
    with open(fabric_path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    assert sha == stage1_report["generated"]["sha256"], \
        "rtl/mnist_mlp_fabric.v changed since Stage 1; Stage 2 must not touch it"


def test_declared_ports_are_exactly_the_stage1_ports(fabric_path):
    ports = memif.parse_fabric_ports(fabric_path)
    assert ports["wmem_en"] == ("output", 1)
    assert ports["wmem_layer"] == ("output", 1)
    assert ports["wmem_addr"] == ("output", 10)
    assert ports["wmem_data"] == ("input", 128)
    assert ports["bmem_en"] == ("output", 1)
    assert ports["bmem_layer"] == ("output", 1)
    assert ports["bmem_addr"] == ("output", 6)
    assert ports["bmem_data"] == ("input", 22)
    assert ports["clk"] == ("input", 1)


def test_address_spaces_are_the_four_required_memories():
    iface = memif.build_interface()
    spaces = {s.name: s for kind in ("weight", "bias") for s in iface[kind].spaces}
    assert spaces["layer1_weights"].depth == 784
    assert spaces["layer1_weights"].used_data_bits == 128
    assert spaces["layer2_weights"].depth == 32
    assert spaces["layer2_weights"].used_data_bits == 40
    assert spaces["bias_l1"].depth == 32 if "bias_l1" in spaces else True
    assert spaces["layer1_bias"].depth == 32
    assert spaces["layer1_bias"].used_data_bits == 22
    assert spaces["layer2_bias"].depth == 10
    assert spaces["layer2_bias"].used_data_bits == 17


def test_timing_contract_is_one_cycle_synchronous_read():
    iface = memif.build_interface()
    assert iface["read_latency"] == 1
    t = iface["timing_contract"].lower()
    assert "cycle t" in t and "cycle t+1" in t
    assert "hold" in t


def test_packing_is_the_stage0_orientation_not_transposed():
    p = memif.build_interface()["packing"]
    assert p["rule"] == "weight_index[i][j] = wmem_data[j*4 +: 4]"
    assert "in_features, out_features" in p["orientation"]
    assert "least significant" in p["neuron0_position"]


def test_storage_footprint():
    f = memif.storage_footprint()
    assert f["layer1_weight_bits"] == 784 * 32 * 4 == 100352
    assert f["layer2_weight_bits"] == 32 * 10 * 4 == 1280
    assert f["weight_bits_total"] == 101632
    assert f["all_parameter_bits"] == 101632 + 32 * 22 + 10 * 17
