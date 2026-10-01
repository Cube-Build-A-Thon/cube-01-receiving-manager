import React, { useState } from 'react';
import { ReceivingRecord } from '../api';
import { Search, Eye, Edit3, ShieldAlert, CheckCircle, AlertTriangle, FileText, RefreshCw, UserCheck, Shield } from 'lucide-react';

interface Props {
  records: ReceivingRecord[];
  onSelectRecord: (rec: ReceivingRecord) => void;
  onOpenOverride: (rec: ReceivingRecord) => void;
  onViewContract: (rec: ReceivingRecord) => void;
  onRetryRecord?: (rec: ReceivingRecord) => void;
}

export const HistoryTable: React.FC<Props> = ({ records, onSelectRecord, onOpenOverride, onViewContract, onRetryRecord }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('ALL');

  const filtered = records.filter(r => {
    const matchSearch = r.record_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        r.unit_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        r.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        r.supplier.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        r.po_number.toLowerCase().includes(searchTerm.toLowerCase());
    const matchVerdict = verdictFilter === 'ALL' || r.overall_verdict === verdictFilter;
    return matchSearch && matchVerdict;
  });

  const formatDate = (isoStr: string) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Receiving Inspection History & Audit Trail</h2>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Row-Level Security Scoped · Total: {filtered.length} Inbound Records Logged
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Verdict Filters */}
          <div style={{ display: 'flex', background: 'var(--bg-tertiary)', padding: '3px', borderRadius: '6px' }}>
            {['ALL', 'PASS', 'FAIL', 'UNCERTAIN', 'PENDING_REVIEW'].map(v => (
              <button
                key={v}
                onClick={() => setVerdictFilter(v)}
                style={{
                  background: verdictFilter === v ? 'var(--accent-blue)' : 'transparent',
                  color: verdictFilter === v ? 'white' : 'var(--text-muted)',
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {v}
              </button>
            ))}
          </div>

          {/* Search Bar */}
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-control"
              placeholder="Search Record, PO, SKU..."
              style={{ paddingLeft: '32px' }}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '10px' }}>Inspection ID</th>
              <th style={{ padding: '10px' }}>PO Number</th>
              <th style={{ padding: '10px' }}>SKU & Product</th>
              <th style={{ padding: '10px' }}>Date / Time</th>
              <th style={{ padding: '10px' }}>Result</th>
              <th style={{ padding: '10px' }}>Confidence</th>
              <th style={{ padding: '10px' }}>Operator Status</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(r => {
              const hasOverrides = r.audit_overrides && r.audit_overrides.length > 0;
              const confPct = Math.round((r.agent_confidence || 0) * 100);

              return (
                <tr
                  key={r.record_id}
                  onClick={() => onSelectRecord(r)}
                  style={{
                    borderBottom: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'background 0.15s'
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '10px', fontWeight: 700 }} className="code-font">
                    {r.record_id}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <div className="code-font" style={{ fontWeight: 600 }}>{r.po_number}</div>
                    {r.shipment_id && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {r.shipment_id}
                      </div>
                    )}
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{r.supplier}</div>
                  </td>
                  <td style={{ padding: '10px' }}>
                    <div className="code-font" style={{ fontWeight: 600 }}>{r.sku}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{r.product_title}</div>
                  </td>
                  <td style={{ padding: '10px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {formatDate(r.captured_at)}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                      <span className={`badge ${r.overall_verdict === 'PASS' ? 'badge-pass' : (r.overall_verdict === 'FAIL' ? 'badge-fail' : (r.overall_verdict === 'PENDING_REVIEW' ? 'badge-pending' : 'badge-uncertain'))}`}>
                        {r.overall_verdict}
                      </span>
                      {r.attempts && r.attempts.length > 1 && (
                        <span style={{ fontSize: '0.65rem', background: 'rgba(139,92,246,0.15)', color: '#c4b5fd', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>
                          Att. {r.attempts.length}
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="code-font" style={{ fontSize: '0.8rem', fontWeight: 600, color: r.overall_verdict === 'UNCERTAIN' ? '#fbbf24' : '#34d399' }}>
                        {confPct}%
                      </span>
                      <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ width: `${confPct}%`, height: '100%', background: r.overall_verdict === 'PASS' ? '#10b981' : (r.overall_verdict === 'FAIL' ? '#f43f5e' : '#f59e0b') }} />
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '10px' }}>
                    {hasOverrides ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: '#fbbf24', background: 'rgba(245,158,11,0.12)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(245,158,11,0.25)' }}>
                        <UserCheck size={12} /> Overridden ({r.audit_overrides?.length})
                      </span>
                    ) : (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        <Shield size={12} /> AI Verified
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      {(r.overall_verdict === 'PENDING_REVIEW' || r.status === 'pending_review') && onRetryRecord && (
                        <button className="btn btn-primary" style={{ padding: '4px 8px', fontSize: '0.75rem', background: '#8b5cf6' }} onClick={() => onRetryRecord(r)} title="Retry Inspection">
                          <RefreshCw size={14} /> Retry
                        </button>
                      )}
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => onSelectRecord(r)} title="Evidence Deep-Dive">
                        <Eye size={14} /> Evidence
                      </button>
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => onOpenOverride(r)} title="Log Operator Override">
                        <Edit3 size={14} /> Override
                      </button>
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => onViewContract(r)} title="Cross-Pod Contract JSON">
                        <FileText size={14} /> JSON
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No inspection records found.
        </div>
      )}
    </div>
  );
};
