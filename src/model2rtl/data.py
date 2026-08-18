"""MNIST loading in the exact integer form the contract expects.

Images are used as raw uint8 pixels in [0, 255] with zero-point 0.  There is
no floating-point normalisation anywhere in the inference path: the value the
RTL will see on its activation input bus is literally the stored pixel byte.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import numpy as np

from . import contract as C

#: Dataset split used everywhere in this project.
TRAIN_SPLIT = 55000   # first 55000 of the 60000 MNIST training images
VAL_SPLIT = 5000      # last 5000 of the training images
TEST_SPLIT = 10000    # the full official MNIST test set


def load_mnist_uint8() -> dict:
    """Load MNIST as flat uint8 activation vectors plus int64 labels."""
    from tensorflow.keras.datasets import mnist  # training-time dependency only

    (x_train, y_train), (x_test, y_test) = mnist.load_data()
    x_train = x_train.reshape(-1, C.INPUT_DIM).astype(np.uint8)
    x_test = x_test.reshape(-1, C.INPUT_DIM).astype(np.uint8)
    y_train = y_train.astype(np.int64)
    y_test = y_test.astype(np.int64)

    assert x_train.shape == (60000, C.INPUT_DIM)
    assert x_test.shape == (TEST_SPLIT, C.INPUT_DIM)

    return {
        "x_train": x_train[:TRAIN_SPLIT],
        "y_train": y_train[:TRAIN_SPLIT],
        "x_val": x_train[TRAIN_SPLIT:],
        "y_val": y_train[TRAIN_SPLIT:],
        "x_test": x_test,
        "y_test": y_test,
    }


def array_sha256(*arrays: np.ndarray) -> str:
    h = hashlib.sha256()
    for a in arrays:
        h.update(str(a.shape).encode())
        h.update(str(a.dtype).encode())
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dataset_fingerprint(data: dict) -> dict:
    return {
        "train_images": int(data["x_train"].shape[0]),
        "val_images": int(data["x_val"].shape[0]),
        "test_images": int(data["x_test"].shape[0]),
        "split_rule": "MNIST train[:55000] / train[55000:60000] / official test",
        "x_train_sha256": array_sha256(data["x_train"]),
        "x_test_sha256": array_sha256(data["x_test"]),
        "y_test_sha256": array_sha256(data["y_test"]),
    }


def observed_activation_range(x: np.ndarray) -> Tuple[int, int]:
    return int(x.min()), int(x.max())
