import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import storage as S  # noqa: E402

PATHS = S.default_paths(ROOT)


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def paths():
    return PATHS


@pytest.fixture(scope="session")
def integer_model():
    if not os.path.exists(PATHS["npz"]):
        pytest.skip("model/mnist_weights_indices.npz missing: run "
                    "scripts/train_mnist_mlp.py first")
    return S.load_indices(PATHS["npz"])


@pytest.fixture(scope="session")
def stage0_report():
    import json
    if not os.path.exists(PATHS["report"]):
        pytest.skip("reports/stage0_quantization.json missing")
    with open(PATHS["report"]) as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def mnist_test():
    """MNIST test set as uint8, loaded from the Keras cache without training."""
    import numpy as np
    cache = os.path.expanduser("~/.keras/datasets/mnist.npz")
    if not os.path.exists(cache):
        pytest.skip("MNIST cache missing: run scripts/train_mnist_mlp.py first")
    with np.load(cache) as z:
        x = z["x_test"].reshape(-1, 784).astype(np.uint8)
        y = z["y_test"].astype(np.int64)
    return x, y


# ---------------------------------------------------------------------------
# Stage-1 fixtures
# ---------------------------------------------------------------------------

FABRIC_PATH = os.path.join(ROOT, "rtl", "mnist_mlp_fabric.v")
STAGE1_REPORT = os.path.join(ROOT, "reports", "stage1_compute_fabric.json")


@pytest.fixture(scope="session")
def fabric_path():
    if not os.path.exists(FABRIC_PATH):
        pytest.skip("rtl/mnist_mlp_fabric.v missing: run "
                    "scripts/gen_compute_fabric.py first")
    return FABRIC_PATH


@pytest.fixture(scope="session")
def fabric_source(fabric_path):
    with open(fabric_path) as fh:
        return fh.read()


@pytest.fixture(scope="session")
def cfg():
    from model2rtl.fabric import FabricConfig
    return FabricConfig()


@pytest.fixture(scope="session")
def stage1_report():
    import json
    if not os.path.exists(STAGE1_REPORT):
        pytest.skip("reports/stage1_compute_fabric.json missing")
    with open(STAGE1_REPORT) as fh:
        return json.load(fh)


def require_tool(name):
    """Fail closed: a missing EDA tool is reported, never silently skipped
    into a weaker check."""
    from model2rtl.sim import have_tool
    if not have_tool(name):
        pytest.fail("required tool %r not found; Stage 1 cannot be verified "
                    "without it" % name)


# ---------------------------------------------------------------------------
# Stage-2 fixtures
# ---------------------------------------------------------------------------

STAGE2_REPORT = os.path.join(ROOT, "reports", "stage2_parameter_backends.json")
OPENRAM_BUILD = os.path.join(ROOT, "build", "openram", "openram_build.json")


def _rtl(name):
    return os.path.join(ROOT, "rtl", name)


@pytest.fixture(scope="session")
def param_images(integer_model):
    from model2rtl.param_image import build_images
    return build_images(integer_model)


@pytest.fixture(scope="session")
def portable_rtl():
    p = _rtl("mnist_mlp_params_portable.v")
    if not os.path.exists(p):
        pytest.skip("run scripts/gen_weight_rom_portable.py first")
    return p


@pytest.fixture(scope="session")
def openram_rtl():
    p = _rtl("mnist_mlp_params_openram.v")
    if not os.path.exists(p):
        pytest.skip("run scripts/gen_weight_rom_openram.py first")
    return p


@pytest.fixture(scope="session")
def top_rtl():
    p = _rtl("mnist_mlp_top.v")
    if not os.path.exists(p):
        pytest.skip("run scripts/gen_weight_rom_openram.py first")
    return p


@pytest.fixture(scope="session")
def equivalence_run(param_images, portable_rtl, openram_rtl, tmp_path_factory):
    from model2rtl import stage2_sim as S2
    require_tool("iverilog")
    d = tmp_path_factory.mktemp("stage2_equiv")
    return S2.run_param_equivalence(ROOT, str(d), param_images)


@pytest.fixture(scope="session")
def stage2_report():
    import json
    if not os.path.exists(STAGE2_REPORT):
        pytest.skip("reports/stage2_parameter_backends.json missing")
    with open(STAGE2_REPORT) as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def openram_build():
    import json
    if not os.path.exists(OPENRAM_BUILD):
        pytest.skip("build/openram/openram_build.json missing")
    with open(OPENRAM_BUILD) as fh:
        return json.load(fh)


STAGE3_REPORT = os.path.join(ROOT, "reports", "stage3_behavioral_verification.json")


@pytest.fixture(scope="session")
def stage3_report():
    import json
    if not os.path.exists(STAGE3_REPORT):
        pytest.skip("reports/stage3_behavioral_verification.json missing")
    with open(STAGE3_REPORT) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Stage-4 fixtures
# ---------------------------------------------------------------------------

STAGE4_REPORT = os.path.join(ROOT, "reports",
                             "stage4_dual_target_portability.json")
STAGE4_SYNTH = os.path.join(ROOT, "build", "stage4", "stage4_synth.json")


@pytest.fixture(scope="session")
def stage4_report():
    import json
    if not os.path.exists(STAGE4_REPORT):
        pytest.fail("reports/stage4_dual_target_portability.json missing: run "
                    "scripts/synth_stage4.py then scripts/verify_stage4.py. "
                    "Stage-4 verification must never be silently skipped.")
    with open(STAGE4_REPORT) as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def stage4_synth(stage4_report):
    import json
    if not os.path.exists(STAGE4_SYNTH):
        pytest.fail("build/stage4/stage4_synth.json missing: run "
                    "scripts/synth_stage4.py")
    with open(STAGE4_SYNTH) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Stage-5 fixtures
# ---------------------------------------------------------------------------

STAGE5_REPORT = os.path.join(ROOT, "reports", "stage5_openrom_physical.json")
STAGE5_BUILD = os.path.join(ROOT, "build", "stage5",
                            "stage5_openrom_build.json")
STAGE5_SWEEP = os.path.join(ROOT, "build", "stage5", "stage5_sweep.json")
STAGE5_DRCLVS = os.path.join(ROOT, "build", "stage5", "stage5_drclvs.json")


def _load_or_fail(path, hint):
    import json
    if not os.path.exists(path):
        pytest.fail("%s missing: %s. Stage-5 physical verification must never "
                    "be silently skipped." % (os.path.relpath(path, ROOT), hint))
    with open(path) as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def stage5_report():
    return _load_or_fail(STAGE5_REPORT, "run scripts/verify_stage5.py")


@pytest.fixture(scope="session")
def stage5_build():
    return _load_or_fail(STAGE5_BUILD, "run scripts/gen_openrom_stage5.py")


@pytest.fixture(scope="session")
def stage5_sweep():
    return _load_or_fail(STAGE5_SWEEP, "run scripts/sweep_stage5.py")


@pytest.fixture(scope="session")
def stage5_drclvs():
    return _load_or_fail(STAGE5_DRCLVS,
                         "run scripts/verify_physical_stage5.py")


@pytest.fixture(scope="session")
def physical_images(param_images):
    from model2rtl import phys_image as P
    return P.build_physical_images(param_images)
