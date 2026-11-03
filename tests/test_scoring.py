import pytest
from orion_ahop.models import AdaptiveIndicators
from orion_ahop.scoring import calculate_score

def test_equal_weight_score():
    result = calculate_score(AdaptiveIndicators(1.0, 0.5, 0.0))
    assert result.score == pytest.approx(0.5)
    assert result.level == "MEDIUM"

def test_missing_indicator_renormalizes():
    result = calculate_score(AdaptiveIndicators(1.0, None, 0.0))
    assert result.score == pytest.approx(0.5)
    assert "data_age" not in result.available_indicators

def test_out_of_range_rejected():
    with pytest.raises(ValueError):
        calculate_score(AdaptiveIndicators(1.2, 0.2, 0.3))
