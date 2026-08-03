# API reference

The interactive OpenAPI explorer is served at `http://localhost:8000/docs`.

## Endpoints

- `GET /health` — service health.
- `GET /v1/city?seed=2026` — network, criticality ranking and summary.
- `POST /v1/extraction/analyze` — road extraction and gap-recovery diagnostics.
- `POST /v1/scenarios/simulate` — disruption impact and emergency-route alternatives.
- `POST /v1/routes/alternatives` — weighted route alternatives after selected link exclusions.

## Scenario request

```json
{
  "kind": "flood_corridor",
  "severity": 0.7,
  "origin": "N0000",
  "destination": "N0507",
  "seed": 2026
}
```

## Route request

```json
{
  "origin": "N0000",
  "destination": "N0507",
  "excluded_edges": ["E014", "E037"],
  "alternatives": 3
}
```
