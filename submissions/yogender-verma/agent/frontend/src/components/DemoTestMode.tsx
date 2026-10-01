import React, { useState } from 'react';
import {
  Sparkles, FlaskConical, AlertTriangle, CheckCircle, HelpCircle,
  ShieldAlert, RefreshCw, Cpu, Box, Camera, ArrowRight, ExternalLink,
  ChevronRight, ShieldCheck, Play
} from 'lucide-react';
import { runInspection, InspectionPayload } from '../api';
import { PURCHASE_ORDERS_CATALOG, PurchaseOrderItem } from '../data/purchaseOrders';
import { getImageUrl } from './ReceivingInspectionStation';

interface Props {
  orgId: string;
  onRecordCreated: () => void;
  onLoadInReceiving: (poNumber: string) => void;
}

export const DemoTestMode: React.FC<Props> = ({ orgId, onRecordCreated, onLoadInReceiving }) => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('s1');
  const [loading, setLoading] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<any>(null);

  // Challenge Scenarios 1-11
  const scenarios = PURCHASE_ORDERS_CATALOG.filter(p => p.scenario_id);

  const activeScenario = scenarios.find(s => s.scenario_id === selectedScenarioId) || scenarios[0];

  const handleRunTest = async (scenario: PurchaseOrderItem) => {
    setSelectedScenarioId(scenario.scenario_id || 's1');
    setLoading(true);

    const sim = scenario.sim_context || {
      cartons_received: scenario.cartons_ordered,
      units_per_carton_counted: scenario.units_per_carton_ordered,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    };

    let activePhotos = [scenario.default_photo];
    if (sim.damage && sim.damage !== 'none' && !activePhotos[0].includes(sim.damage)) {
      activePhotos.push(`fixtures/receiving/${scenario.unit_id}_carton_${sim.damage}.jpg`);
    }

    const payload: InspectionPayload = {
      unit_id: scenario.unit_id,
      shipment_id: scenario.shipment_id || null,
      po_number: scenario.po_number,
      po_line: scenario.po_line,
      supplier: scenario.supplier,
      sku: scenario.sku,
      asin: scenario.asin,
      product_title: scenario.product_title,
      spec_colour: scenario.spec_colour,
      spec_variant: scenario.spec_variant,
      spec_components: scenario.spec_components,
      cartons_ordered: scenario.cartons_ordered,
      cartons_received: sim.cartons_received ?? scenario.cartons_ordered,
      units_per_carton_ordered: scenario.units_per_carton_ordered,
      units_per_carton_counted: sim.units_per_carton_counted ?? scenario.units_per_carton_ordered,
      photo_refs: activePhotos,
      simulate_fail_open: Boolean(sim.fail_open),
      override_identity_match: sim.id_match === 'yes' ? undefined : sim.id_match,
      override_quality_flags: sim.spec_mismatch ? ['wrong_colour', 'missing_components'] : []
    };

    try {
      const res = await runInspection(payload, orgId);
      setTestResult(res);
      onRecordCreated();
    } catch (err: any) {
      alert(`Test execution failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const structuredEvidence = testResult?.structured_evidence || (testResult?.evidence_data ? JSON.parse(testResult.evidence_data) : null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Header Banner with Honest Synthetic Evaluation Disclaimer */}
      <div className="glass-panel" style={{ padding: '20px 24px', borderLeft: '4px solid var(--accent-amber)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', padding: '8px', borderRadius: '8px' }}>
              <FlaskConical size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                Demo / Test Mode · Buildathon Challenge Presets
              </h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Deterministic Fixture Validation Suite · 11 Required Edge-Case Scenarios
              </div>
            </div>
          </div>

          <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
            DEMO MODE (Synthetic Heuristic Engine)
          </span>
        </div>

        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
          <strong>Transparency Notice:</strong> Demo Mode uses synthetic fixtures and deterministic test data when Gemini is not configured.
          The synthetic benchmark validates deterministic decision logic and system behavior; it does not establish real-world visual model accuracy.
          Judges can test each challenge condition below with 1-click or load it into the primary Receiving Station.
        </p>
      </div>

      {/* Preset Scenarios Selector Grid */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} style={{ color: 'var(--accent-amber)' }} />
          <span>Select Challenge Scenario to Test (11 Presets):</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
          {scenarios.map(s => {
            const isSelected = selectedScenarioId === s.scenario_id;
            const tag = s.scenario_tag || 'PASS';

            return (
              <div
                key={s.scenario_id}
                onClick={() => setSelectedScenarioId(s.scenario_id || 's1')}
                style={{
                  background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-tertiary)',
                  border: `1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border-color)'}`,
                  borderRadius: '8px',
                  padding: '12px 14px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: isSelected ? '#ffffff' : 'var(--text-primary)' }}>
                    {s.scenario_label}
                  </div>
                  <span
                    className={`badge ${
                      tag === 'PASS'
                        ? 'badge-pass'
                        : tag === 'FAIL'
                        ? 'badge-fail'
                        : tag === 'PENDING'
                        ? 'badge-pending'
                        : 'badge-uncertain'
                    }`}
                    style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                  >
                    {tag}
                  </span>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {s.notes}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <span className="code-font" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {s.po_number} · {s.sku}
                  </span>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                      onClick={e => {
                        e.stopPropagation();
                        onLoadInReceiving(s.po_number);
                      }}
                      title="Load in Receiving Station"
                    >
                      Station <ArrowRight size={10} />
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                      onClick={e => {
                        e.stopPropagation();
                        handleRunTest(s);
                      }}
                    >
                      <Play size={10} /> Test
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Test Execution & Detailed Diagnostic Output */}
      {activeScenario && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '20px' }}>
          
          {/* Left: Active Scenario Parameters */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>
                Scenario Profile: {activeScenario.scenario_label}
              </h3>
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                onClick={() => handleRunTest(activeScenario)}
                disabled={loading}
              >
                {loading ? <RefreshCw className="pulse-active" size={14} /> : <Play size={14} />}
                {loading ? 'Executing...' : 'Run Test Inspection'}
              </button>
            </div>

            {/* Photo preview */}
            <div style={{
              height: '180px',
              background: '#090d16',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px',
              position: 'relative'
            }}>
              <img
                src={getImageUrl(activeScenario.default_photo, orgId)}
                alt="Fixture"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onError={(e: any) => { e.target.style.display = 'none'; }}
              />
              <div style={{
                position: 'absolute',
                bottom: '6px',
                left: '6px',
                background: 'rgba(0,0,0,0.75)',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '0.65rem',
                color: '#94a3b8'
              }}>
                {activeScenario.default_photo}
              </div>
            </div>

            {/* Spec breakdown */}
            <div style={{ fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Purchase Order:</span>
                <span className="code-font" style={{ fontWeight: 600 }}>{activeScenario.po_number}</span>
              </div>
              {activeScenario.shipment_id && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Shipment ID:</span>
                  <span className="code-font" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{activeScenario.shipment_id}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Expected Product:</span>
                <span style={{ fontWeight: 600 }}>{activeScenario.product_title}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>SKU:</span>
                <span className="code-font">{activeScenario.sku}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Ordered vs Counted:</span>
                <span>
                  {activeScenario.qty_ordered} ord / {((activeScenario.sim_context?.cartons_received ?? activeScenario.cartons_ordered) * (activeScenario.sim_context?.units_per_carton_counted ?? activeScenario.units_per_carton_ordered))} cnt
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Damage Condition:</span>
                <span style={{ color: activeScenario.sim_context?.damage !== 'none' ? 'var(--accent-rose)' : 'inherit', fontWeight: 600 }}>
                  {activeScenario.sim_context?.damage || 'none'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Fail-Open Simulation:</span>
                <span style={{ color: activeScenario.sim_context?.fail_open ? 'var(--accent-purple)' : 'inherit' }}>
                  {activeScenario.sim_context?.fail_open ? 'Enabled (Timeout simulated)' : 'Disabled'}
                </span>
              </div>
            </div>

            <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: '100%', fontSize: '0.8rem', padding: '8px' }}
                onClick={() => onLoadInReceiving(activeScenario.po_number)}
              >
                Load this scenario into Receiving Station <ArrowRight size={14} />
              </button>
            </div>
          </div>

          {/* Right: Engine Diagnostic Result */}
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
              Engine Diagnostic Trace
            </h3>

            {testResult ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{
                  padding: '12px',
                  borderRadius: '8px',
                  background:
                    testResult.overall_verdict === 'PASS'
                      ? 'rgba(16, 185, 129, 0.15)'
                      : testResult.overall_verdict === 'FAIL'
                      ? 'rgba(244, 63, 94, 0.15)'
                      : testResult.overall_verdict === 'PENDING_REVIEW'
                      ? 'rgba(139, 92, 246, 0.15)'
                      : 'rgba(245, 158, 11, 0.15)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>OVERALL VERDICT</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>{testResult.overall_verdict}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CONFIDENCE</div>
                    <div className="code-font" style={{ fontSize: '1rem', fontWeight: 700 }}>
                      {Math.round((testResult.agent_confidence || 0) * 100)}%
                    </div>
                  </div>
                </div>

                {/* Individual checks list */}
                <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>5 Batch Checks:</div>
                  {structuredEvidence?.individual_checks?.map((c: any, i: number) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <span>{c.check_name}</span>
                      <span className={`badge ${c.verdict === 'PASS' ? 'badge-pass' : (c.verdict === 'FAIL' ? 'badge-fail' : 'badge-uncertain')}`} style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                        {c.verdict}
                      </span>
                    </div>
                  ))}
                </div>

                <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem' }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>Decision Rationale:</div>
                  <div style={{ color: 'var(--text-secondary)' }}>{structuredEvidence?.decision_rationale}</div>
                </div>

                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Execution Mode: <span className="code-font" style={{ color: 'var(--accent-cyan)' }}>{testResult.execution_mode}</span> ({testResult.batch_execution_time_ms}ms)
                </div>
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: '8px', minHeight: '220px' }}>
                <FlaskConical size={32} style={{ opacity: 0.3 }} />
                <div style={{ fontSize: '0.85rem' }}>Click 'Run Test Inspection' to view diagnostic trace.</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
