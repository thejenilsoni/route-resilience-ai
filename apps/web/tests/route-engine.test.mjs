import assert from "node:assert/strict";
import test from "node:test";

import {
  analyseCriticality,
  buildDemoNetwork,
  scenarioEdges,
  shortestPath,
  simulateScenario,
} from "../lib/route-engine.mjs";

test("demo network is deterministic and connected", () => {
  const first = buildDemoNetwork(2026);
  const second = buildDemoNetwork(2026);
  assert.equal(first.nodes.length, 48);
  assert.ok(first.edges.length > 80);
  assert.deepEqual(first.nodes, second.nodes);
  assert.ok(shortestPath(first, "N0000", "N0507"));
});

test("criticality produces a complete ranking", () => {
  const network = buildDemoNetwork();
  const analysis = analyseCriticality(network);
  assert.equal(analysis.edges.length, network.edges.length);
  assert.equal(analysis.edges[0].rank, 1);
  assert.ok(analysis.edges[0].score >= analysis.edges.at(-1).score);
  assert.ok(analysis.summary.recoveredEdges > 0);
});

test("scenario selection returns known links", () => {
  const network = buildDemoNetwork();
  const analysis = analyseCriticality(network);
  const selected = scenarioEdges(network, analysis, "flood_corridor", 0.7);
  const known = new Set(network.edges.map((edge) => edge.id));
  assert.ok(selected.length > 0);
  assert.ok(selected.every((edge) => known.has(edge)));
});

test("disruption simulation reports mobility impacts", () => {
  const network = buildDemoNetwork();
  const analysis = analyseCriticality(network);
  const result = simulateScenario(network, analysis, "critical_link", 0.8);
  assert.ok(result.removedEdges.length >= 1);
  assert.ok(result.reachablePopulationPct >= 0 && result.reachablePopulationPct <= 100);
  assert.ok(result.efficiencyLossPct >= 0);
});
