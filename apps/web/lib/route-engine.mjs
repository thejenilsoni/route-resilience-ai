const seeded = (seed = 2026) => {
  let value = seed >>> 0;
  return () => {
    value = (1664525 * value + 1013904223) >>> 0;
    return value / 4294967296;
  };
};

const edgeKey = (a, b) => [a, b].sort().join("::");

export function buildDemoNetwork(seed = 2026) {
  const random = seeded(seed);
  const width = 960;
  const height = 680;
  const columns = 8;
  const rows = 6;
  const nodes = [];
  const facilities = new Map([
    ["0,0", "Hospital"],
    ["7,0", "Fire Station"],
    ["4,3", "Command Centre"],
    ["0,5", "Relief Hub"],
    ["7,5", "Rail Terminal"],
  ]);

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const id = `N${String(row).padStart(2, "0")}${String(column).padStart(2, "0")}`;
      const x = ((column + 1) * width) / (columns + 1) + (random() - 0.5) * 28;
      const y = ((row + 1) * height) / (rows + 1) + (random() - 0.5) * 24;
      const wave = 0.55 + 0.45 * Math.sin(((column + 1) / columns) * Math.PI);
      nodes.push({
        id,
        x,
        y,
        population: Math.round((8000 + random() * 20000) * wave),
        facility: facilities.get(`${column},${row}`) ?? null,
      });
    }
  }

  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  const edges = [];
  const addEdge = (source, target, roadClass, bridge = false) => {
    const a = nodeMap.get(source);
    const b = nodeMap.get(target);
    const lengthKm = Math.hypot(a.x - b.x, a.y - b.y) / 75;
    const selectedClass = bridge ? "bridge" : roadClass;
    const speed = { primary: 55, secondary: 38, local: 25, bridge: 42 }[selectedClass];
    const flowFactor = { primary: 2.2, secondary: 1.35, local: 0.72, bridge: 1.65 }[selectedClass];
    edges.push({
      id: `E${String(edges.length).padStart(3, "0")}`,
      source,
      target,
      roadClass: selectedClass,
      lengthKm,
      travelMinutes: (lengthKm / speed) * 60,
      baselineFlow: Math.round((900 + random() * 1700) * flowFactor),
      floodRisk: Math.min(0.95, 0.05 + random() * 0.5 + (Math.abs(a.y - height * 0.52) < height * 0.12 ? 0.18 : 0)),
    });
  };

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const current = `N${String(row).padStart(2, "0")}${String(column).padStart(2, "0")}`;
      if (column + 1 < columns) {
        const roadClass = [1, 4].includes(row) ? "primary" : row === 3 ? "secondary" : "local";
        addEdge(current, `N${String(row).padStart(2, "0")}${String(column + 1).padStart(2, "0")}`, roadClass);
      }
      if (row + 1 < rows) {
        const roadClass = [2, 5].includes(column) ? "primary" : column === 6 ? "secondary" : "local";
        addEdge(current, `N${String(row + 1).padStart(2, "0")}${String(column).padStart(2, "0")}`, roadClass, row === 2 && [1, 4, 6].includes(column));
      }
    }
  }

  [0, 3, 5].forEach((column) => {
    [0, 2, 4].forEach((row) => {
      if (column + 1 < columns && row + 1 < rows) {
        addEdge(
          `N${String(row).padStart(2, "0")}${String(column).padStart(2, "0")}`,
          `N${String(row + 1).padStart(2, "0")}${String(column + 1).padStart(2, "0")}`,
          "secondary",
        );
      }
    });
  });

  const occlusions = [
    { id: "O01", type: "Cloud", x: 205, y: 120, width: 190, height: 120, confidence: 0.96 },
    { id: "O02", type: "Canopy", x: 520, y: 300, width: 150, height: 135, confidence: 0.88 },
    { id: "O03", type: "Shadow", x: 710, y: 455, width: 165, height: 105, confidence: 0.91 },
    { id: "O04", type: "Cloud", x: 345, y: 500, width: 135, height: 95, confidence: 0.93 },
  ];

  for (const edge of edges) {
    const a = nodeMap.get(edge.source);
    const b = nodeMap.get(edge.target);
    let hits = 0;
    const samples = 40;
    for (let index = 0; index <= samples; index += 1) {
      const t = index / samples;
      const x = a.x + (b.x - a.x) * t;
      const y = a.y + (b.y - a.y) * t;
      if (occlusions.some((item) => x >= item.x && x <= item.x + item.width && y >= item.y && y <= item.y + item.height)) hits += 1;
    }
    edge.occludedFraction = hits / (samples + 1);
    edge.recovered = edge.occludedFraction > 0.08;
  }

  return { name: "Delhi Resilience Demonstrator", width, height, nodes, edges, occlusions };
}

function adjacency(network, excluded = new Set()) {
  const graph = new Map(network.nodes.map((node) => [node.id, []]));
  for (const edge of network.edges) {
    if (excluded.has(edge.id)) continue;
    graph.get(edge.source).push({ node: edge.target, edge, weight: edge.travelMinutes });
    graph.get(edge.target).push({ node: edge.source, edge, weight: edge.travelMinutes });
  }
  return graph;
}

export function shortestPath(network, source, target, excluded = []) {
  const blocked = new Set(excluded);
  const graph = adjacency(network, blocked);
  const distance = new Map(network.nodes.map((node) => [node.id, Number.POSITIVE_INFINITY]));
  const previous = new Map();
  const previousEdge = new Map();
  const pending = new Set(network.nodes.map((node) => node.id));
  distance.set(source, 0);
  while (pending.size) {
    let current = null;
    let best = Number.POSITIVE_INFINITY;
    for (const node of pending) {
      const value = distance.get(node);
      if (value < best) {
        best = value;
        current = node;
      }
    }
    if (current === null || best === Number.POSITIVE_INFINITY) break;
    pending.delete(current);
    if (current === target) break;
    for (const next of graph.get(current) ?? []) {
      const candidate = best + next.weight;
      if (candidate < distance.get(next.node)) {
        distance.set(next.node, candidate);
        previous.set(next.node, current);
        previousEdge.set(next.node, next.edge.id);
      }
    }
  }
  if (!Number.isFinite(distance.get(target))) return null;
  const nodes = [target];
  const edges = [];
  let cursor = target;
  while (cursor !== source) {
    edges.unshift(previousEdge.get(cursor));
    cursor = previous.get(cursor);
    nodes.unshift(cursor);
  }
  return { nodes, edges, minutes: distance.get(target) };
}

function components(network, excluded = []) {
  const graph = adjacency(network, new Set(excluded));
  const seen = new Set();
  const groups = [];
  for (const node of network.nodes) {
    if (seen.has(node.id)) continue;
    const group = [];
    const stack = [node.id];
    seen.add(node.id);
    while (stack.length) {
      const current = stack.pop();
      group.push(current);
      for (const next of graph.get(current) ?? []) {
        if (!seen.has(next.node)) {
          seen.add(next.node);
          stack.push(next.node);
        }
      }
    }
    groups.push(group);
  }
  return groups.sort((a, b) => b.length - a.length);
}

export function analyseCriticality(network) {
  const nodeMap = new Map(network.nodes.map((node) => [node.id, node]));
  const facilities = network.nodes.filter((node) => node.facility).map((node) => node.id);
  const populous = [...network.nodes].sort((a, b) => b.population - a.population).slice(0, 7).map((node) => node.id);
  const targets = [...new Set([...facilities, ...populous])];
  const baselinePairs = [];
  for (let i = 0; i < targets.length; i += 1) {
    for (let j = i + 1; j < targets.length; j += 1) {
      const route = shortestPath(network, targets[i], targets[j]);
      if (route) baselinePairs.push({ source: targets[i], target: targets[j], route });
    }
  }
  const pathCounts = new Map(network.edges.map((edge) => [edge.id, 0]));
  baselinePairs.forEach(({ route }) => route.edges.forEach((edgeId) => pathCounts.set(edgeId, pathCounts.get(edgeId) + 1)));
  const maxPathCount = Math.max(...pathCounts.values(), 1);

  const results = network.edges.map((edge) => {
    const excluded = [edge.id];
    const groups = components(network, excluded);
    const largest = new Set(groups[0] ?? []);
    const totalPopulation = network.nodes.reduce((sum, node) => sum + node.population, 0);
    const isolatedPopulation = network.nodes.filter((node) => !largest.has(node.id)).reduce((sum, node) => sum + node.population, 0);
    let detourSum = 0;
    let unreachable = 0;
    baselinePairs.forEach(({ source, target, route }) => {
      const alternate = shortestPath(network, source, target, excluded);
      if (!alternate) unreachable += 1;
      else detourSum += Math.max(0, alternate.minutes / route.minutes - 1);
    });
    const detour = detourSum / Math.max(baselinePairs.length - unreachable, 1);
    const bridge = groups.length > 1;
    const betweenness = pathCounts.get(edge.id) / maxPathCount;
    const isolation = isolatedPopulation / Math.max(totalPopulation, 1);
    const score = Math.min(100, 100 * (
      0.34 * betweenness +
      0.24 * Math.min(detour, 1) +
      0.18 * isolation +
      0.08 * (unreachable / Math.max(baselinePairs.length, 1)) +
      0.07 * Math.min(edge.baselineFlow / 6500, 1) +
      0.04 * edge.floodRisk +
      0.03 * edge.occludedFraction +
      (bridge ? 0.08 : 0)
    ));
    const direct = shortestPath(network, edge.source, edge.target, excluded);
    const redundancy = direct ? 1 / (1 + Math.max(0, direct.minutes / edge.travelMinutes - 1)) : 0;
    return { ...edge, score, bridge, betweenness, detourPct: detour * 100, isolationPct: isolation * 100, redundancy };
  });
  const rawMin = Math.min(...results.map((edge) => edge.score));
  const rawMax = Math.max(...results.map((edge) => edge.score));
  const rawSpan = Math.max(rawMax - rawMin, 1e-9);
  results.forEach((edge) => { edge.score = 18 + 77 * ((edge.score - rawMin) / rawSpan); });
  results.sort((a, b) => b.score - a.score);
  results.forEach((edge, index) => { edge.rank = index + 1; });
  const cycles = Math.max(0, network.edges.length - network.nodes.length + components(network).length);
  return {
    edges: results,
    summary: {
      nodes: network.nodes.length,
      edges: network.edges.length,
      bridges: results.filter((edge) => edge.bridge).length,
      criticalEdges: results.filter((edge) => edge.score >= 70).length,
      redundancyIndex: Math.min(1, cycles / (network.nodes.length * 0.45)),
      recoveredEdges: network.edges.filter((edge) => edge.recovered).length,
      occludedLengthKm: network.edges.reduce((sum, edge) => sum + edge.lengthKm * edge.occludedFraction, 0),
    },
    nodeMap,
  };
}

export function scenarioEdges(network, analysis, kind, severity = 0.55) {
  const count = Math.max(1, Math.round(network.edges.length * 0.015 + severity * 3));
  if (kind === "bridge_failure") return analysis.edges.filter((edge) => edge.roadClass === "bridge").slice(0, count).map((edge) => edge.id);
  if (kind === "flood_corridor") return [...network.edges].sort((a, b) => b.floodRisk - a.floodRisk).slice(0, count + 1).map((edge) => edge.id);
  if (kind === "critical_link") return analysis.edges.slice(0, count).map((edge) => edge.id);
  const center = { x: network.width * 0.55, y: network.height * 0.47 };
  return [...network.edges]
    .sort((a, b) => {
      const midpoint = (edge) => {
        const p = analysis.nodeMap.get(edge.source);
        const q = analysis.nodeMap.get(edge.target);
        return Math.hypot((p.x + q.x) / 2 - center.x, (p.y + q.y) / 2 - center.y);
      };
      return midpoint(a) - midpoint(b);
    })
    .slice(0, count + 1)
    .map((edge) => edge.id);
}

export function simulateScenario(network, analysis, kind = "critical_link", severity = 0.55) {
  const removedEdges = scenarioEdges(network, analysis, kind, severity);
  const groups = components(network, removedEdges);
  const largest = new Set(groups[0] ?? []);
  const totalPopulation = network.nodes.reduce((sum, node) => sum + node.population, 0);
  const reachablePopulation = network.nodes.filter((node) => largest.has(node.id)).reduce((sum, node) => sum + node.population, 0);
  const facilities = network.nodes.filter((node) => node.facility);
  const origin = facilities[0].id;
  const destination = facilities.at(-1).id;
  const before = shortestPath(network, origin, destination);
  const after = shortestPath(network, origin, destination, removedEdges);
  const routeDetour = before && after ? Math.max(0, after.minutes / before.minutes - 1) * 100 : 100;
  return {
    kind,
    removedEdges,
    connectedComponents: groups.length,
    reachablePopulationPct: (reachablePopulation / totalPopulation) * 100,
    isolatedPopulation: totalPopulation - reachablePopulation,
    meanDetourPct: routeDetour,
    efficiencyLossPct: Math.min(100, routeDetour * 0.68 + (groups.length - 1) * 14),
    baselineRoute: before,
    alternateRoute: after,
  };
}

export function formatCompact(value) {
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
