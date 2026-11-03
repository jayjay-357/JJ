import numpy as np
import pytest

from orion_ahop.collision_risk import (
    ObjectType,
    PairType,
    SpaceObject,
    assess_pair_risk,
    encounter_plane_probability,
    pair_type_for,
    position_covariance_from_state,
)


def covariance(scale=1e-6):
    return ((scale, 0.0, 0.0), (0.0, scale, 0.0), (0.0, 0.0, scale))


def test_all_required_pair_types_are_supported():
    assert pair_type_for(ObjectType.DEBRIS, ObjectType.DEBRIS) == PairType.DEBRIS_DEBRIS
    assert pair_type_for(ObjectType.SATELLITE, ObjectType.DEBRIS) == PairType.SATELLITE_DEBRIS
    assert pair_type_for(ObjectType.ROCKET, ObjectType.DEBRIS) == PairType.ROCKET_DEBRIS


def test_non_debris_pair_is_rejected():
    with pytest.raises(ValueError):
        pair_type_for(ObjectType.SATELLITE, ObjectType.ROCKET)


def test_position_covariance_accepts_3x3_and_6x6():
    c3 = np.eye(3)
    c6 = np.eye(6)
    np.testing.assert_allclose(position_covariance_from_state(c3), c3)
    np.testing.assert_allclose(position_covariance_from_state(c6), c6[:3, :3])


def test_encounter_plane_probability_is_bounded_and_nonzero():
    probability = encounter_plane_probability(
        (0.0001, 0.0, 0.0),
        (7.0, 0.2, 0.1),
        np.diag([1e-8, 1e-8, 1e-8]),
        0.0005,
    )
    assert 0.0 < probability <= 1.0


def test_pair_risk_classifies_rocket_to_debris():
    rocket = SpaceObject("ROCKET-1", ObjectType.ROCKET, 2.0, covariance())
    debris = SpaceObject("DEBRIS-1", ObjectType.DEBRIS, 0.5, covariance())
    result = assess_pair_risk(
        rocket,
        debris,
        0.01,
        (7.5, 0.1, 0.0),
        (0.01, 0.0, 0.0),
    )
    assert result.pair_type is PairType.ROCKET_DEBRIS
    assert result.hard_body_radius_km == pytest.approx(0.0025)
    assert result.collision_probability is not None


def test_pair_risk_without_covariance_is_explicitly_unquantified():
    debris_a = SpaceObject("D1", ObjectType.DEBRIS, 1.0)
    debris_b = SpaceObject("D2", ObjectType.DEBRIS, 1.0)
    result = assess_pair_risk(debris_a, debris_b, 0.01, (7.0, 0.0, 0.0))
    assert result.pair_type is PairType.DEBRIS_DEBRIS
    assert result.collision_probability is None
    assert result.risk_level == "UNQUANTIFIED"
