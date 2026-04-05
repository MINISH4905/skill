"""Compatibility shim — delegates to evaluation_core."""

from evaluation_core.utils.scoring import (  # noqa: F401
    apply_difficulty_weight,
    calculate_time_score,
    combine_scores,
    confidence_from_signals,
    normalize_percent,
)
