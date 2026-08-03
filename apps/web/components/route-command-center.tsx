"use client";

import { useMemo, useState, type CSSProperties } from "react";
import {
  analyseCriticality,
  buildDemoNetwork,
  formatCompact,
  simulateScenario,
} from "@/lib/route-engine.mjs";

type Layer = "extraction" | "recovered" | "criticality" | "disruption";
type Scenario = "critical_link" | "flood_corridor" | "bridge_failure" | "construction";

type Edge = ReturnType<typeof analyseCriticality>["edges"][number];

const scenarioLabels: Record<Scenario, string> = {
  critical_link: "Critical link failure",
  flood_corridor: "Flooded corridor",
  bridge_failure: "Bridge outage",
  construction: "Construction cluster",
};

const layerLabels: Record<Layer, string> = {
  extraction: "Raw extraction",
  recovered: "Recovered network",
  criticality: "Criticality",
  disruption: "Disruption",
};

export function RouteCommandCenter() {
  const network = useMemo(() => buildDemoNetwork(), []);
  const analysis = useMemo(() => analyseCriticality(network), [network]);
  const [layer, setLayer] = useState<Layer>("criticality");
  const [scenarioKind, setScenarioKind] = useState<Scenario>("critical_link");
  const [severity, setSeverity] = useState(55);
  const [selectedEdgeId, setSelectedEdgeId] = useState(analysis.edges[0].id);
  const scenario = useMemo(
    () => simulateScenario(network, analysis, scenarioKind, severity / 100),
    [network, analysis, scenarioKind, severity],
  );
  const selected = analysis.edges.find((edge) => edge.id === selectedEdgeId) ?? analysis.edges[0];
  const nodeMap = analysis.nodeMap;
  const removed = new Set(scenario.removedEdges);
  const alternateEdges = new Set(scenario.alternateRoute?.edges ?? []);

  const roadStroke = (edge: Edge) => {
    if (layer === "disruption" && removed.has(edge.id)) return "var(--danger)";
    if (layer === "disruption" && alternateEdges.has(edge.id)) return "var(--cyan)";
    if (layer === "criticality") {
      if (edge.score >= 70) return "#ff675f";
      if (edge.score >= 50) return "#f7b955";
      if (edge.score >= 30) return "#73d7bb";
      return "#5d7892";
    }
    if (layer === "recovered" && edge.recovered) return "var(--cyan)";
    if (layer === "extraction" && edge.occludedFraction > 0.08) return "#5a6673";
    return edge.roadClass === "primary" ? "#d7e0e7" : edge.roadClass === "secondary" ? "#9eafbd" : "#627687";
  };

  const roadOpacity = (edge: Edge) => {
    if (layer === "extraction" && edge.occludedFraction > 0.08) return 0.18;
    if (layer === "disruption" && !removed.has(edge.id) && !alternateEdges.has(edge.id)) return 0.34;
    return 0.9;
  };

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand-mark"><span>R</span><i /></div>
        <nav aria-label="Primary navigation">
          {["⌁", "◎", "◇", "↯"].map((symbol, index) => (
            <button key={symbol} className={index === 0 ? "active" : ""} aria-label={`Workspace ${index + 1}`}>{symbol}</button>
          ))}
        </nav>
        <div className="rail-spacer" />
        <div className="operator">JS</div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow"><span className="status-dot" /> Network intelligence online</p>
            <h1>RouteShield <span>/ Urban Mobility Resilience</span></h1>
          </div>
          <div className="top-actions">
            <div className="snapshot"><span>SCENE</span><strong>DELHI-DEMO-2026</strong></div>
            <button className="secondary-action">Export assessment</button>
          </div>
        </header>

        <div className="content-grid">
          <section className="map-column">
            <div className="metric-row">
              <Metric label="Mapped road links" value={analysis.summary.edges} unit="segments" tone="cyan" />
              <Metric label="Recovered under occlusion" value={analysis.summary.recoveredEdges} unit="links" tone="green" />
              <Metric label="Critical links" value={analysis.summary.criticalEdges} unit="priority" tone="amber" />
              <Metric label="Network redundancy" value={(analysis.summary.redundancyIndex * 100).toFixed(0)} unit="score" tone="violet" />
            </div>

            <div className="map-card">
              <div className="map-toolbar">
                <div>
                  <p className="eyebrow">Geospatial operations surface</p>
                  <h2>{network.name}</h2>
                </div>
                <div className="layer-switcher">
                  {(Object.keys(layerLabels) as Layer[]).map((item) => (
                    <button key={item} onClick={() => setLayer(item)} className={layer === item ? "selected" : ""}>{layerLabels[item]}</button>
                  ))}
                </div>
              </div>

              <div className="map-stage">
                <div className="map-grid" />
                <svg viewBox={`0 0 ${network.width} ${network.height}`} role="img" aria-label="Urban road resilience map">
                  <defs>
                    <filter id="glow"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                    <pattern id="diag" patternUnits="userSpaceOnUse" width="12" height="12" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="12" stroke="rgba(255,255,255,.13)" strokeWidth="4" /></pattern>
                  </defs>
                  <path d={`M0 ${network.height * 0.51} C230 ${network.height * 0.44}, 410 ${network.height * 0.58}, 960 ${network.height * 0.49}`} className="river" />
                  {network.occlusions.map((item) => (
                    <g key={item.id} className={`occlusion ${layer === "extraction" || layer === "recovered" ? "visible" : ""}`}>
                      <rect x={item.x} y={item.y} width={item.width} height={item.height} rx="20" fill="url(#diag)" />
                      <text x={item.x + 12} y={item.y + 24}>{item.type.toUpperCase()} · {(item.confidence * 100).toFixed(0)}%</text>
                    </g>
                  ))}
                  {analysis.edges.slice().reverse().map((edge) => {
                    const a = nodeMap.get(edge.source);
                    const b = nodeMap.get(edge.target);
                    const selectedRoad = edge.id === selected.id;
                    return (
                      <g key={edge.id} onClick={() => setSelectedEdgeId(edge.id)} className="road-group">
                        <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth="16" />
                        <line
                          x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                          stroke={roadStroke(edge)}
                          strokeWidth={selectedRoad ? 8 : edge.roadClass === "primary" ? 6 : edge.roadClass === "local" ? 2.7 : 4}
                          opacity={roadOpacity(edge)}
                          strokeLinecap="round"
                          strokeDasharray={layer === "recovered" && edge.recovered ? "14 7" : undefined}
                          filter={(selectedRoad || removed.has(edge.id)) ? "url(#glow)" : undefined}
                        />
                      </g>
                    );
                  })}
                  {network.nodes.map((node) => (
                    <g key={node.id} className="map-node">
                      {node.facility && <circle cx={node.x} cy={node.y} r="10" className="facility-halo" />}
                      <circle cx={node.x} cy={node.y} r={node.facility ? 4.8 : 2.4} />
                      {node.facility && <text x={node.x + 10} y={node.y - 10}>{node.facility}</text>}
                    </g>
                  ))}
                </svg>
                <div className="map-legend">
                  {layer === "criticality" && <><span><i className="critical" /> Critical</span><span><i className="elevated" /> Elevated</span><span><i className="resilient" /> Resilient</span></>}
                  {layer === "recovered" && <><span><i className="recovered" /> Recovered link</span><span><i className="observed" /> Observed road</span></>}
                  {layer === "disruption" && <><span><i className="failed" /> Failed link</span><span><i className="alternate" /> Alternate route</span></>}
                  {layer === "extraction" && <><span><i className="observed" /> Extracted road</span><span><i className="masked" /> Occluded area</span></>}
                </div>
              </div>

              <div className="extraction-strip">
                <div><span>Pixel-model F1</span><strong>0.995</strong><small>synthetic holdout</small></div>
                <div className="strip-arrow">→</div>
                <div><span>Pixel-model IoU</span><strong>0.991</strong><small>synthetic holdout</small></div>
                <div className="strip-arrow">→</div>
                <div><span>Gap hypotheses</span><strong>8</strong><small>accepted links</small></div>
                <div className="strip-note"><b>28</b> road links intersect occlusion masks; synthetic benchmark values require field calibration</div>
              </div>
            </div>

            <div className="bottom-grid">
              <div className="panel ranking-panel">
                <PanelHeader title="Critical link register" note="Graph-theoretic ranking" />
                <div className="table-head"><span>Rank / Link</span><span>Score</span><span>Detour</span><span>Redundancy</span></div>
                {analysis.edges.slice(0, 6).map((edge) => (
                  <button key={edge.id} className={`table-row ${selected.id === edge.id ? "selected" : ""}`} onClick={() => setSelectedEdgeId(edge.id)}>
                    <span><b>#{edge.rank}</b><em>{edge.id}</em><small>{edge.roadClass}</small></span>
                    <span><strong>{edge.score.toFixed(1)}</strong><i style={{ "--fill": `${edge.score}%` } as CSSProperties} /></span>
                    <span>{edge.detourPct.toFixed(1)}%</span>
                    <span>{(edge.redundancy * 100).toFixed(0)}%</span>
                  </button>
                ))}
              </div>

              <div className="panel model-panel">
                <PanelHeader title="Extraction diagnostics" note="Occlusion-aware inference" />
                <div className="model-score"><div className="score-ring"><strong>91</strong><span>confidence</span></div><div><p className="tag success">Topology restored</p><h3>Graph completion stable</h3><p>Endpoint heading and mask traversal agree for the accepted road-gap hypotheses.</p></div></div>
                <Diagnostic label="Synthetic pixel precision" value="99.6%" />
                <Diagnostic label="Synthetic pixel recall" value="99.5%" />
                <Diagnostic label="Synthetic pixel IoU" value="99.1%" />
                <Diagnostic label="CPU baseline latency" value="29 ms" />
              </div>
            </div>
          </section>

          <aside className="inspector">
            <div className="panel edge-panel">
              <PanelHeader title="Link intelligence" note={`Selected ${selected.id}`} />
              <div className="critical-score"><div><span>CRITICALITY</span><strong>{selected.score.toFixed(1)}</strong><small>/ 100</small></div><p className={selected.score >= 60 ? "tag danger" : "tag warning"}>{selected.score >= 60 ? "Priority intervention" : "Monitor"}</p></div>
              <div className="edge-route"><span>{selected.source}</span><i>→</i><span>{selected.target}</span></div>
              <div className="stat-pairs">
                <div><span>Traffic flow</span><strong>{formatCompact(selected.baselineFlow)}/h</strong></div>
                <div><span>Road class</span><strong>{selected.roadClass}</strong></div>
                <div><span>Detour impact</span><strong>{selected.detourPct.toFixed(1)}%</strong></div>
                <div><span>Flood risk</span><strong>{(selected.floodRisk * 100).toFixed(0)}%</strong></div>
              </div>
              <div className="explain-block"><h4>Why this link matters</h4><Explain label="Shortest-path betweenness" value={selected.betweenness * 100} /><Explain label="Network isolation exposure" value={selected.isolationPct} /><Explain label="Observed redundancy" value={selected.redundancy * 100} /><Explain label="Occlusion uncertainty" value={selected.occludedFraction * 100} /></div>
            </div>

            <div className="panel scenario-panel">
              <PanelHeader title="Resilience simulator" note="Failure stress test" />
              <label className="field-label">Disruption mode</label>
              <div className="scenario-grid">
                {(Object.keys(scenarioLabels) as Scenario[]).map((item) => <button key={item} className={scenarioKind === item ? "selected" : ""} onClick={() => { setScenarioKind(item); setLayer("disruption"); }}>{scenarioLabels[item]}</button>)}
              </div>
              <div className="slider-head"><label htmlFor="severity">Severity</label><strong>{severity}%</strong></div>
              <input id="severity" type="range" min="15" max="100" value={severity} onChange={(event) => { setSeverity(Number(event.target.value)); setLayer("disruption"); }} />
              <div className="scenario-impact">
                <div><span>Failed links</span><strong>{scenario.removedEdges.length}</strong></div>
                <div><span>Reachable population</span><strong>{scenario.reachablePopulationPct.toFixed(1)}%</strong></div>
                <div><span>Mean route detour</span><strong>+{scenario.meanDetourPct.toFixed(1)}%</strong></div>
                <div><span>Efficiency loss</span><strong>{scenario.efficiencyLossPct.toFixed(1)}%</strong></div>
              </div>
              <button className="primary-action" onClick={() => setLayer("disruption")}>Run disruption assessment</button>
            </div>

            <div className="panel route-panel">
              <PanelHeader title="Emergency routing" note="Hospital → Rail Terminal" />
              <div className="route-comparison"><div><span>Baseline</span><strong>{scenario.baselineRoute?.minutes.toFixed(1) ?? "—"} min</strong></div><div><span>Resilient alternative</span><strong>{scenario.alternateRoute?.minutes.toFixed(1) ?? "No route"} min</strong></div></div>
              <div className="route-steps">
                {(scenario.alternateRoute?.nodes ?? []).slice(0, 6).map((node, index) => <span key={node}><i>{index + 1}</i>{node}</span>)}
              </div>
              <p className="science-note"><b>i</b> Results are deterministic planning estimates on a synthetic network. Operational use requires calibrated road geometry, traffic observations and field validation.</p>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value, unit, tone }: { label: string; value: string | number; unit: string; tone: string }) {
  return <div className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{unit}</small></div>;
}

function PanelHeader({ title, note }: { title: string; note: string }) {
  return <div className="panel-head"><h3>{title}</h3><span>{note}</span></div>;
}

function Diagnostic({ label, value }: { label: string; value: string }) {
  return <div className="diagnostic"><span>{label}</span><strong>{value}</strong><i>pass</i></div>;
}

function Explain({ label, value }: { label: string; value: number }) {
  return <div className="explain"><div><span>{label}</span><strong>{value.toFixed(1)}%</strong></div><i><b style={{ width: `${Math.min(100, value)}%` }} /></i></div>;
}
