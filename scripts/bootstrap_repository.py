from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

PAYLOAD_GLOB = "scripts/bootstrap_payload_*.txt"
STAGES = [('Initialize RouteShield workspace', ['.gitignore', '.env.example', 'LICENSE', 'package.json', 'pyproject.toml', 'Makefile', 'apps/web/package.json', 'apps/web/tsconfig.json', 'apps/web/next-env.d.ts', 'apps/web/next.config.mjs', 'apps/web/eslint.config.mjs', 'services/__init__.py', 'services/api/__init__.py', 'services/api/app/__init__.py', 'ml/route_resilience/__init__.py']), ('Add deterministic city network and satellite scene generator', ['ml/route_resilience/types.py', 'ml/route_resilience/demo.py', 'scripts/generate_demo_data.py', 'data/samples/README.md']), ('Implement occlusion-aware road extraction and training baseline', ['ml/route_resilience/extraction.py', 'ml/route_resilience/training.py', 'scripts/train_baseline.py']), ('Add graph criticality and disruption simulation engine', ['ml/route_resilience/criticality.py', 'ml/route_resilience/scenarios.py']), ('Expose road extraction, routing, and resilience API', ['services/api/app/schemas.py', 'services/api/app/main.py']), ('Add deterministic frontend network engine and application shell', ['apps/web/lib/route-engine.mjs', 'apps/web/app/layout.tsx', 'apps/web/app/page.tsx']), ('Build responsive urban mobility command center', ['apps/web/components/route-command-center.tsx', 'apps/web/app/globals.css']), ('Add extraction, graph, scenario, API, and frontend tests', ['tests/test_demo.py', 'tests/test_extraction.py', 'tests/test_criticality.py', 'tests/test_scenarios.py', 'tests/test_api.py', 'apps/web/tests/route-engine.test.mjs']), ('Add containers and continuous quality workflows', ['services/api/Dockerfile', 'apps/web/Dockerfile', 'docker-compose.yml', '.github/workflows/ci.yml']), ('Complete competition-ready technical documentation', ['README.md', 'docs/architecture.md', 'docs/methodology.md', 'docs/data.md', 'docs/api.md', 'docs/model-card.md'])]


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> None:
    repo = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="route-resilience-") as temp_dir:
        temp = Path(temp_dir)
        payload = "".join(path.read_text(encoding="utf-8").strip() for path in sorted(repo.glob(PAYLOAD_GLOB)))
        archive = base64.b64decode(payload)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            bundle.extractall(temp)

        run("git", "config", "user.name", "thejenilsoni")
        run("git", "config", "user.email", "work.jenilsoni@gmail.com")
        run("git", "checkout", "--orphan", "route-resilience-build")
        run("git", "rm", "-rf", ".")

        for message, paths in STAGES:
            for relative in paths:
                source = temp / relative
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            run("git", "add", "--", *paths)
            run("git", "commit", "-m", message)

        run("git", "push", "--force", "origin", "route-resilience-build:main")


if __name__ == "__main__":
    main()
