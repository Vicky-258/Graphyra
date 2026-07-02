import React, { useState, useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import { 
  Database, RefreshCw, AlertTriangle, Layers, Search, 
  Map, Activity, Trash2, ArrowRight, Play, Clock, BarChart2,
  CheckCircle2, FileText, Code, Network, History
} from "lucide-react";
import "./App.css";

const API_BASE = "/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("corpus");
  
  // Corpus Status & Sync
  const [dbStats, setDbStats] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [syncLogs, setSyncLogs] = useState([]);
  
  // Ingestion Pipeline Inspector
  const [artifacts, setArtifacts] = useState([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactDetails, setArtifactDetails] = useState(null);
  const [ingestionJsonMode, setIngestionJsonMode] = useState(false);
  
  // Explorer Tab
  const [explorerSearch, setExplorerSearch] = useState("");
  const [explorerArtifact, setExplorerArtifact] = useState(null);
  const [explorerJsonMode, setExplorerJsonMode] = useState(false);
  const [explorerError, setExplorerError] = useState(null);

  // Query Tab
  const [queryText, setQueryText] = useState("Who taught Nahida about Irminsul?");
  const [maxDepth, setMaxDepth] = useState(2);
  const [enableScoring, setEnableScoring] = useState(true);
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryJsonMode, setQueryJsonMode] = useState(false);

  // Graph Tab
  const [graphMode, setGraphMode] = useState("corpus"); // corpus vs query
  const [graphData, setGraphData] = useState(null);
  const [graphJsonMode, setGraphJsonMode] = useState(false);
  const cyRef = useRef(null);
  const graphContainerRef = useRef(null);

  // Diagnostics Tab
  const [queryHistory, setQueryHistory] = useState([]);
  
  // Fetch initial db statistics and artifacts
  useEffect(() => {
    fetchStats();
    fetchArtifacts();
  }, []);

  // Poll background crawl jobs if active
  useEffect(() => {
    if (!activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${activeJobId}`);
        const data = await res.json();
        setJobStatus(data);
        
        if (data.status === "completed" || data.status === "failed") {
          setActiveJobId(null);
          fetchStats();
          fetchArtifacts();
          fetchGraphData(); // refresh graph if complete
          
          const logMsg = data.status === "completed"
            ? `SUCCESS: Ingested ${data.metrics?.artifacts_created} artifacts, ${data.metrics?.chunks_created} chunks, and resolved ${data.metrics?.anchors_resolved} anchors in ${data.metrics?.duration}s.`
            : `FAILED: ${data.error}`;
          setSyncLogs(prev => [logMsg, ...prev]);
        }
      } catch (err) {
        setSyncLogs(prev => [`Error polling job status: ${err.message}`, ...prev]);
        setActiveJobId(null);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJobId]);

  // Load Ingestion Detail when an artifact is selected
  useEffect(() => {
    if (selectedArtifactId) {
      fetchArtifactDetails(selectedArtifactId);
    }
  }, [selectedArtifactId]);

  // Trigger Graph rendering when tab becomes active or graphMode changes
  useEffect(() => {
    if (activeTab === "graph") {
      fetchGraphData();
    }
  }, [activeTab, graphMode, queryResult]);

  // Render Cytoscape Graph on Canvas
  useEffect(() => {
    if (activeTab !== "graph" || !graphData || !graphContainerRef.current) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    cyRef.current = cytoscape({
      container: graphContainerRef.current,
      elements: [
        ...graphData.nodes,
        ...graphData.edges
      ],
      style: [
        {
          selector: 'node[type="artifact"]',
          style: {
            'background-color': '#0ea5e9',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '11px',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '80px',
            'height': '30px',
            'shape': 'round-rectangle',
            'border-width': '2px',
            'border-color': '#0284c7'
          }
        },
        {
          selector: 'node[type="anchor"]',
          style: {
            'background-color': '#8b5cf6',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '11px',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '60px',
            'height': '60px',
            'shape': 'ellipse',
            'border-width': '2px',
            'border-color': '#6d28d9'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '8px',
            'color': '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8
          }
        },
        {
          selector: 'edge[type="links_to"]',
          style: {
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            'line-style': 'dashed'
          }
        },
        {
          selector: 'edge[type="mentions"]',
          style: {
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
            'line-style': 'dotted'
          }
        }
      ],
      layout: {
        name: "cose",
        fit: true,
        padding: 30,
        animate: true,
        refresh: 20
      }
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData, activeTab]);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setDbStats(data);
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  };

  const fetchArtifacts = async () => {
    try {
      const res = await fetch(`${API_BASE}/artifacts`);
      const data = await res.json();
      setArtifacts(data);
      if (data.length > 0 && !selectedArtifactId) {
        setSelectedArtifactId(data[0].id);
      }
    } catch (err) {
      console.error("Error fetching artifacts:", err);
    }
  };

  const fetchArtifactDetails = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/artifact/${encodeURIComponent(id)}`);
      const data = await res.json();
      setArtifactDetails(data);
    } catch (err) {
      console.error("Error fetching artifact details:", err);
    }
  };

  const fetchGraphData = async () => {
    if (graphMode === "query" && queryResult) {
      // Map query subgraph nodes & edges
      const nodes = [];
      const edges = [];
      
      const visited = queryResult.visited_nodes || [];
      const chunks = queryResult.evidence_chunks || [];
      
      // Seed anchors
      (queryResult.seed_anchors || []).forEach(e => {
        nodes.push({ data: { id: e.id, label: e.canonical_name, type: "anchor" } });
      });

      // Visited artifacts/anchors
      visited.forEach(nodeId => {
        if (!nodes.some(n => n.data.id === nodeId)) {
          const isArtifact = nodeId.startsWith("genshin_fandom:") || nodeId.startsWith("ART_");
          nodes.push({
            data: {
              id: nodeId,
              label: isArtifact ? nodeId.split(":").pop().replace(/_/g, " ") : nodeId,
              type: isArtifact ? "artifact" : "anchor"
            }
          });
        }
      });

      // Visited paths edges
      const nodeIdsSet = new Set(nodes.map(n => n.data.id));
      (queryResult.discovered_paths || []).forEach(path => {
        for (let i = 0; i < path.hops.length - 1; i++) {
          const u = path.hops[i];
          const v = path.hops[i+1];
          if (nodeIdsSet.has(u) && nodeIdsSet.has(v)) {
            const relType = path.relations[i] || "links";
            const edgeId = `edge_${u}_${v}_${i}`;
            if (!edges.some(e => e.data.id === edgeId)) {
              edges.push({
                data: {
                  id: edgeId,
                  source: u,
                  target: v,
                  label: relType,
                  type: relType
                }
              });
            }
          }
        }
      });

      // Evidence relations
      chunks.forEach(c => {
        if (nodeIdsSet.has(c.artifact_id)) {
          visited.forEach(nodeId => {
            if (nodeIdsSet.has(nodeId) && !nodeId.startsWith("genshin_fandom:") && !nodeId.startsWith("ART_")) {
              const mentionEdgeId = `edge_${c.artifact_id}_${nodeId}_query`;
              if (!edges.some(e => e.data.id === mentionEdgeId)) {
                edges.push({
                  data: {
                    id: mentionEdgeId,
                    source: c.artifact_id,
                    target: nodeId,
                    label: "mentions",
                    type: "mentions"
                  }
                });
              }
            }
          });
        }
      });

      setGraphData({ nodes, edges });
    } else {
      // Corpus Graph View
      try {
        const res = await fetch(`${API_BASE}/graph`);
        const data = await res.json();
        setGraphData(data);
      } catch (err) {
        console.error("Error fetching graph data:", err);
      }
    }
  };

  const handleResetDb = async () => {
    if (!window.confirm("Are you absolutely sure you want to clear all database tables and reset indexes?")) return;
    try {
      const res = await fetch(`${API_BASE}/reset`, { method: "POST" });
      const data = await res.json();
      setSyncLogs(prev => [`RESET: ${data.message}`, ...prev]);
      setDbStats(null);
      setArtifacts([]);
      setArtifactDetails(null);
      setQueryResult(null);
      setGraphData(null);
      fetchStats();
    } catch (err) {
      alert("Reset failed: " + err.message);
    }
  };

  const handleCrawl = async () => {
    try {
      const res = await fetch(`${API_BASE}/crawl`, { method: "POST" });
      const data = await res.json();
      setActiveJobId(data.job_id);
      setSyncLogs(prev => [`JOB STARTED: ID ${data.job_id} submitted to worker thread.`, ...prev]);
    } catch (err) {
      setSyncLogs(prev => [`Crawl submission error: ${err.message}`, ...prev]);
    }
  };

  const handleExecuteQuery = async (overrideText = null) => {
    const textToQuery = overrideText || queryText;
    if (!textToQuery.strip?.() && !textToQuery) return;

    setQueryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          q: textToQuery,
          max_depth: maxDepth,
          enable_scoring: enableScoring
        })
      });
      const data = await res.json();
      setQueryResult(data);

      // Add to local query history
      const historyItem = {
        id: uuid(),
        q: textToQuery,
        maxDepth,
        enableScoring,
        data,
        timestamp: new Date().toLocaleTimeString()
      };
      setQueryHistory(prev => [historyItem, ...prev.slice(0, 9)]);
    } catch (err) {
      console.error("Query failed:", err);
      alert("Query execution failed: " + err.message);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleReplayQuery = (historyItem) => {
    setQueryText(historyItem.q);
    setMaxDepth(historyItem.maxDepth);
    setEnableScoring(historyItem.enableScoring);
    setQueryResult(historyItem.data);
    setActiveTab("query");
  };

  const uuid = () => Math.random().toString(36).substring(2, 10);

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleExplorerLookup = async (id) => {
    setExplorerError(null);
    try {
      const res = await fetch(`${API_BASE}/artifact/${encodeURIComponent(id)}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Document is linked but has not been crawled/ingested in this run (capped at 500 pages).`);
      }
      const data = await res.json();
      setExplorerArtifact(data);
      setActiveTab("explorer");
    } catch (err) {
      console.error("Explorer Lookup error:", err);
      setExplorerError(err.message);
      setExplorerArtifact(null);
      setActiveTab("explorer");
    }
  };

  return (
    <div className="console-container">
      {/* Sidebar Nav */}
      <aside className="console-sidebar">
        <div className="sidebar-logo">
          <Network className="logo-icon" />
          <span>Graphyra<span className="logo-badge">DEV</span></span>
        </div>
        <nav className="sidebar-nav">
          <button 
            className={`nav-item ${activeTab === "corpus" ? "active" : ""}`}
            onClick={() => setActiveTab("corpus")}
          >
            <Database size={16} />
            <span>Corpus</span>
          </button>
          <button 
            className={`nav-item ${activeTab === "ingestion" ? "active" : ""}`}
            onClick={() => setActiveTab("ingestion")}
          >
            <Layers size={16} />
            <span>Ingestion Pipeline</span>
          </button>
          <button 
            className={`nav-item ${activeTab === "explorer" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("explorer");
              if (artifacts.length > 0 && !explorerArtifact) {
                handleExplorerLookup(artifacts[0].id);
              }
            }}
          >
            <Search size={16} />
            <span>Explorer</span>
          </button>
          <button 
            className={`nav-item ${activeTab === "query" ? "active" : ""}`}
            onClick={() => setActiveTab("query")}
          >
            <Play size={16} />
            <span>Query Trace</span>
          </button>
          <button 
            className={`nav-item ${activeTab === "graph" ? "active" : ""}`}
            onClick={() => setActiveTab("graph")}
          >
            <Map size={16} />
            <span>Graph Visualizer</span>
          </button>
          <button 
            className={`nav-item ${activeTab === "diagnostics" ? "active" : ""}`}
            onClick={() => setActiveTab("diagnostics")}
          >
            <Activity size={16} />
            <span>Diagnostics</span>
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="db-health-indicator">
            <span className="health-dot active"></span>
            <span>Index Status: ONLINE</span>
          </div>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="console-workspace">
        
        {/* Tab 1: Corpus */}
        {activeTab === "corpus" && (
          <div className="workspace-tab animate-fade">
            <header className="tab-header">
              <h1>Corpus Ingestion & Metrics</h1>
              <p>Manage raw wiki crawlers, trigger asynchronous sync jobs, and inspect system database statistics.</p>
            </header>

            <div className="stats-row">
              <div className="stats-card">
                <div className="card-icon blue"><FileText size={20} /></div>
                <div className="card-info">
                  <h3>{dbStats ? dbStats.artifacts_count : 0}</h3>
                  <p>Artifacts</p>
                </div>
              </div>
              <div className="stats-card">
                <div className="card-icon purple"><Layers size={20} /></div>
                <div className="card-info">
                  <h3>{dbStats ? dbStats.chunks_count : 0}</h3>
                  <p>Evidence Chunks</p>
                </div>
              </div>
              <div className="stats-card">
                <div className="card-icon amber"><Network size={20} /></div>
                <div className="card-info">
                  <h3>{dbStats ? dbStats.anchors_count : 0}</h3>
                  <p>Resolved Anchors</p>
                </div>
              </div>
              <div className="stats-card">
                <div className="card-icon green"><Activity size={20} /></div>
                <div className="card-info">
                  <h3>{dbStats ? dbStats.relations_count : 0}</h3>
                  <p>Relations Edges</p>
                </div>
              </div>
            </div>

            <div className="control-grid">
              <div className="control-panel glass">
                <h2>Corpus Management Sync</h2>
                <p className="panel-desc">Execute an asynchronous crawl of the Genshin Wiki to pull target lore and build retrieval index structures.</p>
                
                <div className="sync-buttons">
                  <button 
                    className="btn primary" 
                    onClick={handleCrawl}
                    disabled={activeJobId !== null}
                  >
                    <RefreshCw className={activeJobId ? "spin" : ""} size={16} />
                    <span>{activeJobId ? "Syncing..." : "Sync Wiki Pages"}</span>
                  </button>
                  
                  <button className="btn danger" onClick={handleResetDb}>
                    <Trash2 size={16} />
                    <span>Reset Database</span>
                  </button>
                </div>

                {jobStatus && (
                  <div className="job-status-panel animate-fade">
                    <div className="job-status-header">
                      <div className="job-status-title">
                        {jobStatus.status === "running" && <RefreshCw size={16} className="spin icon-blue" />}
                        {jobStatus.status === "completed" && <CheckCircle2 size={16} className="icon-green" />}
                        {jobStatus.status === "failed" && <AlertTriangle size={16} className="icon-red" />}
                        <span>Job ID: <code>{jobStatus.id}</code></span>
                      </div>
                      <span className={`status-badge ${jobStatus.status}`}>{jobStatus.status.toUpperCase()}</span>
                    </div>

                    <div className="job-pipeline-visual">
                      <div className={`stage-node ${jobStatus.progress >= 5 ? "active" : ""}`}>
                        <div className="stage-dot">1</div>
                        <div className="stage-label">Reset DB</div>
                      </div>
                      <div className="stage-connector"></div>
                      <div className={`stage-node ${jobStatus.progress >= 10 ? "active" : ""}`}>
                        <div className="stage-dot">2</div>
                        <div className="stage-label">Discover API</div>
                      </div>
                      <div className="stage-connector"></div>
                      <div className={`stage-node ${jobStatus.progress >= 15 && jobStatus.progress < 60 ? "active active-pulse" : jobStatus.progress >= 60 ? "active" : ""}`}>
                        <div className="stage-dot">3</div>
                        <div className="stage-label">Crawl Wiki</div>
                      </div>
                      <div className="stage-connector"></div>
                      <div className={`stage-node ${jobStatus.progress >= 60 && jobStatus.progress < 100 ? "active active-pulse" : jobStatus.progress >= 100 ? "active" : ""}`}>
                        <div className="stage-dot">4</div>
                        <div className="stage-label">Ingest Pipeline</div>
                      </div>
                    </div>

                    <div className="progress-bar-container">
                      <div className="progress-bar" style={{ width: `${jobStatus.progress}%` }}></div>
                      <span className="progress-pct">{jobStatus.progress}%</span>
                    </div>

                    <div className="job-status-log-card">
                      <span className="log-badge">Active Step</span>
                      <p className="job-status-message">{jobStatus.message}</p>
                    </div>
                    
                    {jobStatus.metrics && jobStatus.status === "completed" && (
                      <div className="metrics-summary animate-fade">
                        <h4>Ingestion Stage Metrics</h4>
                        <div className="metrics-grid">
                          <div className="metric-box">
                            <span className="metric-lbl">Artifacts</span>
                            <span className="metric-val">{jobStatus.metrics.artifacts_created}</span>
                          </div>
                          <div className="metric-box">
                            <span className="metric-lbl">Chunks</span>
                            <span className="metric-val">{jobStatus.metrics.chunks_created}</span>
                          </div>
                          <div className="metric-box">
                            <span className="metric-lbl">Mentions</span>
                            <span className="metric-val">{jobStatus.metrics.mentions_extracted}</span>
                          </div>
                          <div className="metric-box">
                            <span className="metric-lbl">Resolved Anchors</span>
                            <span className="metric-val">{jobStatus.metrics.anchors_resolved}</span>
                          </div>
                          <div className="metric-box">
                            <span className="metric-lbl">Relations</span>
                            <span className="metric-val">{jobStatus.metrics.relations_created}</span>
                          </div>
                          <div className="metric-box">
                            <span className="metric-lbl">Duration</span>
                            <span className="metric-val">{jobStatus.metrics.duration}s</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="control-panel glass">
                <h2>Crawl & Ingestion Logs</h2>
                <div className="logs-container">
                  {syncLogs.length === 0 ? (
                    <div className="empty-logs">No activity logs recorded. Trigger a database sync or reset.</div>
                  ) : (
                    syncLogs.map((log, idx) => (
                      <div key={idx} className="log-line">
                        <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
                        <span className="log-text">{log}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Ingestion Inspector */}
        {activeTab === "ingestion" && (
          <div className="workspace-tab animate-fade">
            <header className="tab-header">
              <h1>Ingestion Pipeline Inspector</h1>
              <p>Step-by-step debugger showing the path from a source <code>KnowledgeDocument</code> to generated chunks, mentions, and canonical anchors.</p>
            </header>

            <div className="inspector-layout">
              <div className="inspector-sidebar glass">
                <h3>Catalog Index</h3>
                <div className="artifact-list">
                  {artifacts.length === 0 ? (
                    <div className="empty-list-info">No artifacts loaded. Run a sync job first.</div>
                  ) : (
                    artifacts.map(art => (
                      <button 
                        key={art.id} 
                        className={`artifact-item-btn ${selectedArtifactId === art.id ? "active" : ""}`}
                        onClick={() => setSelectedArtifactId(art.id)}
                      >
                        <FileText size={14} />
                        <span>{art.title}</span>
                      </button>
                    ))
                  )}
                </div>
              </div>

              <div className="inspector-detail glass">
                <div className="detail-tabs">
                  <span className="detail-title">Pipeline Analysis</span>
                  <div className="view-toggle">
                    <button 
                      className={!ingestionJsonMode ? "active" : ""}
                      onClick={() => setIngestionJsonMode(false)}
                    >
                      <Layers size={14} /> UI View
                    </button>
                    <button 
                      className={ingestionJsonMode ? "active" : ""}
                      onClick={() => setIngestionJsonMode(true)}
                    >
                      <Code size={14} /> JSON View
                    </button>
                  </div>
                </div>

                <div className="detail-body">
                  {!artifactDetails ? (
                    <div className="empty-state">Select an artifact from the sidebar to inspect the ingestion stages.</div>
                  ) : ingestionJsonMode ? (
                    <pre className="json-block">{JSON.stringify(artifactDetails, null, 2)}</pre>
                  ) : (
                    <div className="pipeline-steps-vertical">
                      <div className="pipeline-step-box">
                        <div className="step-num">01</div>
                        <div className="step-content">
                          <h4>Original Knowledge Document Container</h4>
                          <div className="metadata-tag-grid">
                            <span>ID: <code>{artifactDetails.artifact.id}</code></span>
                            <span>Type: <strong className="type-lbl">{artifactDetails.artifact.source_type}</strong></span>
                          </div>
                        </div>
                      </div>

                      <div className="pipeline-arrow-down"></div>

                      <div className="pipeline-step-box">
                        <div className="step-num">02</div>
                        <div className="step-content">
                          <h4>Generated Text Chunks ({artifactDetails.chunks?.length || 0})</h4>
                          <div className="chunks-inspector-list">
                            {artifactDetails.chunks?.map((c, i) => (
                              <div key={c.id} className="chunk-inspector-card">
                                <span className="card-badge">Chunk #{i+1} (ID: {c.id})</span>
                                <p>{c.content}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="pipeline-arrow-down"></div>

                      <div className="pipeline-step-box">
                        <div className="step-num">03</div>
                        <div className="step-content">
                          <h4>Extracted Mention Tokens & Resolved Anchors</h4>
                          <div className="resolved-anchors-tags">
                            {artifactDetails.resolved_anchors?.length === 0 ? (
                              <div className="no-tags">No anchors detected or resolved in text chunks.</div>
                            ) : (
                              artifactDetails.resolved_anchors.map(anchor => (
                                <div key={anchor.id} className="anchor-tag">
                                  <Network size={12} />
                                  <span>{anchor.canonical_name}</span>
                                  <span className="anchor-id-badge">ID: {anchor.id}</span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Explorer */}
        {activeTab === "explorer" && (
          <div className="workspace-tab animate-fade">
            <header className="tab-header">
              <h1>Corpus Explorer</h1>
              <p>Explore incoming/outgoing reference hyperlinks across documents and explore the internal corpus structure like a mini Wikipedia.</p>
            </header>

            <div className="explorer-search-bar">
              <Search className="search-icon" size={16} />
              <input 
                type="text" 
                placeholder="Search artifact titles (e.g. Nahida, Irminsul)..." 
                value={explorerSearch}
                onChange={(e) => setExplorerSearch(e.target.value)}
              />
              {explorerSearch && (
                <div className="search-dropdown glass">
                  {artifacts
                    .filter(art => art.title.toLowerCase().includes(explorerSearch.toLowerCase()))
                    .map(art => (
                      <button 
                        key={art.id} 
                        onClick={() => {
                          handleExplorerLookup(art.id);
                          setExplorerSearch("");
                        }}
                      >
                        {art.title}
                      </button>
                    ))
                  }
                </div>
              )}
            </div>

            <div className="explorer-workspace glass">
              <div className="detail-tabs">
                <span className="detail-title">Wiki Document Panel</span>
                <div className="view-toggle">
                  <button 
                    className={!explorerJsonMode ? "active" : ""}
                    onClick={() => setExplorerJsonMode(false)}
                  >
                    <FileText size={14} /> UI View
                  </button>
                  <button 
                    className={explorerJsonMode ? "active" : ""}
                    onClick={() => setExplorerJsonMode(true)}
                  >
                    <Code size={14} /> JSON View
                  </button>
                </div>
              </div>

              <div className="detail-body animate-fade">
                {explorerError && (
                  <div className="explorer-error-banner animate-fade">
                    <AlertTriangle size={24} className="err-icon" />
                    <div className="err-text">
                      <h4>Document Not Ingested</h4>
                      <p>{explorerError}</p>
                    </div>
                  </div>
                )}
                {!explorerArtifact && !explorerError ? (
                  <div className="empty-state">Use the search bar above to look up and load document artifacts.</div>
                ) : explorerJsonMode && explorerArtifact ? (
                  <pre className="json-block">{JSON.stringify(explorerArtifact, null, 2)}</pre>
                ) : explorerArtifact ? (
                  <div className="explorer-document-view">
                    <header className="doc-header">
                      <h2>{explorerArtifact.artifact.title}</h2>
                      <span className="doc-type-badge">{explorerArtifact.artifact.source_type}</span>
                    </header>

                    <div className="doc-body-grid">
                      <div className="doc-content-section">
                        <h3>Content Chunks</h3>
                        {explorerArtifact.chunks?.map((c, i) => (
                          <div key={c.id} className="doc-chunk-paragraph">
                            <span className="p-num">{i+1}</span>
                            <p>{c.content}</p>
                          </div>
                        ))}
                      </div>

                      <div className="doc-connections-section">
                        <div className="connections-card">
                          <h3>Outgoing Hyperlinks (links_to)</h3>
                          <div className="connections-list">
                            {explorerArtifact.outgoing_links?.length === 0 ? (
                              <div className="no-links">No outgoing references discovered.</div>
                            ) : (
                              explorerArtifact.outgoing_links.map((link, idx) => (
                                <button 
                                  key={idx} 
                                  className="link-navigate-btn"
                                  onClick={() => handleExplorerLookup(link.target_id)}
                                >
                                  <span>{link.target_id.split(":").pop().replace(/_/g, " ")}</span>
                                  <ArrowRight size={12} />
                                </button>
                              ))
                            )}
                          </div>
                        </div>

                        <div className="connections-card">
                          <h3>Incoming Hyperlinks</h3>
                          <div className="connections-list">
                            {explorerArtifact.incoming_links?.length === 0 ? (
                              <div className="no-links">No incoming references discovered.</div>
                            ) : (
                              explorerArtifact.incoming_links.map((link, idx) => (
                                <button 
                                  key={idx} 
                                  className="link-navigate-btn"
                                  onClick={() => handleExplorerLookup(link.source_id)}
                                >
                                  <span>{link.source_id.split(":").pop().replace(/_/g, " ")}</span>
                                  <ArrowRight size={12} />
                                </button>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Query Trace */}
        {activeTab === "query" && (
          <div className="workspace-tab animate-fade">
            <header className="tab-header">
              <h1>Graph-Constrained Traversal Trace</h1>
              <p>Execute retrieval queries, trace resolved anchors, scoring mechanisms, and inspect exact retrieved evidence constraints.</p>
            </header>

            <div className="query-settings-bar glass">
              <div className="query-input-wrapper">
                <input 
                  type="text" 
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder="Ask Graphyra a question..."
                  onKeyDown={(e) => e.key === "Enter" && handleExecuteQuery()}
                />
                <button className="btn primary" onClick={() => handleExecuteQuery()} disabled={queryLoading}>
                  <Play size={14} /> Run Query
                </button>
              </div>

              <div className="query-params-row">
                <div className="param-item">
                  <label>Max Hops Depth:</label>
                  <input 
                    type="range" 
                    min="1" 
                    max="5" 
                    value={maxDepth} 
                    onChange={(e) => setMaxDepth(parseInt(e.target.value))} 
                  />
                  <span>{maxDepth}</span>
                </div>
                <div className="param-item checkbox">
                  <input 
                    type="checkbox" 
                    id="scoring" 
                    checked={enableScoring}
                    onChange={(e) => setEnableScoring(e.target.checked)}
                  />
                  <label htmlFor="scoring">Enable Path Scoring</label>
                </div>
              </div>
            </div>

            {queryLoading && (
              <div className="query-loading-spinner glass animate-pulse">
                <RefreshCw size={24} className="spin" />
                <span>Running BFS Traversal constrains and evidence mapping...</span>
              </div>
            )}

            {queryResult && !queryLoading && (
              <div className="query-results-panel">
                <div className="detail-tabs">
                  <span className="detail-title">Query Traversal Trace Outcomes</span>
                  <div className="view-toggle">
                    <button 
                      className={!queryJsonMode ? "active" : ""}
                      onClick={() => setQueryJsonMode(false)}
                    >
                      <Layers size={14} /> UI View
                    </button>
                    <button 
                      className={queryJsonMode ? "active" : ""}
                      onClick={() => setQueryJsonMode(true)}
                    >
                      <Code size={14} /> JSON View
                    </button>
                  </div>
                </div>

                <div className="detail-body">
                  {queryJsonMode ? (
                    <pre className="json-block">{JSON.stringify(queryResult, null, 2)}</pre>
                  ) : (
                    <div className="query-trace-ui-grid">
                      {/* Left Pane: Route Steps & Hops */}
                      <div className="trace-pathways-section">
                        <div className="diagnostics-summary-card">
                          <h3>Execution Diagnostics</h3>
                          <div className="diag-mini-grid">
                            <div><Clock size={12} /> Latency: <strong>{queryResult.diagnostics?.latency_ms} ms</strong></div>
                            <div><Layers size={12} /> Nodes Expanded: <strong>{queryResult.diagnostics?.nodes_expanded}</strong></div>
                            <div><Network size={12} /> Paths Found: <strong>{queryResult.diagnostics?.paths_discovered}</strong></div>
                          </div>
                        </div>

                        <div className="reasoning-trace-logs">
                          <h3>Traversal Reasoning Trace</h3>
                          <div className="reasoning-lines">
                            {queryResult.trace_steps?.map((step, idx) => (
                              <div key={idx} className="reasoning-step-line">
                                <span className="bullet">↳</span>
                                <p>{step}</p>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="paths-tree-visualizer">
                          <h3>Discovered Traversal Paths</h3>
                          {queryResult.discovered_paths?.length === 0 ? (
                            <div className="no-paths-info">No paths mapped under depth limit constraints.</div>
                          ) : (
                            queryResult.discovered_paths.map((path, idx) => (
                              <div key={idx} className="path-tree-card">
                                <div className="path-header">
                                  <span>Path #{idx+1}</span>
                                  <span>Score: <strong className="score-badge">{path.score}</strong></span>
                                </div>
                                <div className="path-hops-sequence">
                                  {path.hops.map((hop, hidx) => {
                                    const isArtifact = hop.startsWith("genshin_fandom:") || hop.startsWith("ART_");
                                    const label = isArtifact ? hop.split(":").pop().replace(/_/g, " ") : hop;
                                    return (
                                      <React.Fragment key={hidx}>
                                        <div className={`hop-node ${isArtifact ? "art" : "anch"}`}>
                                          {label}
                                        </div>
                                        {hidx < path.hops.length - 1 && (
                                          <div className="hop-connector">
                                            <span>{path.relations[hidx]}</span>
                                            <ArrowRight size={10} />
                                          </div>
                                        )}
                                      </React.Fragment>
                                    );
                                  })}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>

                      {/* Right Pane: Evidence Sentences retrieved */}
                      <div className="trace-evidence-section">
                        <h3>Retrieved Context Evidence ({queryResult.evidence_chunks?.length || 0})</h3>
                        <div className="evidence-list-panel">
                          {queryResult.evidence_chunks?.length === 0 ? (
                            <div className="no-evidence">No evidence sentences retrieved.</div>
                          ) : (
                            queryResult.evidence_chunks.map((chunk, idx) => (
                              <div key={chunk.id} className="evidence-chunk-card">
                                <div className="evidence-header">
                                  <span>Rank #{idx+1} (ID: {chunk.id})</span>
                                  <span>Score: <strong>{chunk.score}</strong></span>
                                </div>
                                <p>{chunk.content}</p>
                                <div className="evidence-provenance">
                                  <span>Source:</span>
                                  <button onClick={() => handleExplorerLookup(chunk.artifact_id)}>
                                    {chunk.artifact_title}
                                  </button>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Graph Visualizer */}
        {activeTab === "graph" && (
          <div className="workspace-tab tab-graph animate-fade">
            <header className="tab-header flex-header">
              <div>
                <h1>Lore Network Topology Graph</h1>
                <p>Interactive force-directed visualization of full corpus indexes or query traversal constraints subgraphs.</p>
              </div>
              <div className="graph-controls-header">
                <div className="mode-toggle">
                  <button 
                    className={graphMode === "corpus" ? "active" : ""}
                    onClick={() => setGraphMode("corpus")}
                  >
                    Corpus Graph
                  </button>
                  <button 
                    className={graphMode === "query" ? "active" : ""}
                    onClick={() => {
                      if (!queryResult) {
                        alert("Please run a query first to view its traversal constraint subgraph.");
                        return;
                      }
                      setGraphMode("query");
                    }}
                  >
                    Query Traversal Graph
                  </button>
                </div>

                <div className="view-toggle">
                  <button 
                    className={!graphJsonMode ? "active" : ""}
                    onClick={() => setGraphJsonMode(false)}
                  >
                    <Network size={14} /> Interactive Graph
                  </button>
                  <button 
                    className={graphJsonMode ? "active" : ""}
                    onClick={() => setGraphJsonMode(true)}
                  >
                    <Code size={14} /> JSON View
                  </button>
                </div>
              </div>
            </header>

            <div className="graph-workspace-panel glass">
              {graphJsonMode ? (
                <div className="detail-body">
                  <pre className="json-block">{JSON.stringify(graphData, null, 2)}</pre>
                </div>
              ) : (
                <div className="cytoscape-outer-container">
                  <div className="graph-legend">
                    <div className="legend-item"><span className="legend-dot blue"></span> Artifact Document</div>
                    <div className="legend-item"><span className="legend-dot purple"></span> Resolved Anchor</div>
                    <div className="legend-item"><span className="legend-line solid-green"></span> links_to Relation</div>
                    <div className="legend-item"><span className="legend-line dotted-amber"></span> mentions Relation</div>
                  </div>
                  <div ref={graphContainerRef} className="cytoscape-container"></div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 6: Diagnostics */}
        {activeTab === "diagnostics" && (
          <div className="workspace-tab animate-fade">
            <header className="tab-header">
              <h1>System Diagnostics & Ingestion Quality Audit</h1>
              <p>Inspect database indexing integrity, look up latency metrics, and review corpus coverage diagnostics.</p>
            </header>

            <div className="diagnostics-grid">
              {/* SQLite stats */}
              <div className="diagnostic-panel glass">
                <h2>SQLite Storage Diagnostics</h2>
                {dbStats && (
                  <div className="stats-list">
                    <div className="stat-line">
                      <span>Database Path:</span>
                      <code>/home/vicky/v_drive/Codes/Graphyra/graphyra.db</code>
                    </div>
                    <div className="stat-line">
                      <span>Database File Size:</span>
                      <strong>{formatBytes(dbStats.db_size_bytes)}</strong>
                    </div>
                    <div className="stat-line">
                      <span>FTS5 Search Virtual Tables:</span>
                      <strong className="success-lbl">ONLINE (FTS5 Enabled)</strong>
                    </div>
                    <div className="stat-line">
                      <span>Indexing Status:</span>
                      <span className="health-badge healthy">HEALTHY</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Query history & replay */}
              <div className="diagnostic-panel glass">
                <h2>Query Replay Cache</h2>
                <p className="panel-desc">Click on any past query to restore its inputs, parameters, path scores, and subgraphs.</p>
                <div className="history-list">
                  {queryHistory.length === 0 ? (
                    <div className="empty-history-info">
                      <History size={20} />
                      <p>No queries executed in current session cache.</p>
                    </div>
                  ) : (
                    queryHistory.map(item => (
                      <button 
                        key={item.id} 
                        className="history-item-btn"
                        onClick={() => handleReplayQuery(item)}
                      >
                        <div className="hist-header">
                          <span className="hist-time">{item.timestamp}</span>
                          <span className="hist-depth">depth: {item.maxDepth}</span>
                        </div>
                        <p className="hist-query">"{item.q}"</p>
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Retrieval Quality Audit Summary */}
              {dbStats && dbStats.avg_chunk_length !== undefined && (
                <div className="diagnostic-panel glass span-two">
                  <h2>Retrieval Quality & Coverage Metrics</h2>
                  <div className="stats-grid-cols">
                    <div className="stats-group">
                      <h3>Chunking Integrity</h3>
                      <div className="stat-line"><span>Total Chunks:</span> <strong>{dbStats.chunks_count}</strong></div>
                      <div className="stat-line"><span>Avg Chunk Length (chars):</span> <strong>{dbStats.avg_chunk_length}</strong></div>
                      <div className="stat-line"><span>Median Chunk Length:</span> <strong>{dbStats.median_chunk_length}</strong></div>
                      <div className="stat-line"><span>Shortest / Longest:</span> <strong>{dbStats.shortest_chunk} / {dbStats.longest_chunk}</strong></div>
                      <div className="stat-line"><span>Chunks &lt; 100 words:</span> <strong>{dbStats.chunks_less_100_words}</strong></div>
                      <div className="stat-line"><span>Chunks &gt; Max Size (400w):</span> <strong className={dbStats.chunks_greater_max_size > 0 ? "warning-lbl" : "success-lbl"}>{dbStats.chunks_greater_max_size}</strong></div>
                      <div className="stat-line"><span>Duplicate Chunks:</span> <strong className={dbStats.duplicate_chunks_count > 0 ? "warning-lbl" : "success-lbl"}>{dbStats.duplicate_chunks_count}</strong></div>
                    </div>
                    <div className="stats-group">
                      <h3>Anchor Coverage Invariant</h3>
                      <div className="stat-line"><span>Artifacts Count:</span> <strong>{dbStats.artifacts_count}</strong></div>
                      <div className="stat-line"><span>Anchors Count:</span> <strong>{dbStats.anchors_count}</strong></div>
                      <div className="stat-line"><span>Anchor Coverage Rate:</span> <strong className="success-lbl">{dbStats.anchor_coverage_pct}%</strong></div>
                      <div className="stat-line"><span>Artifacts Missing Anchors:</span> <strong className={dbStats.missing_artifacts_count > 0 ? "warning-lbl" : "success-lbl"}>{dbStats.missing_artifacts_count}</strong></div>
                      <div className="stat-line"><span>Auto-Registered Anchors:</span> <strong>{dbStats.auto_registered_anchors}</strong></div>
                      <div className="stat-line"><span>Redirect Aliases Registered:</span> <strong>{dbStats.redirect_aliases_count}</strong></div>
                      <div className="stat-line"><span>Mention Density (per chunk):</span> <strong>{dbStats.mention_density}</strong></div>
                    </div>
                    <div className="stats-group">
                      <h3>Graph Relations Breakdown</h3>
                      <div className="stat-line"><span>Total Relations:</span> <strong>{dbStats.relations_count}</strong></div>
                      {Object.entries(dbStats.relation_breakdown || {}).map(([type, count]) => (
                        <div className="stat-line" key={type}>
                          <span>- {type}:</span> <strong>{count}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Word Size Histogram */}
                  {dbStats.chunk_size_histogram && Object.keys(dbStats.chunk_size_histogram).length > 0 && (
                    <div className="histogram-container">
                      <h3>Chunk Size Histogram (Word Counts)</h3>
                      <div className="histogram-bars">
                        {Object.entries(dbStats.chunk_size_histogram)
                          .sort((a, b) => {
                            const valA = parseInt(a[0].split("-")[0]);
                            const valB = parseInt(b[0].split("-")[0]);
                            return valA - valB;
                          })
                          .map(([bucket, count]) => {
                            const maxCount = Math.max(...Object.values(dbStats.chunk_size_histogram), 1);
                            const percentage = (count / maxCount) * 100;
                            return (
                              <div className="histogram-row" key={bucket}>
                                <span className="bucket-label">{bucket} words:</span>
                                <div className="bar-wrapper">
                                  <div className="bar" style={{ width: `${percentage}%` }}></div>
                                  <span className="bar-val">{count} chunks</span>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Actionable Debug Lists Panel */}
              {dbStats && dbStats.avg_chunk_length !== undefined && (
                <div className="diagnostic-panel glass span-two">
                  <h2>Actionable Retrieval Debug Panels</h2>
                  <div className="actionable-lists-grid">
                    {/* List 1: Top Short Chunks */}
                    <div className="actionable-list-box">
                      <h3>Top Shortest Chunks <span>length (chars)</span></h3>
                      {dbStats.top_shortest_chunks?.map(c => (
                        <div className="actionable-item" key={c.id}>
                          <div>
                            <span className="title">{c.id}</span>
                            <div className="text-muted" style={{ fontSize: '10px' }}>{c.content.substring(0, 45)}...</div>
                          </div>
                          <span className="badge">{c.length}</span>
                        </div>
                      ))}
                    </div>

                    {/* List 2: Top Long Chunks */}
                    <div className="actionable-list-box">
                      <h3>Top Longest Chunks <span>length (chars)</span></h3>
                      {dbStats.top_longest_chunks?.map(c => (
                        <div className="actionable-item" key={c.id}>
                          <div>
                            <span className="title">{c.id}</span>
                            <div className="text-muted" style={{ fontSize: '10px' }}>{c.content.substring(0, 45)}...</div>
                          </div>
                          <span className="info-badge">{c.length}</span>
                        </div>
                      ))}
                    </div>

                    {/* List 3: Chunks without Mentions */}
                    <div className="actionable-list-box">
                      <h3>Chunks Without Mentions <span>total: {dbStats.chunks_no_mentions_count}</span></h3>
                      {dbStats.top_chunks_no_mentions?.map(c => (
                        <div className="actionable-item" key={c.id}>
                          <div>
                            <span className="title">{c.id}</span>
                            <div className="text-muted" style={{ fontSize: '10px' }}>{c.content.substring(0, 50)}...</div>
                          </div>
                          <span className="warn-badge">NO MENTIONS</span>
                        </div>
                      ))}
                    </div>

                    {/* List 4: Artifacts highest chunk counts */}
                    <div className="actionable-list-box">
                      <h3>Artifacts with Highest Chunk Counts <span>chunks count</span></h3>
                      {dbStats.top_artifacts_highest_chunks?.map(a => (
                        <div className="actionable-item" key={a.id}>
                          <span className="title">{a.title}</span>
                          <span className="info-badge">{a.chunk_count} chunks</span>
                        </div>
                      ))}
                    </div>

                    {/* List 5: Artifacts missing anchors */}
                    <div className="actionable-list-box">
                      <h3>Artifacts Missing Anchors <span>total: {dbStats.missing_artifacts_count}</span></h3>
                      {dbStats.top_missing_artifacts?.length === 0 ? (
                        <div className="text-muted" style={{ fontSize: '11px', padding: '10px' }}>All artifacts successfully mapped to anchors (100% Coverage).</div>
                      ) : (
                        dbStats.top_missing_artifacts?.map(a => (
                          <div className="actionable-item" key={a.id}>
                            <span className="title">{a.title}</span>
                            <span className="badge">MISSING ANCHOR</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* List 6: Duplicate Chunks */}
                    <div className="actionable-list-box">
                      <h3>Duplicate Chunks <span>duplicates count</span></h3>
                      {dbStats.top_duplicate_chunks?.length === 0 ? (
                        <div className="text-muted" style={{ fontSize: '11px', padding: '10px' }}>No duplicate chunk texts found in the database.</div>
                      ) : (
                        dbStats.top_duplicate_chunks?.map((c, idx) => (
                          <div className="actionable-item" key={idx}>
                            <div>
                              <div className="text-muted" style={{ fontSize: '11px' }}>"{c.content.substring(0, 50)}..."</div>
                            </div>
                            <span className="warn-badge">{c.count} duplicates</span>
                          </div>
                        ))
                      )}
                    </div>

                  </div>
                </div>
              )}

            </div>
          </div>
        )}

      </main>
    </div>
  );
}
