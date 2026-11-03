from orion_ahop.controller import AdaptiveController
from orion_ahop.models import AdaptiveIndicators, CCSDSMessage

def _valid_omm():
    return CCSDSMessage("OMM", {}, {
        "OBJECT_ID":"2026-001A", "EPOCH":"2026-01-01T00:00:00",
        "MEAN_MOTION":"15", "ECCENTRICITY":"0.001", "INCLINATION":"51",
        "RA_OF_ASC_NODE":"10", "ARG_OF_PERICENTER":"20", "MEAN_ANOMALY":"30",
        "MEAN_ELEMENT_THEORY":"SGP4"
    })

def test_escalates_immediately_and_deescalates_after_dwell():
    controller = AdaptiveController(min_dwell_steps=2)
    engine, high = controller.update(_valid_omm(), AdaptiveIndicators(1, 1, 1), 0)
    assert engine == "SGP4"
    assert high.level == "HIGH"
    _, medium = controller.update(_valid_omm(), AdaptiveIndicators(0, 0, 0), 1)
    assert medium.level == "HIGH"
    _, medium = controller.update(_valid_omm(), AdaptiveIndicators(0, 0, 0), 2)
    assert medium.level == "MEDIUM"
    _, baseline = controller.update(_valid_omm(), AdaptiveIndicators(0, 0, 0), 4)
    assert baseline.level == "BASELINE"
