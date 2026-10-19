from __future__ import annotations

from pathlib import Path

from officedisplay.ai.offline_design import CLASSES, features, logits
from officedisplay.paths import model_path


def predict(text: str) -> tuple[str, str]:
    """Gibt (Klasse, Quelle) zurück. Quelle ist onnxruntime oder numpy."""
    vector = features(text)
    path = model_path()
    if path.is_file():
        try:
            import numpy as np
            import onnxruntime as ort

            session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            array = np.asarray([vector], dtype=np.float32)
            scores = session.run(None, {"input": array})[0][0]
            return CLASSES[int(scores.argmax())], "onnxruntime"
        except Exception:
            pass
    scores = logits(vector)
    return CLASSES[max(range(len(scores)), key=scores.__getitem__)], "numpy"


def inspect_model() -> str:
    path = model_path()
    if not path.is_file():
        return f"Modelldatei fehlt: {path}"
    try:
        import netron

        address = netron.start(str(path), address=("127.0.0.1", 8787), browse=False)
        return (
            f"Netron zeigt das lokale Layout-Modell unter http://{address[0]}:{address[1]}.\n"
            f"Datei: {path}\n"
            "Der Klassifikator rechnet offline (Merkmale aus dem Text, kein Download)."
        )
    except Exception:
        return (
            f"Modell liegt unter {path}. Netron ist nicht installiert. "
            "Installation: pip install netron, danach im Programm erneut „Modell inspizieren“."
        )
