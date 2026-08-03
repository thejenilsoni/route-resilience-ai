from __future__ import annotations

import math
from collections import deque
from typing import Iterable

import numpy as np
from skimage.draw import line
from skimage.filters import gaussian, threshold_otsu
from skimage.measure import label
from skimage.morphology import closing, dilation, disk, opening, remove_small_objects, skeletonize

from .types import ExtractionResult


def _normalise(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    span = float(values.max() - values.min())
    if span < 1e-8:
        return np.zeros_like(values)
    return (values - values.min()) / span


def road_probability(image: np.ndarray, occlusion_mask: np.ndarray | None = None) -> np.ndarray:
    """Estimate a road probability surface using spectral and texture cues.

    The lightweight baseline favours low-saturation, mid-brightness, elongated
    surfaces and is intentionally transparent. A trained classifier can replace
    this function without changing downstream graph recovery.
    """
    rgb = image.astype(np.float32) / 255.0
    brightness = rgb.mean(axis=2)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    horizontal = np.abs(brightness - np.roll(brightness, 1, axis=1))
    vertical = np.abs(brightness - np.roll(brightness, 1, axis=0))
    texture = gaussian(horizontal + vertical, sigma=1.2)
    mid_tone = np.exp(-((brightness - 0.46) ** 2) / 0.035)
    spectral_neutrality = 1.0 - np.clip(saturation / 0.35, 0, 1)
    smoothness = 1.0 - _normalise(texture)
    probability = 0.52 * mid_tone + 0.31 * spectral_neutrality + 0.17 * smoothness
    probability = gaussian(probability, sigma=0.75)
    if occlusion_mask is not None:
        probability = probability.copy()
        probability[occlusion_mask] *= 0.15
    return np.clip(probability, 0, 1)


def extract_roads(
    image: np.ndarray,
    occlusion_mask: np.ndarray | None = None,
    threshold: float | None = None,
) -> ExtractionResult:
    probability = road_probability(image, occlusion_mask)
    valid = probability if occlusion_mask is None else probability[~occlusion_mask]
    auto_threshold = float(threshold_otsu(valid)) if valid.size else 0.55
    selected_threshold = threshold if threshold is not None else max(0.78, min(0.86, auto_threshold + 0.08))
    raw = probability >= selected_threshold
    raw = opening(raw, disk(1))
    raw = closing(raw, disk(2))
    raw = remove_small_objects(raw, max_size=17)
    if occlusion_mask is not None:
        raw = raw.copy()
        raw[occlusion_mask] = False
    recovered, candidates = recover_occluded_gaps(raw, occlusion_mask)
    return ExtractionResult(
        raw_mask=raw,
        recovered_mask=recovered,
        confidence=probability,
        gap_candidates=candidates,
    )


def _neighbour_count(skeleton: np.ndarray) -> np.ndarray:
    padded = np.pad(skeleton.astype(np.uint8), 1)
    total = np.zeros_like(skeleton, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            if dx == 1 and dy == 1:
                continue
            total += padded[dy : dy + skeleton.shape[0], dx : dx + skeleton.shape[1]]
    return total


def _endpoint_heading(skeleton: np.ndarray, point: tuple[int, int], radius: int = 8) -> np.ndarray:
    y, x = point
    queue: deque[tuple[int, int, int]] = deque([(y, x, 0)])
    visited = {(y, x)}
    points: list[tuple[float, float]] = []
    while queue:
        cy, cx, depth = queue.popleft()
        points.append((cx, cy))
        if depth >= radius:
            continue
        for ny in range(max(0, cy - 1), min(skeleton.shape[0], cy + 2)):
            for nx in range(max(0, cx - 1), min(skeleton.shape[1], cx + 2)):
                if (ny, nx) not in visited and skeleton[ny, nx]:
                    visited.add((ny, nx))
                    queue.append((ny, nx, depth + 1))
    if len(points) < 2:
        return np.array([0.0, 0.0])
    centroid = np.mean(points[1:], axis=0)
    vector = np.array([x, y], dtype=float) - centroid
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def _line_coverage(mask: np.ndarray, rr: np.ndarray, cc: np.ndarray) -> float:
    if len(rr) == 0:
        return 0.0
    return float(mask[rr, cc].mean())


def recover_occluded_gaps(
    raw_mask: np.ndarray,
    occlusion_mask: np.ndarray | None,
    max_gap: float = 42.0,
    min_occlusion_coverage: float = 0.45,
) -> tuple[np.ndarray, list[dict[str, float | int | str]]]:
    """Reconnect plausible road endpoints across explicit occlusion regions.

    Candidate links are scored using distance, endpoint heading compatibility,
    and the fraction of the connecting line that crosses an occlusion mask.
    """
    if occlusion_mask is None or not np.any(occlusion_mask):
        return raw_mask.copy(), []

    skeleton = skeletonize(raw_mask)
    component_labels = label(raw_mask, connectivity=2)
    neighbours = _neighbour_count(skeleton)
    endpoint_pixels = np.argwhere(skeleton & (neighbours == 1))
    headings = {tuple(point): _endpoint_heading(skeleton, tuple(point)) for point in endpoint_pixels}
    candidates: list[tuple[float, tuple[int, int], tuple[int, int], dict[str, float | int | str]]] = []

    for index, first in enumerate(endpoint_pixels):
        y1, x1 = map(int, first)
        for second in endpoint_pixels[index + 1 :]:
            y2, x2 = map(int, second)
            distance = math.dist((x1, y1), (x2, y2))
            if component_labels[y1, x1] == component_labels[y2, x2]:
                continue
            if distance < 4 or distance > max_gap:
                continue
            rr, cc = line(y1, x1, y2, x2)
            occ_coverage = _line_coverage(occlusion_mask, rr, cc)
            if occ_coverage < min_occlusion_coverage:
                continue
            direction = np.array([x2 - x1, y2 - y1], dtype=float)
            direction /= max(np.linalg.norm(direction), 1e-8)
            first_alignment = float(np.dot(headings[(y1, x1)], direction))
            second_alignment = float(np.dot(headings[(y2, x2)], -direction))
            alignment = max(0.0, (first_alignment + second_alignment) / 2)
            if alignment < 0.35:
                continue
            score = 0.52 * alignment + 0.33 * occ_coverage + 0.15 * (1 - distance / max_gap)
            metadata: dict[str, float | int | str] = {
                "id": f"gap-{len(candidates) + 1:02d}",
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "distance_px": round(distance, 2),
                "occlusion_coverage": round(occ_coverage, 3),
                "heading_alignment": round(alignment, 3),
                "confidence": round(score, 3),
            }
            candidates.append((score, (y1, x1), (y2, x2), metadata))

    candidates.sort(key=lambda item: item[0], reverse=True)
    recovered = raw_mask.copy()
    used: set[tuple[int, int]] = set()
    accepted: list[dict[str, float | int | str]] = []
    for _, first, second, metadata in candidates:
        if first in used or second in used:
            continue
        rr, cc = line(first[0], first[1], second[0], second[1])
        bridge_region = dilation(occlusion_mask, disk(2))
        accepted_pixels = bridge_region[rr, cc]
        recovered[rr[accepted_pixels], cc[accepted_pixels]] = True
        used.update((first, second))
        metadata["status"] = "accepted"
        accepted.append(metadata)

    thickened = dilation(recovered, disk(1))
    recovered = np.where(occlusion_mask, thickened, raw_mask)
    return recovered.astype(bool), accepted


def segmentation_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    prediction = prediction.astype(bool)
    truth = truth.astype(bool)
    tp = int(np.logical_and(prediction, truth).sum())
    fp = int(np.logical_and(prediction, ~truth).sum())
    fn = int(np.logical_and(~prediction, truth).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    iou = tp / max(tp + fp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "iou": round(iou, 4),
    }


def connectivity_score(mask: np.ndarray) -> float:
    """Return the fraction of skeleton pixels belonging to the largest component."""
    skeleton = skeletonize(mask)
    visited = np.zeros_like(skeleton, dtype=bool)
    sizes: list[int] = []
    for y, x in np.argwhere(skeleton):
        if visited[y, x]:
            continue
        stack = [(int(y), int(x))]
        visited[y, x] = True
        size = 0
        while stack:
            cy, cx = stack.pop()
            size += 1
            for ny in range(max(0, cy - 1), min(mask.shape[0], cy + 2)):
                for nx in range(max(0, cx - 1), min(mask.shape[1], cx + 2)):
                    if skeleton[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
        sizes.append(size)
    total = sum(sizes)
    return round(max(sizes, default=0) / max(total, 1), 4)


def mask_to_pixel_graph(mask: np.ndarray) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Compress a road skeleton into graph nodes and edges for diagnostics."""
    skeleton = skeletonize(mask)
    degree = _neighbour_count(skeleton)
    nodes = [tuple(map(int, point)) for point in np.argwhere(skeleton & (degree != 2))]
    node_set = set(nodes)
    visited_links: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    edges: list[tuple[int, int]] = []

    def neighbours(point: tuple[int, int]) -> Iterable[tuple[int, int]]:
        y, x = point
        for ny in range(max(0, y - 1), min(mask.shape[0], y + 2)):
            for nx in range(max(0, x - 1), min(mask.shape[1], x + 2)):
                if (ny, nx) != point and skeleton[ny, nx]:
                    yield (ny, nx)

    node_index = {node: index for index, node in enumerate(nodes)}
    for start in nodes:
        for neighbour in neighbours(start):
            link = tuple(sorted((start, neighbour)))
            if link in visited_links:
                continue
            previous, current = start, neighbour
            visited_links.add(link)
            while current not in node_set:
                next_steps = [point for point in neighbours(current) if point != previous]
                if not next_steps:
                    break
                next_point = next_steps[0]
                visited_links.add(tuple(sorted((current, next_point))))
                previous, current = current, next_point
            if current in node_set and current != start:
                edge = tuple(sorted((node_index[start], node_index[current])))
                if edge not in edges:
                    edges.append(edge)
    return nodes, edges
