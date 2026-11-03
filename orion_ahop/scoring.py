"""Adaptive priority score using normalized indicators in [0, 1]."""
from orion_ahop.models import AdaptiveIndicators, AdaptiveDecision

DEFAULT_WEIGHTS = {"uncertainty": 1/3, "data_age": 1/3, "conjunction_relevance": 1/3}

def calculate_score(indicators: AdaptiveIndicators, weights: dict[str, float] | None = None) -> AdaptiveDecision:
    weights = weights or DEFAULT_WEIGHTS
    if set(weights) != set(DEFAULT_WEIGHTS) or any(w < 0 for w in weights.values()):
        raise ValueError("Provide non-negative weights for all three indicators.")
    values = {"uncertainty": indicators.uncertainty, "data_age": indicators.data_age,
              "conjunction_relevance": indicators.conjunction_relevance}
    for name, value in values.items():
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{name} must be normalized to [0, 1].")
    available = [k for k, v in values.items() if v is not None and weights[k] > 0]
    total_weight = sum(weights[k] for k in available)
    if total_weight <= 0:
        raise ValueError("At least one available indicator must have positive weight.")
    score = sum(weights[k] * float(values[k]) for k in available) / total_weight
    if score >= 0.70:
        level, effort = "HIGH", "HIGH_FIDELITY_OR_MORE_SAMPLES"
    elif score >= 0.35:
        level, effort = "MEDIUM", "REFINED_PROPAGATION_OR_MORE_SAMPLES"
    else:
        level, effort = "BASELINE", "BASELINE_PROPAGATION"
    return AdaptiveDecision(score, level, effort, tuple(available))
