from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_recall_fscore_support, jaccard_score

from .demo import build_demo_city, render_satellite_scene


@dataclass(slots=True)
class PixelModelReport:
    precision: float
    recall: float
    f1: float
    iou: float
    samples: int
    positive_rate: float


def pixel_features(image: np.ndarray) -> np.ndarray:
    rgb = image.astype(np.float32) / 255.0
    brightness = rgb.mean(axis=2)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    grad_x = np.abs(brightness - np.roll(brightness, 1, axis=1))
    grad_y = np.abs(brightness - np.roll(brightness, 1, axis=0))
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    features = np.stack(
        [
            rgb[..., 0],
            rgb[..., 1],
            rgb[..., 2],
            brightness,
            saturation,
            grad_x,
            grad_y,
            xx / max(image.shape[1] - 1, 1),
            yy / max(image.shape[0] - 1, 1),
        ],
        axis=-1,
    )
    return features.reshape(-1, features.shape[-1])


def build_training_data(seeds: range = range(2020, 2028)) -> tuple[np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    rng = np.random.default_rng(2026)
    for seed in seeds:
        image, truth, occlusion = render_satellite_scene(build_demo_city(seed), 200, 140)
        x = pixel_features(image)
        y = truth.reshape(-1).astype(np.uint8)
        visible = (~occlusion).reshape(-1)
        candidates = np.flatnonzero(visible)
        positives = candidates[y[candidates] == 1]
        negatives = candidates[y[candidates] == 0]
        positive_take = min(len(positives), 2_800)
        negative_take = min(len(negatives), positive_take * 3)
        selected = np.concatenate(
            [
                rng.choice(positives, positive_take, replace=False),
                rng.choice(negatives, negative_take, replace=False),
            ]
        )
        rng.shuffle(selected)
        features.append(x[selected])
        labels.append(y[selected])
    return np.concatenate(features), np.concatenate(labels)


def train_baseline() -> tuple[HistGradientBoostingClassifier, PixelModelReport]:
    x, y = build_training_data()
    split = int(len(y) * 0.8)
    model = HistGradientBoostingClassifier(
        max_iter=130,
        learning_rate=0.08,
        max_leaf_nodes=25,
        min_samples_leaf=24,
        l2_regularization=0.5,
        random_state=2026,
    )
    model.fit(x[:split], y[:split])
    prediction = model.predict(x[split:])
    precision, recall, f1, _ = precision_recall_fscore_support(
        y[split:], prediction, average="binary", zero_division=0
    )
    report = PixelModelReport(
        precision=round(float(precision), 4),
        recall=round(float(recall), 4),
        f1=round(float(f1), 4),
        iou=round(float(jaccard_score(y[split:], prediction, zero_division=0)), 4),
        samples=len(y),
        positive_rate=round(float(y.mean()), 4),
    )
    return model, report
