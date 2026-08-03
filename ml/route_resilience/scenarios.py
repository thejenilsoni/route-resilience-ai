from __future__ import annotations

from dataclasses import asdict
from statistics import mean
from typing import Literal

import networkx as nx

from .criticality import analyze_network, build_graph, edge_distance_to_point, network_efficiency, route_geometry
from .types import CityNetwork, DisruptionResult

ScenarioKind = Literal["flood_corridor", "bridge_failure", "construction", "critical_link"]


def scenario_edges(city: CityNetwork, kind: ScenarioKind, severity: float = 0.55) -> list[str]:
    severity = max(0.05, min(1.0, severity))
    count = max(1, round(len(city.edges) * 0.015 + severity * 3))
    if kind == "bridge_failure":
        bridges = [edge for edge in city.edges if edge.road_class == "bridge"]
        return [edge.id for edge in sorted(bridges, key=lambda item: item.baseline_flow, reverse=True)[:count]]
    if kind == "flood_corridor":
        return [
            edge.id
            for edge in sorted(city.edges, key=lambda item: item.flood_risk, reverse=True)[: count + 1]
        ]
    if kind == "critical_link":
        analysis = analyze_network(city)
        ranked = analysis["edges"]
        return [item.edge_id for item in ranked[:count]]  # type: ignore[index,union-attr]

    center_x, center_y = city.width * 0.55, city.height * 0.47
    affected = sorted(city.edges, key=lambda edge: edge_distance_to_point(edge, center_x, center_y))
    return [edge.id for edge in affected[: count + 1]]


def _route_alternatives(
    city: CityNetwork,
    disrupted: nx.Graph,
    source: str,
    target: str,
    baseline_graph: nx.Graph,
) -> list[dict[str, object]]:
    alternatives: list[dict[str, object]] = []
    try:
        baseline_time = nx.shortest_path_length(baseline_graph, source, target, weight="weight")
    except nx.NetworkXNoPath:
        baseline_time = 0.0
    try:
        generator = nx.shortest_simple_paths(disrupted, source, target, weight="weight")
        for index, path in enumerate(generator):
            if index >= 3:
                break
            minutes = nx.path_weight(disrupted, path, weight="weight")
            alternatives.append(
                {
                    "rank": index + 1,
                    "nodes": path,
                    "geometry": route_geometry(city, path),
                    "minutes": round(float(minutes), 2),
                    "detour_pct": round(
                        max(0.0, float(minutes) / max(float(baseline_time), 1e-6) - 1) * 100,
                        2,
                    ),
                }
            )
    except nx.NetworkXNoPath:
        return []
    return alternatives


def simulate_disruption(
    city: CityNetwork,
    removed_edges: list[str] | None = None,
    kind: ScenarioKind = "critical_link",
    severity: float = 0.55,
    origin: str | None = None,
    destination: str | None = None,
) -> DisruptionResult:
    removed = removed_edges or scenario_edges(city, kind, severity)
    baseline = build_graph(city)
    disrupted = build_graph(city, removed)
    total_population = sum(node.population for node in city.nodes)
    components = sorted(nx.connected_components(disrupted), key=len, reverse=True)
    largest = components[0] if components else set()
    reachable_population = sum(disrupted.nodes[node]["population"] for node in largest)
    isolated_population = total_population - reachable_population

    facilities = [node.id for node in city.nodes if node.facility]
    sample_nodes = facilities + [node.id for node in sorted(city.nodes, key=lambda n: n.population, reverse=True)[:6]]
    sample_nodes = list(dict.fromkeys(sample_nodes))
    detours: list[float] = []
    for index, source in enumerate(sample_nodes):
        for target in sample_nodes[index + 1 :]:
            try:
                before = nx.shortest_path_length(baseline, source, target, weight="weight")
                after = nx.shortest_path_length(disrupted, source, target, weight="weight")
                detours.append(max(0.0, float(after) / max(float(before), 1e-6) - 1))
            except nx.NetworkXNoPath:
                detours.append(1.0)

    efficiency_before = network_efficiency(baseline)
    efficiency_after = network_efficiency(disrupted)
    source = origin or facilities[0]
    target = destination or facilities[-1]
    alternatives = _route_alternatives(city, disrupted, source, target, baseline)

    analysis = analyze_network(city)
    critical_lookup = {item.edge_id: item for item in analysis["edges"]}  # type: ignore[union-attr]
    edge_lookup = {edge.id: edge for edge in city.edges}
    edge_impacts = []
    for edge_id in removed:
        edge = edge_lookup[edge_id]
        metric = critical_lookup[edge_id]
        edge_impacts.append(
            {
                "edge_id": edge_id,
                "source": edge.source,
                "target": edge.target,
                "criticality": metric.score,
                "baseline_flow": edge.baseline_flow,
                "road_class": edge.road_class,
            }
        )

    return DisruptionResult(
        removed_edges=removed,
        reachable_population_pct=round(reachable_population / max(total_population, 1) * 100, 2),
        isolated_population=isolated_population,
        mean_detour_pct=round(mean(detours) * 100 if detours else 0.0, 2),
        network_efficiency_loss_pct=round(
            max(0.0, 1 - efficiency_after / max(efficiency_before, 1e-9)) * 100,
            2,
        ),
        connected_components=len(components),
        alternate_routes=alternatives,
        edge_impacts=edge_impacts,
    )


def result_to_dict(result: DisruptionResult) -> dict[str, object]:
    return asdict(result)
