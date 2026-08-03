from route_resilience.demo import build_demo_city, render_satellite_scene


def test_demo_city_is_deterministic_and_connected_shape():
    first = build_demo_city(2026)
    second = build_demo_city(2026)
    assert first.to_dict() == second.to_dict()
    assert len(first.nodes) == 48
    assert len(first.edges) > 80
    assert any(edge.occluded_fraction > 0 for edge in first.edges)


def test_satellite_scene_has_truth_and_occlusion():
    image, truth, occlusion = render_satellite_scene(build_demo_city())
    assert image.shape == (224, 320, 3)
    assert truth.shape == occlusion.shape == (224, 320)
    assert truth.any()
    assert occlusion.any()
