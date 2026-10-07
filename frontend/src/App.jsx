import { useEffect, useMemo, useState } from 'react';
import {
  analyzeInspection,
  createInspection,
  getInspection,
  getInspectionImageUrl,
  healthCheck,
  listInspections,
  overrideInspection,
  uploadInspectionImages,
} from './services/api';

const defaultPo = {
  po_id: 'PO-9001',
  sku: 'BLUE-BOTTLE-001',
  product_name: 'Blue Bottle',
  expected_quantity: 24,
  variant: 'Blue',
  units_per_carton: 12,
  expected_cartons: 2,
  expected_components: ['cap', 'label'],
};

const navItems = ['Overview', 'Inspections', 'Exceptions', 'Evidence', 'Analytics', 'Integration', 'System Health'];

const demoScenarios = [
  { value: 'correct_shipment', label: 'Correct Shipment' },
  { value: 'short_shipment', label: 'Short Shipment' },
  { value: 'wrong_variant', label: 'Wrong Variant' },
  { value: 'damaged_carton', label: 'Damaged Carton' },
  { value: 'ambiguous', label: 'Ambiguous' },
];

const statusToneMap = {
  PASS: 'success',
  EXCEPTION: 'danger',
  UNCERTAIN: 'warning',
};

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function getStatusValue(value) {
  if (!value) return 'UNCERTAIN';
  return String(value).toUpperCase();
}

export default function App() {
  const [activeNav, setActiveNav] = useState('Overview');
  const [inspections, setInspections] = useState([]);
  const [selectedInspectionId, setSelectedInspectionId] = useState('');
  const [inspection, setInspection] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [po, setPo] = useState(defaultPo);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeScenario, setActiveScenario] = useState('correct_shipment');
  const [overrideDecision, setOverrideDecision] = useState('EXCEPTION');
  const [overrideReason, setOverrideReason] = useState('Visible condition requires operator review.');
  const [status, setStatus] = useState('Waiting for receiving intake');
  const [systemStatus, setSystemStatus] = useState({ backend: 'online', ai: 'demo mode', sync: 'healthy' });
  const [search, setSearch] = useState('');

  const refreshInspections = async () => {
    const data = await listInspections();
    const items = data?.items ?? [];
    setInspections(items);

    if (!selectedInspectionId && items.length > 0) {
      setSelectedInspectionId(items[0].inspection_id);
      setInspection(items[0]);
    }

    if (selectedInspectionId) {
      const match = items.find((item) => item.inspection_id === selectedInspectionId);
      if (match) {
        setInspection(match);
      }
    }
  };

  useEffect(() => {
    async function initialize() {
      try {
        const health = await healthCheck();
        if (health?.status === 'ok') {
          setSystemStatus((current) => ({ ...current, backend: 'online' }));
        }
        await refreshInspections();
      } catch (error) {
        setSystemStatus((current) => ({ ...current, backend: 'degraded' }));
        setStatus('Backend unavailable. Please retry in a moment.');
      }
    }

    initialize();
  }, []);

  const analytics = useMemo(() => {
    const total = inspections.length;
    const passed = inspections.filter((item) => item.final_decision === 'PASS').length;
    const exceptions = inspections.filter((item) => item.final_decision === 'EXCEPTION').length;
    const uncertain = inspections.filter((item) => item.final_decision === 'UNCERTAIN').length;
    const openExceptions = inspections.filter((item) => item.final_decision === 'EXCEPTION').length;
    const evidenceProcessed = inspections.reduce((sum, item) => sum + (item.evidence?.length ?? 0), 0);

    const confidenceValues = inspections.flatMap((item) => (item.checks ?? []).map((check) => check.confidence ?? 0));
    const avgConfidence = confidenceValues.length
      ? (confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length) * 100
      : 0;

    const processingValues = inspections
      .map((item) => {
        const created = new Date(item.created_at).getTime();
        const updated = new Date(item.updated_at || item.created_at).getTime();
        return Math.max((updated - created) / 60000, 0);
      })
      .filter((value) => Number.isFinite(value));
    const avgProcessingTime = processingValues.length
      ? processingValues.reduce((sum, value) => sum + value, 0) / processingValues.length
      : 0;

    return {
      total,
      passed,
      exceptions,
      uncertain,
      openExceptions,
      evidenceProcessed,
      avgConfidence,
      avgProcessingTime,
    };
  }, [inspections]);

  const recentInspections = useMemo(
    () => [...inspections].sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)).slice(0, 5),
    [inspections],
  );

  const activeExceptions = useMemo(
    () => inspections.filter((item) => item.final_decision === 'EXCEPTION').slice(0, 5),
    [inspections],
  );

  const decisionDistribution = useMemo(
    () => [
      { label: 'PASS', value: analytics.total ? Math.round((analytics.passed / analytics.total) * 100) : 0 },
      { label: 'EXCEPTION', value: analytics.total ? Math.round((analytics.exceptions / analytics.total) * 100) : 0 },
      { label: 'UNCERTAIN', value: analytics.total ? Math.round((analytics.uncertain / analytics.total) * 100) : 0 },
    ],
    [analytics],
  );

  const currentInspection =
    inspection ?? (selectedInspectionId ? inspections.find((item) => item.inspection_id === selectedInspectionId) ?? null : null);

  const filteredInspections = useMemo(() => {
    if (!search.trim()) return inspections;
    const query = search.toLowerCase();
    return inspections.filter((item) => {
      const poId = item.po?.po_id ?? '';
      const sku = item.po?.sku ?? '';
      return `${poId} ${sku}`.toLowerCase().includes(query);
    });
  }, [inspections, search]);

  const previewUrls = useMemo(
    () => selectedFiles.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [selectedFiles],
  );

  useEffect(
    () => () => {
      previewUrls.forEach((preview) => URL.revokeObjectURL(preview.url));
    },
    [previewUrls],
  );

  const handleCreateInspection = async () => {
    try {
      const created = await createInspection(po);
      setSelectedInspectionId(created.inspection_id);
      setInspection(created);
      setStatus(`Inspection ${created.inspection_id} created for ${created.po.po_id}.`);
      await refreshInspections();
    } catch (error) {
      setStatus(`Inspection creation failed: ${error.message}`);
    }
  };

  const handleUpload = async () => {
    let activeId = selectedInspectionId || inspection?.inspection_id;

    if (!activeId) {
      await handleCreateInspection();
      activeId = selectedInspectionId || inspection?.inspection_id;
    }

    if (!activeId || selectedFiles.length === 0) {
      setStatus('Select an inspection and add evidence images before uploading.');
      return;
    }

    try {
      setUploading(true);
      await uploadInspectionImages(activeId, selectedFiles);
      const refreshed = await getInspection(activeId);
      setInspection(refreshed);
      setSelectedInspectionId(activeId);
      setSelectedFiles([]);
      setStatus(`Uploaded ${selectedFiles.length} evidence image(s) for ${activeId}.`);
      await refreshInspections();
    } catch (error) {
      setStatus(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    let activeId = selectedInspectionId || inspection?.inspection_id;

    if (!activeId) {
      const created = await createInspection(po);
      activeId = created.inspection_id;
      setSelectedInspectionId(activeId);
      setInspection(created);
    }

    if (selectedFiles.length > 0) {
      try {
        setUploading(true);
        await uploadInspectionImages(activeId, selectedFiles);
        setSelectedFiles([]);
      } catch (error) {
        setStatus(`Upload before analysis failed: ${error.message}`);
        return;
      } finally {
        setUploading(false);
      }
    }

    try {
      setAnalyzing(true);
      const result = await analyzeInspection(activeId, activeScenario);
      const refreshed = await getInspection(activeId);
      setInspection(refreshed);
      setSelectedInspectionId(activeId);
      setStatus(`Analysis complete: ${result.decision} for ${refreshed.po.po_id}.`);
      await refreshInspections();
    } catch (error) {
      setStatus(`Analysis failed: ${error.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleOverride = async () => {
    const activeId = selectedInspectionId || inspection?.inspection_id;
    if (!activeId) {
      setStatus('Create or select an inspection before applying an override.');
      return;
    }

    try {
      await overrideInspection(activeId, overrideDecision, overrideReason);
      const refreshed = await getInspection(activeId);
      setInspection(refreshed);
      setSelectedInspectionId(activeId);
      setStatus(`Operator override applied: ${overrideDecision}.`);
      await refreshInspections();
    } catch (error) {
      setStatus(`Override failed: ${error.message}`);
    }
  };

  const selectedPo = currentInspection?.po ?? po;
  const decision = currentInspection?.final_decision ?? 'UNCERTAIN';
  const selectedImages = currentInspection?.images ?? [];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">RI</div>
          <div>
            <div className="eyebrow">CUBE 2026</div>
            <h1>Receiving Intelligence</h1>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((item) => (
            <button
              key={item}
              type="button"
              className={`nav-item ${activeNav === item ? 'active' : ''}`}
              onClick={() => setActiveNav(item)}
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-card">
          <div className="label">Environment</div>
          <div className="status-line">
            <span className="dot online" /> Backend {systemStatus.backend}
          </div>
          <div className="status-line">
            <span className="dot neutral" /> AI {systemStatus.ai}
          </div>
          <div className="status-line">
            <span className="dot success" /> Sync {systemStatus.sync}
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <div className="eyebrow muted">Operations command</div>
            <h2>Inbound Receiving Control Tower</h2>
          </div>

          <div className="topbar-actions">
            <div className="status-pills">
              <span className="mini-pill">Backend: {systemStatus.backend}</span>
              <span className="mini-pill">AI: {systemStatus.ai}</span>
            </div>
            <label className="search-wrap">
              <span>Search</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="PO / SKU" />
            </label>
          </div>
        </header>

        <section className="kpi-grid">
          <article className="kpi-card">
            <div className="kpi-label">Total Inspections</div>
            <strong>{analytics.total}</strong>
            <small>Across all captured shipments</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Passed</div>
            <strong>{analytics.passed}</strong>
            <small>Verified against expected PO</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Exceptions</div>
            <strong>{analytics.exceptions}</strong>
            <small>Failed business-rule checks</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Uncertain</div>
            <strong>{analytics.uncertain}</strong>
            <small>Needs manual review</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Open Exceptions</div>
            <strong>{analytics.openExceptions}</strong>
            <small>Awaiting action</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Average Confidence</div>
            <strong>{analytics.avgConfidence.toFixed(0)}%</strong>
            <small>Across all check results</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Evidence Processed</div>
            <strong>{analytics.evidenceProcessed}</strong>
            <small>Evidence records ingested</small>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">Average Processing Time</div>
            <strong>{analytics.avgProcessingTime.toFixed(1)} min</strong>
            <small>From intake to verdict</small>
          </article>
        </section>

        <section className="content-grid">
          <div className="panel large-panel">
            <div className="panel-header">
              <h3>Today's Receiving Activity</h3>
              <span className="subtle">Live data</span>
            </div>
            <div className="activity-list">
              {recentInspections.length ? (
                recentInspections.map((item) => (
                  <div key={item.inspection_id} className="activity-item">
                    <div>
                      <strong>{item.po?.po_id ?? item.inspection_id}</strong>
                      <small>{item.po?.sku ?? '—'}</small>
                    </div>
                    <span className={`badge ${statusToneMap[getStatusValue(item.final_decision)] ?? 'warning'}`}>
                      {getStatusValue(item.final_decision)}
                    </span>
                    <time>{formatDate(item.updated_at || item.created_at)}</time>
                  </div>
                ))
              ) : (
                <div className="empty-state inline">No recent inspection activity available.</div>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Recent Inspections</h3>
              <span className="subtle">{filteredInspections.length}</span>
            </div>
            <div className="table-list">
              {filteredInspections.length ? (
                filteredInspections.slice(0, 5).map((item) => (
                  <button
                    key={item.inspection_id}
                    type="button"
                    className={`row-button ${selectedInspectionId === item.inspection_id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedInspectionId(item.inspection_id);
                      setInspection(item);
                    }}
                  >
                    <span>{item.po?.po_id ?? item.inspection_id}</span>
                    <span>{item.final_decision ?? 'UNCERTAIN'}</span>
                  </button>
                ))
              ) : (
                <div className="empty-state inline">No inspections yet.</div>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Active Exceptions</h3>
              <span className="subtle">{activeExceptions.length}</span>
            </div>
            <div className="stack-list">
              {activeExceptions.length ? (
                activeExceptions.map((item) => (
                  <div key={item.inspection_id} className="stack-item">
                    <strong>{item.po?.po_id ?? item.inspection_id}</strong>
                    <small>{item.agent_summary || 'Exception requires operator action.'}</small>
                  </div>
                ))
              ) : (
                <div className="empty-state inline">No open exceptions.</div>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Decision Distribution</h3>
              <span className="subtle">{analytics.total} total</span>
            </div>
            <div className="distribution-list">
              {decisionDistribution.map((item) => (
                <div key={item.label} className="distribution-row">
                  <div className="distribution-header">
                    <span>{item.label}</span>
                    <strong>{item.value}%</strong>
                  </div>
                  <div className="distribution-bar">
                    <span style={{ width: `${item.value}%` }} className={`fill ${statusToneMap[item.label] ?? 'warning'}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>AI Processing Status</h3>
              <span className="subtle">Vision + rules</span>
            </div>
            <div className="status-grid">
              <div className="status-row">
                <span>Vision service</span>
                <span className="badge success">Ready</span>
              </div>
              <div className="status-row">
                <span>Quality gates</span>
                <span className="badge neutral">Validated</span>
              </div>
              <div className="status-row">
                <span>Rule engine</span>
                <span className="badge success">Healthy</span>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Integration Events</h3>
              <span className="subtle">Downstream</span>
            </div>
            <div className="event-list">
              <div className="event-item">
                <strong>ERP push</strong>
                <small>Last sync 2 min ago</small>
              </div>
              <div className="event-item">
                <strong>Recovery agent</strong>
                <small>Queued for follow-up</small>
              </div>
              <div className="event-item">
                <strong>Audit trail</strong>
                <small>Immutable record retained</small>
              </div>
            </div>
          </div>
        </section>

        <section className="workspace-grid">
          <div className="panel workspace-panel">
            <div className="panel-header">
              <h3>Shipment Context</h3>
              <span className={`badge ${statusToneMap[getStatusValue(decision)] ?? 'warning'}`}>{decision}</span>
            </div>

            <div className="field-grid">
              <label>
                <span>PO Number</span>
                <input value={selectedPo.po_id ?? ''} onChange={(event) => setPo((current) => ({ ...current, po_id: event.target.value }))} />
              </label>
              <label>
                <span>Shipment ID</span>
                <input value={selectedPo.po_id ? `SHIP-${selectedPo.po_id.replace('PO-', '')}` : ''} readOnly />
              </label>
              <label>
                <span>Supplier</span>
                <input value="Alpha Logistics" readOnly />
              </label>
              <label>
                <span>SKU</span>
                <input value={selectedPo.sku ?? ''} onChange={(event) => setPo((current) => ({ ...current, sku: event.target.value }))} />
              </label>
              <label>
                <span>Expected Quantity</span>
                <input type="number" value={selectedPo.expected_quantity ?? 0} onChange={(event) => setPo((current) => ({ ...current, expected_quantity: Number(event.target.value) }))} />
              </label>
              <label>
                <span>Expected Cartons</span>
                <input type="number" value={selectedPo.expected_cartons ?? 0} onChange={(event) => setPo((current) => ({ ...current, expected_cartons: Number(event.target.value) }))} />
              </label>
              <label>
                <span>Units per Carton</span>
                <input type="number" value={selectedPo.units_per_carton ?? 0} onChange={(event) => setPo((current) => ({ ...current, units_per_carton: Number(event.target.value) }))} />
              </label>
              <label>
                <span>Expected Variant</span>
                <input value={selectedPo.variant ?? ''} onChange={(event) => setPo((current) => ({ ...current, variant: event.target.value }))} />
              </label>
              <label className="full-width">
                <span>Expected Components</span>
                <input
                  value={(selectedPo.expected_components ?? []).join(', ')}
                  onChange={(event) =>
                    setPo((current) => ({
                      ...current,
                      expected_components: event.target.value
                        .split(',')
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }))
                  }
                />
              </label>
            </div>
          </div>

          <div className="panel workspace-panel">
            <div className="panel-header">
              <h3>Evidence</h3>
              <span className="subtle">{selectedImages.length + selectedFiles.length} files</span>
            </div>

            <div className="upload-box">
              <input
                id="file-input"
                type="file"
                multiple
                accept="image/png,image/jpeg,image/webp"
                onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))}
              />
              <label htmlFor="file-input" className="upload-button">Add evidence photos</label>
            </div>

            <div className="preview-grid">
              {previewUrls.length ? (
                previewUrls.map(({ file, url }) => (
                  <div key={`${file.name}-${file.lastModified}`} className="preview-card">
                    <img src={url} alt={file.name} />
                    <span>{file.name}</span>
                  </div>
                ))
              ) : selectedImages.length ? (
                selectedImages.map((image) => (
                  <div key={image.image_id} className="preview-card">
                    <img src={getInspectionImageUrl(currentInspection.inspection_id, image.image_id)} alt={image.filename} />
                    <span>{image.filename}</span>
                  </div>
                ))
              ) : (
                <div className="empty-state inline">No evidence attached yet.</div>
              )}
            </div>

            <div className="action-row">
              <button type="button" className="primary-button" onClick={handleCreateInspection} disabled={uploading || analyzing}>
                Create inspection
              </button>
              <button type="button" className="secondary-button" onClick={handleUpload} disabled={uploading || analyzing || selectedFiles.length === 0}>
                {uploading ? 'Uploading...' : 'Upload evidence'}
              </button>
              <button type="button" className="primary-button" onClick={handleAnalyze} disabled={uploading || analyzing}>
                {analyzing ? 'Analyzing...' : 'Analyze shipment'}
              </button>
            </div>

            <div className="scenario-list compact-list">
              {demoScenarios.map((scenario) => (
                <button
                  key={scenario.value}
                  type="button"
                  className={`scenario-pill ${activeScenario === scenario.value ? 'selected' : ''}`}
                  onClick={() => setActiveScenario(scenario.value)}
                >
                  {scenario.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="bottom-grid">
          <div className="panel">
            <div className="panel-header">
              <h3>Inspection Summary</h3>
              <span className="subtle">{currentInspection?.inspection_id ?? 'No selection'}</span>
            </div>
            <div className="summary-box">
              <div className={`status-banner ${statusToneMap[getStatusValue(decision)] ?? 'warning'}`}>
                {decision}
              </div>
              <p>{currentInspection?.agent_summary ?? 'No inspection summary available yet.'}</p>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Operator Override</h3>
              <span className="subtle">Manual decision</span>
            </div>
            <div className="override-form">
              <select value={overrideDecision} onChange={(event) => setOverrideDecision(event.target.value)}>
                <option value="PASS">PASS</option>
                <option value="EXCEPTION">EXCEPTION</option>
                <option value="UNCERTAIN">UNCERTAIN</option>
              </select>
              <textarea value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} rows={4} />
              <button type="button" className="secondary-button wide" onClick={handleOverride}>
                Apply override
              </button>
            </div>
          </div>
        </section>

        <footer className="footer-bar">
          <span>{status}</span>
        </footer>
      </main>
    </div>
  );
}
