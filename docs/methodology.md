# Methodology

## 1. Road extraction

The transparent baseline combines RGB brightness, spectral neutrality, local texture and morphology. Occlusion pixels are excluded from direct classification. A trainable pixel classifier is included as a reproducible benchmark and extension point for a U-Net, SegFormer or topology-aware segmentation model.

Recommended production metrics include pixel precision/recall/F1/IoU, centerline F1, Average Path Length Similarity, connectivity correctness and topology-aware junction accuracy.

## 2. Occlusion-robust gap recovery

The visible road mask is skeletonized. Pixels with exactly one skeleton neighbour are candidate endpoints. For endpoint pairs, the system calculates:

1. Euclidean gap distance;
2. heading agreement at both endpoints;
3. fraction of the proposed link crossing a known occlusion mask;
4. whether endpoints belong to different visible components.

Only high-confidence candidates are connected, and new pixels are restricted to the masked region. Every accepted hypothesis is returned with coordinates, distance, mask coverage, heading alignment and confidence for audit.

## 3. Mobility graph

Road links carry length, speed, travel time, road class, lanes, baseline traffic, flood risk and occlusion fraction. Nodes carry population and critical-facility labels.

## 4. Graph-theoretic criticality

For every link, the system combines:

- weighted edge betweenness;
- mean shortest-path detour after removal;
- population isolated outside the largest component;
- unreachable critical origin-destination pairs;
- baseline flow;
- flood exposure;
- extraction uncertainty;
- bridge status and alternate-route redundancy.

The final 0–100 value is a relative within-scene priority score, not a universal safety classification.

## 5. Resilience simulation

Four deterministic stressors are included: highest-criticality links, flood-prone corridor, bridge outage and spatially clustered construction. Outputs include reachable population, isolated population, connected components, mean detour, efficiency loss and emergency-route alternatives.

## 6. Validation protocol

A field evaluation should use geographically separated train/validation/test areas and temporally held-out imagery. Random neighbouring-pixel splits are not acceptable because they leak spatial context. Road extraction, topology recovery and mobility consequences should be evaluated separately before end-to-end claims are made.
