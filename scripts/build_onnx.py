from __future__ import annotations

"""Kleines Layout-Modell als ONNX, identisch zur NumPy-Referenz in offline_design."""

import sys
from pathlib import Path

import numpy as np
from onnx import TensorProto, helper, numpy_helper, save

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from officedisplay.ai.offline_design import BIAS, WEIGHTS  # noqa: E402


def main() -> None:
    weights = np.asarray(WEIGHTS, dtype=np.float32)
    bias = np.asarray(BIAS, dtype=np.float32)
    graph_input = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 8])
    graph_output = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 6])
    node = helper.make_node("Gemm", ["input", "W", "B"], ["output"], transB=1)
    graph = helper.make_graph(
        [node],
        "layout",
        [graph_input],
        [graph_output],
        [numpy_helper.from_array(weights, name="W"), numpy_helper.from_array(bias, name="B")],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    target = ROOT / "models" / "layout_classifier.onnx"
    target.parent.mkdir(parents=True, exist_ok=True)
    save(model, target)
    print(target)


if __name__ == "__main__":
    main()
