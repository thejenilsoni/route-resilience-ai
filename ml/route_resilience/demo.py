from __future__ import annotations

import math
import random
from dataclasses import replace

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .types import CityNetwork, Occlusion, RoadEdge, RoadNode


def build_demo_city(seed: int = 2026, columns: int = 8, rows: int = 6) -> CityNetwork:
    """Create a deterministic Delhi-inspired road network for complete offline demos."""
    rng = random.Random(seed)
    width, height = 960, 680
    x_gap, y_gap = width / (columns + 1), height / (rows + 1)
    nodes: list[RoadNode] = []

    facilities = {
        (0, 0): "hospital",
        (columns - 1, 0): "fire_station",
        (columns // 2, rows // 2): "command_center",
        (0, rows - 1): "relief_hub",
        (columns - 1, rows - 1): "rail_terminal",
    }

    for row in range(rows):
        for col in range(columns):
            jitter_x = rng.uniform(-14, 14)
            jitter_y = rng.uniform(-12, 12)
            density_wave = 0.55 + 0.45 * math.sin((col + 1) / columns * math.pi)
            population = int(rng.uniform(8_000, 28_000) * density_wave)
            nodes.append(
                RoadNode(
                    id=f"N{row:02d}{col:02d}",
                    x=round((col + 1) * x_gap + jitter_x, 2),
                    y=round((row + 1) * y_gap + jitter_y, 2),
                    population=population,
                    facility=facilities.get((col, row)),
                )
            )

    node_lookup = {node.id: node for node in nodes}
    edges: list[RoadEdge] = []

    def add_edge(source: str, target: str, road_class: str, bridge: bool = False) -> None:
        a, b = node_lookup[source], node_lookup[target]
        pixel_length = math.dist((a.x, a.y), (b.x, b.y))
        length_km = pixel_length / 75.0
        if bridge:
            road_class = "bridge"
        lanes = {"primary": 4, "secondary": 2, "local": 1, "bridge": 2}[road_class]
        speed = {"primary": 55.0, "secondary": 38.0, "local": 25.0, "bridge": 42.0}[road_class]
        flow_factor = {"primary": 2.2, "secondary": 1.35, "local": 0.72, "bridge": 1.65}[road_class]
        edge_id = f"E{len(edges):03d}"
        edges.append(
            RoadEdge(
                id=edge_id,
                source=source,
                target=target,
                geometry=[(a.x, a.y), (b.x, b.y)],
                length_km=round(length_km, 3),
                lanes=lanes,
                speed_kph=speed,
                road_class=road_class,  # type: ignore[arg-type]
                baseline_flow=int(rng.uniform(900, 2_600) * flow_factor),
                flood_risk=round(rng.uniform(0.05, 0.55) + (0.18 if row_near_river(a.y, height) else 0), 3),
            )
        )

    for row in range(rows):
        for col in range(columns):
            current = f"N{row:02d}{col:02d}"
            if col + 1 < columns:
                cls = "primary" if row in {1, 4} else ("secondary" if row == 3 else "local")
                add_edge(current, f"N{row:02d}{col + 1:02d}", cls)
            if row + 1 < rows:
                cls = "primary" if col in {2, 5} else ("secondary" if col == 6 else "local")
                bridge = row == 2 and col in {1, 4, 6}
                add_edge(current, f"N{row + 1:02d}{col:02d}", cls, bridge=bridge)

    for col in (0, 3, 5):
        for row in (0, 2, 4):
            if col + 1 < columns and row + 1 < rows:
                add_edge(f"N{row:02d}{col:02d}", f"N{row + 1:02d}{col + 1:02d}", "secondary")

    occlusions = [
        Occlusion("O01", "cloud", 205, 120, 190, 120, 0.96),
        Occlusion("O02", "tree_canopy", 520, 300, 150, 135, 0.88),
        Occlusion("O03", "building_shadow", 710, 455, 165, 105, 0.91),
        Occlusion("O04", "cloud", 345, 500, 135, 95, 0.93),
    ]

    def covered_fraction(edge: RoadEdge) -> float:
        samples = 40
        hit = 0
        (x1, y1), (x2, y2) = edge.geometry
        for index in range(samples + 1):
            t = index / samples
            x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            if any(
                occ.x <= x <= occ.x + occ.width and occ.y <= y <= occ.y + occ.height
                for occ in occlusions
            ):
                hit += 1
        return round(hit / (samples + 1), 3)

    edges = [replace(edge, occluded_fraction=covered_fraction(edge)) for edge in edges]
    return CityNetwork("Delhi Resilience Demonstrator", width, height, nodes, edges, occlusions, seed)


def row_near_river(y: float, height: int) -> bool:
    river_y = height * 0.52
    return abs(y - river_y) < height * 0.12


def render_satellite_scene(
    city: CityNetwork,
    image_width: int = 320,
    image_height: int = 224,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Render RGB satellite-like imagery, ground-truth roads, and occlusion mask."""
    scale_x, scale_y = image_width / city.width, image_height / city.height
    rng = np.random.default_rng(city.seed)
    base = np.zeros((image_height, image_width, 3), dtype=np.float32)
    yy, xx = np.mgrid[0:image_height, 0:image_width]
    texture = rng.normal(0, 8, size=(image_height, image_width))
    base[..., 0] = 79 + 18 * np.sin(xx / 23) + texture
    base[..., 1] = 91 + 22 * np.sin(yy / 29) + texture * 0.65
    base[..., 2] = 76 + 12 * np.cos((xx + yy) / 31) + texture * 0.45
    image = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image)
    truth_image = Image.new("L", (image_width, image_height), 0)
    truth_draw = ImageDraw.Draw(truth_image)

    for edge in city.edges:
        points = [(x * scale_x, y * scale_y) for x, y in edge.geometry]
        road_width = {"primary": 5, "secondary": 4, "local": 3, "bridge": 4}[edge.road_class]
        draw.line(points, fill=(178, 173, 164), width=road_width + 2)
        draw.line(points, fill=(116, 116, 112), width=road_width)
        truth_draw.line(points, fill=255, width=road_width)

    image = image.filter(ImageFilter.GaussianBlur(radius=0.6))
    observed = np.asarray(image).copy()
    truth = np.asarray(truth_image) > 0
    occlusion = np.zeros((image_height, image_width), dtype=bool)

    for occ in city.occlusions:
        x1, y1 = int(occ.x * scale_x), int(occ.y * scale_y)
        x2, y2 = int((occ.x + occ.width) * scale_x), int((occ.y + occ.height) * scale_y)
        x1, x2 = max(0, x1), min(image_width, x2)
        y1, y2 = max(0, y1), min(image_height, y2)
        occlusion[y1:y2, x1:x2] = True
        if occ.kind == "cloud":
            cloud = rng.normal(220, 9, size=(y2 - y1, x2 - x1, 3))
            observed[y1:y2, x1:x2] = np.clip(cloud, 0, 255)
        elif occ.kind == "tree_canopy":
            canopy = np.zeros((y2 - y1, x2 - x1, 3), dtype=np.float32)
            canopy[..., 0] = rng.normal(48, 10, canopy.shape[:2])
            canopy[..., 1] = rng.normal(94, 14, canopy.shape[:2])
            canopy[..., 2] = rng.normal(46, 9, canopy.shape[:2])
            observed[y1:y2, x1:x2] = np.clip(canopy, 0, 255)
        else:
            observed[y1:y2, x1:x2] = (observed[y1:y2, x1:x2] * 0.32).astype(np.uint8)

    return observed.astype(np.uint8), truth.astype(bool), occlusion
