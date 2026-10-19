import unittest

import numpy as np

from officedisplay.ai.layout_model import predict
from officedisplay.ai.offline_design import CLASSES, features, logits, softmax


class LayoutModelTest(unittest.TestCase):
    def test_feature_width_matches_weights(self):
        vector = features("Agenda mit Diagramm und Zeitstrahl")
        self.assertEqual(len(vector), 8)
        self.assertEqual(len(logits(vector)), len(CLASSES))

    def test_numpy_and_onnx_agree(self):
        samples = [
            "Willkommen zum Titel",
            "Vergleich Kosten versus Nutzen",
            "Zeitstrahl der Roadmap und der Prozessschritte",
            "Zitat: sie sagte den Satz",
            "KPI Umsatz 12 Prozent Diagramm",
            "Punkte der Liste zum Thema",
        ]
        for text in samples:
            numpy_label = CLASSES[int(np.argmax(softmax(logits(features(text)))))]
            label, source = predict(text)
            self.assertEqual(label, numpy_label, text)
            self.assertEqual(source, "onnxruntime", text)

    def test_obvious_classes(self):
        self.assertEqual(predict("Vergleich versus gegenüber")[0], "two_col")
        self.assertEqual(predict("Zitat sagte quote")[0], "quote")
        self.assertEqual(predict("Zeitstrahl Timeline Roadmap Prozess")[0], "timeline")
        self.assertEqual(predict("Diagramm Chart Umsatz 12")[0], "chart")


if __name__ == "__main__":
    unittest.main()
