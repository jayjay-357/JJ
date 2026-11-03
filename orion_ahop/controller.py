"""Compatibility-first adaptive controller."""
from orion_ahop.models import AdaptiveIndicators, CCSDSMessage
from orion_ahop.scoring import calculate_score
from orion_ahop.validation import propagation_path

def decide(message: CCSDSMessage, indicators: AdaptiveIndicators):
    # Adaptive score allocates effort; it never overrides engine compatibility.
    return propagation_path(message), calculate_score(indicators)
