from route_resilience.demo import build_demo_city
from route_resilience.scenarios import scenario_edges, simulate_disruption


def test_scenario_edges_are_valid():
    city = build_demo_city()
    known = {edge.id for edge in city.edges}
    selected = scenario_edges(city, "flood_corridor", 0.7)
    assert selected
    assert set(selected) <= known


def test_disruption_result_is_consistent():
    city = build_demo_city()
    result = simulate_disruption(city, kind="critical_link", severity=0.8)
    assert result.removed_edges
    assert 0 <= result.reachable_population_pct <= 100
    assert result.isolated_population >= 0
    assert result.connected_components >= 1
    assert result.network_efficiency_loss_pct >= 0
