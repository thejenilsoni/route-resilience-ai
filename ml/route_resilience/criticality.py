from __future__ import annotations

import math
from statistics import mean
from typing import Iterable

import networkx as nx

from .types import CityNetwork, EdgeCriticality, RoadEdge


def build_graph(city: CityNetwork, excluded_edges: Iterable[str] = ()) -> nx.Graph:
    excluded = set(excluded_edges)
    graph = nx.Graph(name=city.name)
    for node in city.nodes:
        graph.add_node(
            node.id,
            x=node.x,
            y=node.y,
            population=node.population,
            facility=node.facility,
        )
    for edge in city.edges:
        if edge.id in excluded:
            continue
        graph.add_edge(
            edge.source,
            edge.target,
            id=edge.id,
            weight=edge.travel_minutes,
            length_km=edge.length_km,
            flow=edge.baseline_flow,
            lanes=edge.lanes,
            road_class=edge.road_class,
            flood_risk=edge.flood_risk,
            occluded_fraction=edge.occluded_fraction,
        )
    return graph


def _minmax(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lower, upper = min(values.values()), max(values.values())
    span = upper - lower
    if span < 1e-9:
        return {key: 0.0 for key in values}
    return {key: (value - lower) / span for key, value in values.items()}


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _baseline_pairs(graph: nx.Graph) -> dict[tuple[str, str], float]:
    facilities = [node for node, attrs in graph.nodes(data=True) if attrs.get("facility")]
    populous = sorted(graph.nodes, key=lambda node: graph.nodes[node]["population"], reverse=True)[:8]
    targets = list(dict.fromkeys(facilities + populous))
    pairs: dict[tuple[str, str], float] = {}
    for index, source in enumerate(targets):
        lengths = nx.single_source_dijkstra_path_length(graph, source, weight="weight")
        for target in targets[index + 1 :]:
            if target in lengths:
                pairs[_pair_key(source, target)] = float(lengths[target])
    return pairs


def _disruption_impact(
    graph: nx.Graph,
    edge: RoadEdge,
    baseline_pairs: dict[tuple[str, str], float],
) -> tuple[float, float, float]:
    disrupted = graph.copy()
    disrupted.remove_edge(edge.source, edge.target)
    components = list(nx.connected_components(disrupted))
    largest = max(components, key=len) if components else set()
    total_population = sum(graph.nodes[node]["population"] for node in graph.nodes)
    isolated_population = sum(
        graph.nodes[node]["population"] for node in graph.nodes if node not in largest
    )
    isolation = isolated_population / max(total_population, 1)

    detours: list[float] = []
    unreachable = 0
    for (source, target), baseline in baseline_pairs.items():
        try:
            updated = nx.shortest_path_length(disrupted, source, target, weight="weight")
            detours.append(max(0.0, float(updated) / max(baseline, 1e-6) - 1.0))
        except nx.NetworkXNoPath:
            unreachable += 1
    detour = mean(detours) if detours else 0.0
    reachability_penalty = unreachable / max(len(baseline_pairs), 1)
    return detour, isolation, reachability_penalty


def analyze_network(city: CityNetwork) -> dict[str, object]:
    graph = build_graph(city)
    raw_betweenness = nx.edge_betweenness_centrality(graph, weight="weight", normalized=True)
    bridge_pairs = {_pair_key(a, b) for a, b in nx.bridges(graph)}
    baseline_pairs = _baseline_pairs(graph)
    edge_lookup = {edge.id: edge for edge in city.edges}
    betweenness: dict[str, float] = {}
    detour: dict[str, float] = {}
    isolation: dict[str, float] = {}
    reachability: dict[str, float] = {}

    for (source, target), value in raw_betweenness.items():
        edge_id = graph[source][target]["id"]
        betweenness[edge_id] = float(value)

    for edge in city.edges:
        detour_value, isolation_value, reachability_value = _disruption_impact(
            graph, edge, baseline_pairs
        )
        detour[edge.id] = detour_value
        isolation[edge.id] = isolation_value
        reachability[edge.id] = reachability_value

    bet_norm, detour_norm = _minmax(betweenness), _minmax(detour)
    isolation_norm, reach_norm = _minmax(isolation), _minmax(reachability)
    scores: dict[str, float] = {}
    for edge in city.edges:
        bridge = _pair_key(edge.source, edge.target) in bridge_pairs
        flow = min(edge.baseline_flow / 6500.0, 1.0)
        flood = edge.flood_risk
        occlusion_uncertainty = edge.occluded_fraction
        score = (
            0.28 * bet_norm.get(edge.id, 0.0)
            + 0.23 * detour_norm.get(edge.id, 0.0)
            + 0.18 * isolation_norm.get(edge.id, 0.0)
            + 0.10 * reach_norm.get(edge.id, 0.0)
            + 0.08 * flow
            + 0.05 * flood
            + 0.04 * occlusion_uncertainty
            + (0.04 if bridge else 0.0)
        )
        scores[edge.id] = score

    relative_scores = _minmax(scores)
    display_scores = {edge_id: 18.0 + 77.0 * value for edge_id, value in relative_scores.items()}
    ranked = sorted(display_scores, key=display_scores.get, reverse=True)
    criticality: list[EdgeCriticality] = []
    for rank, edge_id in enumerate(ranked, start=1):
        edge = edge_lookup[edge_id]
        bridge = _pair_key(edge.source, edge.target) in bridge_pairs
        redundancy = 0.0
        if not bridge:
            graph_without = graph.copy()
            graph_without.remove_edge(edge.source, edge.target)
            try:
                alternate = nx.shortest_path_length(
                    graph_without, edge.source, edge.target, weight="weight"
                )
                redundancy = 1 / (1 + max(0.0, float(alternate) / edge.travel_minutes - 1))
            except nx.NetworkXNoPath:
                redundancy = 0.0
        criticality.append(
            EdgeCriticality(
                edge_id=edge_id,
                score=round(display_scores[edge_id], 2),
                rank=rank,
                betweenness=round(betweenness.get(edge_id, 0.0), 5),
                detour_impact=round(detour[edge.id] * 100, 2),
                isolation_impact=round(isolation[edge.id] * 100, 2),
                bridge=bridge,
                redundancy=round(redundancy, 3),
            )
        )

    node_connectivity = nx.node_connectivity(graph) if nx.is_connected(graph) else 0
    edge_connectivity = nx.edge_connectivity(graph) if nx.is_connected(graph) else 0
    cycle_edges = len(nx.cycle_basis(graph))
    redundancy_index = min(1.0, cycle_edges / max(len(city.nodes) * 0.45, 1))
    return {
        "edges": criticality,
        "summary": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "bridges": len(bridge_pairs),
            "node_connectivity": node_connectivity,
            "edge_connectivity": edge_connectivity,
            "redundancy_index": round(redundancy_index, 3),
            "network_density": round(nx.density(graph), 4),
            "critical_edge_count": sum(1 for item in criticality if item.score >= 70),
        },
    }


def network_efficiency(graph: nx.Graph) -> float:
    nodes = list(graph.nodes)
    if len(nodes) < 2:
        return 0.0
    inverse_lengths: list[float] = []
    for index, source in enumerate(nodes):
        lengths = nx.single_source_dijkstra_path_length(graph, source, weight="weight")
        for target in nodes[index + 1 :]:
            distance = lengths.get(target)
            inverse_lengths.append(0.0 if distance is None else 1.0 / max(float(distance), 1e-9))
    return sum(inverse_lengths) / max(len(inverse_lengths), 1)


def route_geometry(city: CityNetwork, node_path: list[str]) -> list[tuple[float, float]]:
    lookup = {node.id: node for node in city.nodes}
    return [(lookup[node].x, lookup[node].y) for node in node_path]


def edge_distance_to_point(edge: RoadEdge, x: float, y: float) -> float:
    (x1, y1), (x2, y2) = edge.geometry
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.dist((x, y), (x1, y1))
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    projection = (x1 + t * dx, y1 + t * dy)
    return math.dist((x, y), projection)
