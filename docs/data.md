# Data integration guide

## Required production inputs

| Layer | Typical variables | Required processing |
| --- | --- | --- |
| Optical satellite imagery | RGB/NIR, pan-sharpened imagery | atmospheric correction, orthorectification, cloud/shadow masks |
| Existing road references | centerlines, road class, lanes | coordinate validation, temporal versioning |
| Traffic | speed, flow, congestion | map matching, outlier filtering, time-of-day profiles |
| Urban form | buildings, crossings, barriers, bridges | vector cleanup and graph intersection rules |
| Hazards | flood depth, landslide, construction, closures | scenario time, confidence and spatial overlap |
| Exposure | zonal population, facilities | privacy-preserving aggregation and provenance |

## Canonical road contract

Each `RoadEdge` contains an immutable ID, endpoint IDs, geometry, length, lanes, speed, class, baseline flow, flood risk and occluded fraction. Production adapters may add source and timestamp metadata without changing graph-analysis semantics.

## Demonstration data

The fixed seed `2026` creates 48 nodes, 91 links, five critical facilities and four occlusion regions. Values are synthetic and exist only for reproducibility and software validation.
