import math
from typing import Literal


def normalize_percent(score: float) -> float:
    return float(max(0.0, min(100.0, score)))


def combine_scores(
    exact_ratio: float,
    similarity: float | None,
    *,
    exact_weight: float = 0.85,
) -> float:
    """
    exact_ratio: 0-1 from automated tests
    similarity: optional 0-1 fuzzy signal for text tasks
    """
    sim = similarity if similarity is not None else exact_ratio
    w = max(0.0, min(1.0, exact_weight))
    return normalize_percent(100.0 * (w * exact_ratio + (1.0 - w) * sim))


def calculate_time_score(time_taken: float, expected_time: float) -> float:
    if time_taken <= expected_time:
        return 1.0
    delta = time_taken - expected_time
    decay = math.exp(-0.005 * delta)
    score = 0.5 + (0.5 * decay)
    return float(round(score, 3))


def apply_difficulty_weight(score: float, tier: str) -> float:
    weights = {
        "beginner": 1.0,
        "elementary": 1.05,
        "intermediate": 1.12,
        "advanced": 1.2,
        "expert": 1.28,
    }
    w = weights.get(tier.lower(), 1.0)
    return float(min(100.0, score * w))


def confidence_from_signals(
    test_pass_ratio: float,
    stability: Literal["high", "medium", "low"] = "medium",
) -> float:
    """
    Map pass ratio + stability hint to a 0-1 confidence for downstream UX.
    """
    base = 0.55 + 0.45 * max(0.0, min(1.0, test_pass_ratio))
    adj = {"high": 0.05, "medium": 0.0, "low": -0.08}.get(stability, 0.0)
    return float(max(0.0, min(1.0, base + adj)))
