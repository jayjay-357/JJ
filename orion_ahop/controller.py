"""Compatibility-first adaptive controller with hysteresis and dwell control."""
from dataclasses import dataclass
from orion_ahop.models import AdaptiveIndicators, CCSDSMessage, AdaptiveDecision
from orion_ahop.scoring import calculate_score
from orion_ahop.validation import propagation_path


def decide(message: CCSDSMessage, indicators: AdaptiveIndicators):
    """Stateless compatibility route and adaptive effort recommendation."""
    return propagation_path(message), calculate_score(indicators)


@dataclass
class AdaptiveController:
    """Stateful threshold controller to reduce rapid level switching.

    Thresholds are provisional and should be calibrated on study data.
    The controller only changes computational effort; it cannot change
    the physically compatible propagation engine.
    """
    medium_threshold: float = 0.35
    high_threshold: float = 0.70
    min_dwell_steps: int = 2
    current_level: str = "BASELINE"
    last_switch_step: int = -10**9

    def __post_init__(self):
        if not 0 <= self.medium_threshold < self.high_threshold <= 1:
            raise ValueError("Require 0 <= medium_threshold < high_threshold <= 1.")
        if self.min_dwell_steps < 0:
            raise ValueError("min_dwell_steps must be non-negative.")
        if self.current_level not in {"BASELINE", "MEDIUM", "HIGH"}:
            raise ValueError("Invalid initial controller level.")

    def update(self, message: CCSDSMessage, indicators: AdaptiveIndicators,
               step: int) -> tuple[str, AdaptiveDecision]:
        compatible_engine = propagation_path(message)
        raw = calculate_score(indicators)
        target = ("HIGH" if raw.score >= self.high_threshold else
                  "MEDIUM" if raw.score >= self.medium_threshold else "BASELINE")
        rank = {"BASELINE": 0, "MEDIUM": 1, "HIGH": 2}
        # Escalation is immediate; de-escalation requires hysteresis and dwell.
        if rank[target] > rank[self.current_level]:
            self.current_level = target
            self.last_switch_step = step
        elif rank[target] < rank[self.current_level]:
            if step - self.last_switch_step >= self.min_dwell_steps:
                # One-level de-escalation per update prevents abrupt drops.
                self.current_level = {2: "MEDIUM", 1: "BASELINE"}[rank[self.current_level]]
                self.last_switch_step = step
        effort = {
            "BASELINE": "BASELINE_PROPAGATION",
            "MEDIUM": "REFINED_PROPAGATION_OR_MORE_SAMPLES",
            "HIGH": "HIGH_FIDELITY_OR_MORE_SAMPLES",
        }[self.current_level]
        decision = AdaptiveDecision(raw.score, self.current_level, effort,
                                     raw.available_indicators)
        return compatible_engine, decision
