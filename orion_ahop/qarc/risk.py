"""Classical Monte Carlo reference for a defined collision-event predicate."""
import numpy as np

def monte_carlo_probability(sample_event, sample_count: int, seed: int | None = None):
    if sample_count <= 0:
        raise ValueError("sample_count must be positive.")
    rng = np.random.default_rng(seed)
    hits = sum(bool(sample_event(rng)) for _ in range(sample_count))
    probability = hits / sample_count
    return {"samples": sample_count, "hits": hits, "probability": probability,
            "standard_error": float(np.sqrt(probability * (1-probability) / sample_count))}

def gaussian_disk_event(mean_xy, covariance_xy, hard_body_radius_km: float):
    covariance = np.asarray(covariance_xy, dtype=float)
    if covariance.shape != (2, 2) or hard_body_radius_km <= 0:
        raise ValueError("Expected a 2x2 covariance and positive hard-body radius.")
    def event(rng):
        point = rng.multivariate_normal(np.asarray(mean_xy, dtype=float), covariance)
        return bool(np.linalg.norm(point) <= hard_body_radius_km)
    return event
