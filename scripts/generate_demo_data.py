from __future__ import annotations

import json
from pathlib import Path

from route_resilience.demo import build_demo_city


def main() -> None:
    output = Path("data/generated/demo_city.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    city = build_demo_city()
    output.write_text(json.dumps(city.to_dict(), indent=2), encoding="utf-8")
    print(f"Wrote {len(city.nodes)} nodes and {len(city.edges)} edges to {output}")


if __name__ == "__main__":
    main()
