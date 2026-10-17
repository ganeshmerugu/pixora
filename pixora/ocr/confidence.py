from __future__ import annotations
import math


class PlattCalibrator:
    """Platt scaling: calibrated = sigmoid(a * raw + b).
    Fit a, b from eval data. Defaults to identity (a=1, b=0)."""

    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a = a
        self.b = b

    def calibrate(self, raw_confidence: float) -> float:
        z = self.a * raw_confidence + self.b
        z = max(-20.0, min(20.0, z))
        return round(1.0 / (1.0 + math.exp(-z)), 4)

    def fit(self, predictions: list[dict]) -> None:
        """Simple grid search for a, b that minimize log loss on eval data."""
        if len(predictions) < 10:
            return

        best_loss = float("inf")
        best_a, best_b = self.a, self.b

        for a_candidate in [x * 0.5 for x in range(-4, 20)]:
            for b_candidate in [x * 0.25 for x in range(-20, 20)]:
                loss = 0.0
                for pred in predictions:
                    conf = pred.get("confidence", 0.5)
                    correct = 1.0 if pred.get("correct", False) else 0.0
                    z = a_candidate * conf + b_candidate
                    z = max(-20.0, min(20.0, z))
                    p = 1.0 / (1.0 + math.exp(-z))
                    p = max(1e-7, min(1.0 - 1e-7, p))
                    loss -= correct * math.log(p) + (1.0 - correct) * math.log(1.0 - p)
                loss /= len(predictions)
                if loss < best_loss:
                    best_loss = loss
                    best_a = a_candidate
                    best_b = b_candidate

        self.a = best_a
        self.b = best_b

    def to_dict(self) -> dict[str, float]:
        return {"a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, d: dict) -> PlattCalibrator:
        return cls(a=d.get("a", 1.0), b=d.get("b", 0.0))
