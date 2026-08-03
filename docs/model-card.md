# Model card

**System:** RouteShield road perception and network-resilience baseline  
**Version:** `0.1.0`  
**Purpose:** road extraction prototyping, occlusion-gap hypothesis generation and relative mobility criticality analysis

## Included models

1. An interpretable spectral/texture heuristic for immediate offline extraction.
2. A histogram-gradient-boosting pixel classifier trained on generated satellite scenes.
3. Deterministic graph algorithms for topology, criticality and routing.

## Synthetic benchmark

The bundled pixel classifier reaches approximately `0.996 precision`, `0.995 recall`, `0.995 F1` and `0.991 IoU` on a held-out split from the same synthetic generator family. These metrics validate code and model plumbing; they are not evidence of generalization to real satellite imagery.

## Intended use

- research and hackathon prototyping;
- relative comparison of links in a consistent network snapshot;
- explainable demonstration of topology recovery and disruption analysis;
- baseline for evaluation against deep segmentation models.

## Out-of-scope use

- autonomous emergency dispatch;
- public claims about current road availability;
- infrastructure investment without authoritative data and field review;
- safety-critical navigation;
- individual mobility or surveillance decisions.

## Production requirements

Observed-data calibration, multi-city and multi-season testing, uncertainty calibration, topology-aware metrics, human review of recovered links, traffic validation, hazard-specific engineering review and post-deployment monitoring are required.
