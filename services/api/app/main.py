from __future__ import annotations

from dataclasses import asdict
from typing import Any

import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from route_resilience.criticality import analyze_network, build_graph, route_geometry
from route_resilience.demo import build_demo_city, render_satellite_scene
from route_resilience.extraction import connectivity_score, extract_roads, segmentation_metrics
from route_resilience.scenarios import result_to_dict, simulate_disruption

from .schemas import ExtractionRequest, RouteRequest, ScenarioRequest

app = FastAPI(
    title="Route Resilience API",
    version="0.1.0",
    description="Occlusion-robust road extraction and urban network criticality analysis.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "route-resilience-api"}


@app.get("/v1/city")
def city(seed: int = 2026) -> dict[str, Any]:
    network = build_demo_city(seed)
    analysis = analyze_network(network)
    return {
        "city": network.to_dict(),
        "criticality": {
            "summary": analysis["summary"],
            "edges": [asdict(item) for item in analysis["edges"]],
        },
    }


@app.post("/v1/extraction/analyze")
def extraction(request: ExtractionRequest) -> dict[str, Any]:
    network = build_demo_city(request.seed)
    image, truth, occlusion = render_satellite_scene(network)
    result = extract_roads(image, occlusion, request.threshold)
    raw_metrics = segmentation_metrics(result.raw_mask, truth)
    recovered_metrics = segmentation_metrics(result.recovered_mask, truth)
    return {
        "image_shape": list(image.shape),
        "occluded_pixel_pct": round(float(occlusion.mean()) * 100, 2),
        "raw": {
            "metrics": raw_metrics,
            "connectivity": connectivity_score(result.raw_mask),
            "road_pixel_pct": round(float(result.raw_mask.mean()) * 100, 2),
        },
        "recovered": {
            "metrics": recovered_metrics,
            "connectivity": connectivity_score(result.recovered_mask),
            "road_pixel_pct": round(float(result.recovered_mask.mean()) * 100, 2),
            "accepted_gaps": result.gap_candidates,
        },
    }


@app.post("/v1/scenarios/simulate")
def scenario(request: ScenarioRequest) -> dict[str, Any]:
    network = build_demo_city(request.seed)
    known_edges = {edge.id for edge in network.edges}
    if request.removed_edges:
        unknown = sorted(set(request.removed_edges) - known_edges)
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown edge IDs: {unknown}")
    known_nodes = {node.id for node in network.nodes}
    for value, label in ((request.origin, "origin"), (request.destination, "destination")):
        if value and value not in known_nodes:
            raise HTTPException(status_code=422, detail=f"Unknown {label} node: {value}")
    result = simulate_disruption(
        network,
        removed_edges=request.removed_edges,
        kind=request.kind,
        severity=request.severity,
        origin=request.origin,
        destination=request.destination,
    )
    return result_to_dict(result)


@app.post("/v1/routes/alternatives")
def alternatives(request: RouteRequest) -> dict[str, Any]:
    network = build_demo_city(request.seed)
    known_nodes = {node.id for node in network.nodes}
    if request.origin not in known_nodes or request.destination not in known_nodes:
        raise HTTPException(status_code=422, detail="Origin or destination node is unknown")
    graph = build_graph(network, request.excluded_edges)
    try:
        paths = nx.shortest_simple_paths(graph, request.origin, request.destination, weight="weight")
        alternatives_payload = []
        for index, path in enumerate(paths):
            if index >= request.alternatives:
                break
            alternatives_payload.append(
                {
                    "rank": index + 1,
                    "nodes": path,
                    "geometry": route_geometry(network, path),
                    "minutes": round(float(nx.path_weight(graph, path, weight="weight")), 2),
                }
            )
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        raise HTTPException(status_code=404, detail="No route is available") from exc
    return {"alternatives": alternatives_payload}
