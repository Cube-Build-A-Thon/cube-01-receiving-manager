import React from 'react';
import { ReceivingRecord } from '../api';
import { X, CheckCircle, AlertTriangle, HelpCircle, FileText, ArrowRight, ShieldCheck } from 'lucide-react';

interface Props {
  record: ReceivingRecord | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<Props> = ({ record, onClose }) => {
  if (!record) return null;

  let evidence: any = {};
  try {
    evidence = record.evidence_data ? JSON.parse(record.evidence_data) : {};
  } catch (e) {
    evidence = {};
  }

  const checks = evidence.checks || [
    { check_name: "Identity Match", verdict: record.identity_match === 'yes' ? 'PASS' : (record.identity_match === 'no' ? 'FAIL' : 'UNCERTAIN'), details: record.identity_match },
    { check_name: "Quantity Count", verdict: record.qty_received === record.qty_ordered ? 'PASS' : 'FAIL', details: `${record.qty_received} rec vs ${record.qty_ordered} ord` },
    { check_name: "Carton Damage", verdict: record.carton_damage === 'none' ? 'PASS' : 'FAIL', details: record.carton_damage },
    { check_name: "Unit Damage", verdict: record.unit_damage === 'none' ? 'PASS' : 'FAIL', details: record.unit_damage },
    { check_name: "Quality Spec", verdict: !record.quality_flags ? 'PASS' : 'FAIL', details: record.quality_flags || 'Matches agreed spec' }
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '850px', maxHeight: '90vh', overflowY: 'auto', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck style={{ color: 'var(--accent-blue)' }} size={24} />
              Decision Evidence & Traceability Record ({record.record_id})
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Unit: {record.unit_id} · PO: {record.po_number} · SKU: {record.sku} {record.shipment_id ? `· Shipment ID: ${record.shipment_id}` : '· Shipment ID: null'} · Tenant: {record.org_id} · Timestamp: {record.captured_at}
            </div>
          </div>
          <button className="btn btn-secondary" style={{ padding: '6px' }} onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* 6-Step Visual Pipeline Flow */}
        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '12px' }}>
            Evidence Chain of Custody (Step 01 of 5)
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', overflowX: 'auto' }}>
            <div style={{ flex: 1, background: 'var(--bg-tertiary)', padding: '10px', borderRadius: '6px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>1. RECEIVED</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>{record.qty_received} Units</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{record.cartons_received} Cartons</div>
            </div>

            <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />

            <div style={{ flex: 1, background: 'var(--bg-tertiary)', padding: '10px', borderRadius: '6px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>2. EXPECTED</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>{record.qty_ordered} Units</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{record.sku}</div>
            </div>

            <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />

            <div style={{ flex: 1, background: 'var(--bg-tertiary)', padding: '10px', borderRadius: '6px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>3. CHECKS</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>5 Batch Checks</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--accent-blue)' }}>Single-Pass</div>
            </div>

            <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />

            <div style={{ flex: 1, background: 'var(--bg-tertiary)', padding: '10px', borderRadius: '6px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>4. FINDINGS</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>{record.carton_damage !== 'none' ? record.carton_damage : 'No Damage'}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{record.quality_flags || 'No Flags'}</div>
            </div>

            <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />

            <div style={{ flex: 1, background: 'var(--bg-tertiary)', padding: '10px', borderRadius: '6px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>5. VERDICT</div>
              <span className={`badge ${record.overall_verdict === 'PASS' ? 'badge-pass' : (record.overall_verdict === 'FAIL' ? 'badge-fail' : 'badge-uncertain')}`} style={{ marginTop: '2px' }}>
                {record.overall_verdict}
              </span>
            </div>
          </div>
        </div>

        {/* Detailed Checks Grid */}
        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>6 Batch Verification Checks & Evidence Proof</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '24px' }}>
          {checks.map((c: any, idx: number) => (
            <div key={idx} style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{c.check_name}</span>
                <span className={`badge ${c.verdict === 'PASS' ? 'badge-pass' : (c.verdict === 'FAIL' ? 'badge-fail' : 'badge-uncertain')}`}>
                  {c.verdict}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{c.details}</div>
              {c.confidence && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Model Confidence: {Math.round(c.confidence * 100)}%
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Audit Overrides Section */}
        {record.audit_overrides && record.audit_overrides.length > 0 && (
          <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.3)', marginBottom: '20px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-amber)', marginBottom: '8px' }}>
              Operator Audit Override History (Engineering Rule: Overrides are data)
            </div>
            {record.audit_overrides.map((ov: any, idx: number) => (
              <div key={idx} style={{ fontSize: '0.8rem', color: 'var(--text-primary)', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px', marginBottom: '6px' }}>
                <strong>{ov.operator_id}</strong> changed overall verdict from <code>{ov.original_overall_verdict}</code> to <code>{ov.new_overall_verdict}</code> at {ov.overridden_at}.
                <br />
                <span style={{ color: 'var(--text-muted)' }}>Reason: "{ov.override_reason}"</span>
              </div>
            ))}
          </div>
        )}

        {/* Inspection Attempt Audit Trail (Priority 2) */}
        {record.attempts && record.attempts.length > 0 && (
          <div style={{ background: 'rgba(139, 92, 246, 0.08)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.25)', marginBottom: '20px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c4b5fd', marginBottom: '8px' }}>
              Inspection Attempt Audit Trail (Priority 2: Multi-Attempt Preservation)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {record.attempts.map((att: any, idx: number) => (
                <div key={idx} style={{ fontSize: '0.8rem', background: 'rgba(0,0,0,0.25)', padding: '8px 12px', borderRadius: '6px', borderLeft: `3px solid ${att.overall_verdict === 'PASS' ? '#10b981' : (att.overall_verdict === 'FAIL' ? '#f43f5e' : (att.overall_verdict === 'PENDING_REVIEW' ? '#8b5cf6' : '#f59e0b'))}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700 }}>Attempt #{att.attempt_number} — <span className="code-font">{att.overall_verdict}</span></span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{att.captured_at}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Mode: <code>{att.execution_mode}</code> {att.ai_provider ? `(${att.ai_provider})` : ''} · Confidence: {Math.round((att.agent_confidence || 0) * 100)}%
                  </div>
                  {att.decision_rationale && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                      {att.decision_rationale}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={onClose}>Close Evidence Modal</button>
        </div>
      </div>
    </div>
  );
};
