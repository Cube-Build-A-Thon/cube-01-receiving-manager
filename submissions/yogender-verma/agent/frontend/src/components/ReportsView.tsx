import React, { useState, useEffect } from 'react';
import { BarChart3, FileText, ShieldCheck, Activity, RefreshCw, Info, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { EvalDashboard } from './EvalDashboard';
import { ContractViewer } from './ContractViewer';
import { fetchAuthoritativeRules, fetchLiveMetrics, ReceivingRecord } from '../api';

interface Props {
  selectedRecord: ReceivingRecord | null;
  orgId: string;
}

export const ReportsView: React.FC<Props> = ({ selectedRecord, orgId }) => {
  const [subTab, setSubTab] = useState<'live' | 'eval' | 'contract' | 'rules'>('live');
  const [rules, setRules] = useState<any[]>([]);
  const [liveMetrics, setLiveMetrics] = useState<any>(null);
  const [loadingLive, setLoadingLive] = useState<boolean>(false);

  const loadLiveMetrics = async () => {
    setLoadingLive(true);
    try {
      const data = await fetchLiveMetrics(orgId);
      setLiveMetrics(data);
    } catch (err) {
      console.error('Failed to load live operational metrics:', err);
    } finally {
      setLoadingLive(false);
    }
  };

  useEffect(() => {
    loadLiveMetrics();
    fetchAuthoritativeRules()
      .then(res => {
        if (Array.isArray(res)) setRules(res);
      })
      .catch(() => {});
  }, [orgId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Sub-navigation tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button
          className={`btn ${subTab === 'live' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => { setSubTab('live'); loadLiveMetrics(); }}
        >
          <Activity size={15} /> Live Operational Metrics
        </button>
        <button
          className={`btn ${subTab === 'eval' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('eval')}
        >
          <BarChart3 size={15} /> Synthetic Evaluation
        </button>
        <button
          className={`btn ${subTab === 'contract' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('contract')}
        >
          <FileText size={15} /> Cross-Pod Evidence Contract JSON
        </button>
        <button
          className={`btn ${subTab === 'rules' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('rules')}
        >
          <ShieldCheck size={15} /> Authoritative Channel Rules
        </button>
      </div>

      {/* Sub-tab content: Live Operational Metrics */}
      {subTab === 'live' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header & Refresh */}
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Activity style={{ color: 'var(--accent-cyan)' }} size={22} />
                Live Operational Metrics &amp; Uncertain Rate
              </h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Computed dynamically from active point-of-receipt intake records in SQLite database for tenant: <strong style={{ color: 'var(--text-primary)' }}>{orgId}</strong>
              </div>
            </div>

            <button className="btn btn-secondary" onClick={loadLiveMetrics} disabled={loadingLive}>
              <RefreshCw className={loadingLive ? 'pulse-active' : ''} size={15} /> Refresh Metrics
            </button>
          </div>

          {liveMetrics && (
            <>
              {/* Stat Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL INTAKE</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-primary)' }}>{liveMetrics.total_inspections}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>All Inbound Units</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>COMPLETED</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-blue)' }}>{liveMetrics.completed_inspections}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Evaluated Units</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>PASS COUNT</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>{liveMetrics.pass_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Verified Clean</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>FAIL COUNT</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-rose)' }}>{liveMetrics.fail_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Discrepancies / Damage</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>UNCERTAIN COUNT</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-amber)' }}>{liveMetrics.uncertain_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Insufficient Proof</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>PENDING REVIEW</div>
                  <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#8b5cf6' }}>{liveMetrics.pending_review_count}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Fail-Open Holds</div>
                </div>
              </div>

              {/* Uncertain Rate Deep Dive Card */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                  <div style={{ flex: 1, minWidth: '280px' }}>
                    <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.5px' }}>
                      Live Operational Uncertainty Rate
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginTop: '6px' }}>
                      <span className="code-font" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent-amber)' }}>
                        {liveMetrics.uncertain_rate_pct}%
                      </span>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        ({liveMetrics.uncertain_count} of {liveMetrics.completed_inspections} completed inspections)
                      </span>
                    </div>

                    <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', margin: '14px 0' }}>
                      <div style={{ width: `${Math.min(liveMetrics.uncertain_rate_pct, 100)}%`, height: '100%', background: '#f59e0b', borderRadius: '4px' }} />
                    </div>
                  </div>

                  {/* Policy Definition Box */}
                  <div style={{ flex: 1, minWidth: '320px', background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Info size={16} /> Operational Definition &amp; Formula
                    </div>
                    <div className="code-font" style={{ fontSize: '0.78rem', color: 'var(--text-primary)', marginBottom: '8px', background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: '4px' }}>
                      {liveMetrics.formula}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      <strong>Denominator Rule:</strong> {liveMetrics.denominator_policy}.
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                      Note: No arbitrary target percentage or pass/fail threshold is imposed. This reports genuine operational visibility at the dock.
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Sub-tab content: Synthetic Evaluation */}
      {subTab === 'eval' && (
        <div>
          <div style={{ background: 'rgba(59, 130, 246, 0.08)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)', marginBottom: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--accent-blue)' }}>Synthetic Evaluation Methodology Notice:</strong> These metrics reflect execution across 50 deterministic synthetic fixtures with dual programmatic consensus labels to validate Cohen's Kappa scoring formula and rule enforcement. They are separate from the Live Operational Metrics above.
          </div>
          <EvalDashboard />
        </div>
      )}

      {/* Sub-tab content: Contract JSON */}
      {subTab === 'contract' && (
        <ContractViewer selectedRecord={selectedRecord} orgId={orgId} />
      )}

      {/* Sub-tab content: Authoritative Rules */}
      {subTab === 'rules' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ marginBottom: '18px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck style={{ color: 'var(--accent-emerald)' }} size={22} />
              Authoritative Logistics Channel Compliance Rules (Rule 5)
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Standard operating procedures for Amazon FBA and Global 3PL cross-dock compliance.
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px' }}>Rule ID</th>
                  <th style={{ padding: '10px' }}>Channel</th>
                  <th style={{ padding: '10px' }}>Rule Name</th>
                  <th style={{ padding: '10px' }}>Description</th>
                  <th style={{ padding: '10px' }}>Authoritative Reference</th>
                  <th style={{ padding: '10px' }}>Pass Criteria</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px', fontWeight: 700 }} className="code-font">{r.rule_id}</td>
                    <td style={{ padding: '10px' }}>
                      <span className="badge" style={{ background: 'rgba(59,130,246,0.15)', color: '#60a5fa' }}>
                        {r.channel}
                      </span>
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{r.rule_name}</td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{r.description}</td>
                    <td className="code-font" style={{ padding: '10px', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
                      {r.authoritative_ref}
                    </td>
                    <td className="code-font" style={{ padding: '10px', fontSize: '0.75rem', color: '#34d399' }}>
                      {r.pass_criteria}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
