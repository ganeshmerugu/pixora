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


class TemperatureCalibrator:
    """Temperature scaling: calibrated_i = exp(z_i/T) / sum(exp(z_j/T)).

    For single-value confidence: calibrated = sigmoid(logit(raw) / T).
    Fit T on validation set by minimizing negative log-likelihood."""

    def __init__(self, temperature: float = 1.0):
        self.temperature = max(temperature, 0.01)

    def calibrate(self, raw_confidence: float) -> float:
        raw_confidence = max(1e-7, min(1.0 - 1e-7, raw_confidence))
        logit = math.log(raw_confidence / (1.0 - raw_confidence))
        scaled = logit / self.temperature
        scaled = max(-20.0, min(20.0, scaled))
        return round(1.0 / (1.0 + math.exp(-scaled)), 4)

    def calibrate_logits(self, logits: list[float]) -> list[float]:
        scaled = [z / self.temperature for z in logits]
        max_z = max(scaled)
        exps = [math.exp(z - max_z) for z in scaled]
        total = sum(exps)
        return [round(e / total, 6) for e in exps]

    def fit(self, predictions: list[dict]) -> None:
        if len(predictions) < 10:
            return

        best_nll = float("inf")
        best_t = self.temperature

        for t_int in range(1, 200):
            t = t_int * 0.05
            nll = 0.0
            for pred in predictions:
                conf = pred.get("confidence", 0.5)
                correct = 1.0 if pred.get("correct", False) else 0.0
                conf = max(1e-7, min(1.0 - 1e-7, conf))
                logit = math.log(conf / (1.0 - conf))
                scaled = logit / t
                scaled = max(-20.0, min(20.0, scaled))
                p = 1.0 / (1.0 + math.exp(-scaled))
                p = max(1e-7, min(1.0 - 1e-7, p))
                nll -= correct * math.log(p) + (1.0 - correct) * math.log(1.0 - p)
            nll /= len(predictions)
            if nll < best_nll:
                best_nll = nll
                best_t = t

        self.temperature = best_t

    def to_dict(self) -> dict[str, float]:
        return {"temperature": self.temperature}

    @classmethod
    def from_dict(cls, d: dict) -> TemperatureCalibrator:
        return cls(temperature=d.get("temperature", 1.0))


class CombinedCalibrator:
    """Chains Platt scaling followed by temperature scaling."""

    def __init__(
        self,
        platt: PlattCalibrator | None = None,
        temperature: TemperatureCalibrator | None = None,
    ):
        self.platt = platt or PlattCalibrator()
        self.temperature = temperature or TemperatureCalibrator()

    def calibrate(self, raw_confidence: float) -> float:
        platt_out = self.platt.calibrate(raw_confidence)
        return self.temperature.calibrate(platt_out)

    def fit(self, predictions: list[dict]) -> None:
        self.platt.fit(predictions)
        calibrated = []
        for pred in predictions:
            new_conf = self.platt.calibrate(pred.get("confidence", 0.5))
            calibrated.append({**pred, "confidence": new_conf})
        self.temperature.fit(calibrated)

    def to_dict(self) -> dict:
        return {"platt": self.platt.to_dict(), "temperature": self.temperature.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> CombinedCalibrator:
        return cls(
            platt=PlattCalibrator.from_dict(d.get("platt", {})),
            temperature=TemperatureCalibrator.from_dict(d.get("temperature", {})),
        )
