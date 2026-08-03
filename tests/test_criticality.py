from route_resilience.criticality import analyze_network, build_graph
from route_resilience.demo import build_demo_city


def test_graph_matches_city_contract():
    city = build_demo_city()
    graph = build_graph(city)
    assert graph.number_of_nodes() == len(city.nodes)
    assert graph.number_of_edges() == len(city.edges)


def test_criticality_is_ranked_and_bounded():
    city = build_demo_city()
    analysis = analyze_network(city)
    edges = analysis["edges"]
    assert len(edges) == len(city.edges)
    assert edges[0].rank == 1
    assert all(0 <= edge.score <= 100 for edge in edges)
    assert edges[0].score >= edges[-1].score
    assert analysis["summary"]["redundancy_index"] >= 0
