import React, { useState } from 'react';
import { Lock, Cpu, BookOpen, ShieldCheck, AlertTriangle, Layers } from 'lucide-react';
import { TenancySandbox } from './TenancySandbox';
import { DeliverablesHub } from './DeliverablesHub';
import { HealthStatus } from '../api';

interface Props {
  orgId: string;
  setOrgId: (orgId: string) => void;
  health: HealthStatus | null;
}

export const SettingsView: React.FC<Props> = ({ orgId, setOrgId, health }) => {
  const [subTab, setSubTab] = useState<'tenancy' | 'ai' | 'docs'>('tenancy');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Sub-navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button
          className={`btn ${subTab === 'tenancy' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('tenancy')}
        >
          <Lock size={15} /> Tenancy Security Sandbox (Rule 1)
        </button>
        <button
          className={`btn ${subTab === 'ai' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('ai')}
        >
          <Cpu size={15} /> AI Engine & Multimodal Settings
        </button>
        <button
          className={`btn ${subTab === 'docs' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.82rem', padding: '8px 14px' }}
          onClick={() => setSubTab('docs')}
        >
          <BookOpen size={15} /> Submission Deliverables
        </button>
      </div>

      {/* Sub-tab content */}
      {subTab === 'tenancy' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Active Tenant Switcher Card */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={18} style={{ color: 'var(--accent-purple)' }} />
              Active Organization (Tenant) Switcher
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              All database queries, image uploads, and inspection records enforce strict row-level security (RLS) scoped to the active tenant header.
            </p>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                type="button"
                className={`btn ${orgId === 'org_demo_alpha' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setOrgId('org_demo_alpha')}
              >
                org_demo_alpha {orgId === 'org_demo_alpha' && '✓ (Active)'}
              </button>
              <button
                type="button"
                className={`btn ${orgId === 'org_demo_bravo' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setOrgId('org_demo_bravo')}
              >
                org_demo_bravo {orgId === 'org_demo_bravo' && '✓ (Active)'}
              </button>
            </div>
          </div>

          <TenancySandbox />
        </div>
      )}

      {subTab === 'ai' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu style={{ color: 'var(--accent-cyan)' }} size={22} />
            AI Multimodal Engine Status & Configuration
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>EXECUTION MODE</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '4px' }}>
                {health?.execution_mode || 'DEMO_MODE_SYNTHETIC'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {health?.is_real_ai ? 'Real Multimodal Vision API Active' : 'Deterministic Heuristic Rule Engine Active'}
              </div>
            </div>

            <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>BATCH VISION MODEL</div>
              <div className="code-font" style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '4px', color: 'var(--accent-blue)' }}>
                {health?.batch_model || 'gemini-1.5-flash'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Single-pass unified batch vision pipeline (Rule 2)
              </div>
            </div>

            <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>FAIL-OPEN RESILIENCE</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '4px', color: '#34d399' }}>
                ENABLED & ENFORCED
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Timeouts & API errors trigger PENDING_REVIEW without blocking warehouse receiving (Rule 3)
              </div>
            </div>
          </div>

          <div style={{ marginTop: '20px', padding: '14px', borderRadius: '8px', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', fontSize: '0.8rem', lineHeight: 1.6 }}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: 'var(--text-primary)' }}>Configuration Instructions:</div>
            <div>To activate real Gemini Multimodal Vision AI:</div>
            <div className="code-font" style={{ background: 'rgba(0,0,0,0.4)', padding: '8px', borderRadius: '4px', margin: '6px 0', color: 'var(--accent-cyan)' }}>
              set GEMINI_API_KEY=your_gemini_api_key_here
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              When <code>GEMINI_API_KEY</code> is present in the backend environment, the system automatically transitions to <strong>REAL_AI_MULTIMODAL</strong> mode using Gemini 1.5 Flash. If the real API encounters a timeout or network outage, it safely fails open to <strong>PENDING_REVIEW</strong>.
            </div>
          </div>
        </div>
      )}

      {subTab === 'docs' && <DeliverablesHub />}
    </div>
  );
};
