from __future__ import annotations

from dataclasses import asdict

from route_resilience.training import train_baseline


if __name__ == "__main__":
    _, report = train_baseline()
    print(asdict(report))
