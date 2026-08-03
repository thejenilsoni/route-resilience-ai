import numpy as np

from route_resilience.demo import build_demo_city, render_satellite_scene
from route_resilience.extraction import (
    connectivity_score,
    extract_roads,
    recover_occluded_gaps,
    segmentation_metrics,
)


def test_extraction_returns_binary_masks_and_metrics():
    image, truth, occlusion = render_satellite_scene(build_demo_city())
    result = extract_roads(image, occlusion)
    assert result.raw_mask.dtype == bool
    assert result.recovered_mask.dtype == bool
    assert result.raw_mask.shape == truth.shape
    metrics = segmentation_metrics(result.recovered_mask, truth)
    assert 0 <= metrics["iou"] <= 1
    assert result.recovered_mask.sum() >= result.raw_mask.sum()


def test_gap_recovery_connects_simple_occluded_line():
    raw = np.zeros((50, 80), dtype=bool)
    raw[25, 5:31] = True
    raw[25, 48:74] = True
    occlusion = np.zeros_like(raw)
    occlusion[18:33, 28:52] = True
    recovered, candidates = recover_occluded_gaps(raw, occlusion, max_gap=30)
    assert candidates
    assert recovered[25, 39]
    assert connectivity_score(recovered) >= connectivity_score(raw)
