import React, { useState, useEffect } from 'react';
import { ReceivingInspectionStation } from './components/ReceivingInspectionStation';
import { HistoryTable } from './components/HistoryTable';
import { PurchaseOrdersView } from './components/PurchaseOrdersView';
import { ReportsView } from './components/ReportsView';
import { SettingsView } from './components/SettingsView';
import { DemoTestMode } from './components/DemoTestMode';
import { EvidenceModal } from './components/EvidenceModal';
import { OverrideModal } from './components/OverrideModal';
import { fetchRecords, fetchHealth, retryInspection, ReceivingRecord, HealthStatus } from './api';
import {
  Box, Camera, History, Package, BarChart3, Lock, Settings,
  Sparkles, FlaskConical, Cpu, ShieldCheck, AlertTriangle
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'receiving' | 'history' | 'purchase_orders' | 'reports' | 'settings' | 'demo'>('receiving');
  const [orgId, setOrgId] = useState('org_demo_alpha');
  const [records, setRecords] = useState<ReceivingRecord[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const [selectedRecord, setSelectedRecord] = useState<ReceivingRecord | null>(null);
  const [overrideRecord, setOverrideRecord] = useState<ReceivingRecord | null>(null);
  const [preselectedPo, setPreselectedPo] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [recs, h] = await Promise.all([
        fetchRecords(orgId).catch(() => []),
        fetchHealth().catch(() => null)
      ]);
      setRecords(recs);
      if (h) setHealth(h);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, [orgId]);

  const handleSelectPoToReceive = (poNumber: string) => {
    setPreselectedPo(poNumber);
    setActiveTab('receiving');
  };

  return (
    <div style={{ padding: '20px 24px', maxWidth: '1440px', margin: '0 auto', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header Bar */}
      <header className="glass-panel" style={{ padding: '16px 24px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', width: '42px', height: '42px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(59,130,246,0.3)' }}>
            <Box size={24} style={{ color: 'white' }} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 800, background: 'linear-gradient(135deg, #f8fafc, #cbd5e1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
              Receiving Manager
            </h1>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Point-of-Receipt Multimodal Visual Inspection & Evidence Engine · Buildathon Track 01
            </div>
          </div>
        </div>

        {/* Tenant Switcher & Real AI / Health Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-tertiary)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <Lock size={15} style={{ color: 'var(--accent-purple)' }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Active Tenant:</span>
            <select
              value={orgId}
              onChange={e => setOrgId(e.target.value)}
              className="code-font"
              style={{ background: 'transparent', color: 'var(--text-primary)', border: 'none', fontWeight: 700, cursor: 'pointer', outline: 'none', fontSize: '0.8rem' }}
            >
              <option value="org_demo_alpha" style={{ background: '#121824' }}>org_demo_alpha</option>
              <option value="org_demo_bravo" style={{ background: '#121824' }}>org_demo_bravo</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {health?.is_real_ai ? (
              <span className="badge badge-pass" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Cpu size={14} /> REAL AI: {health.batch_model}
              </span>
            ) : (
              <span className="badge" style={{ display: 'flex', alignItems: 'center', gap: '5px', background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <AlertTriangle size={14} /> DEMO MODE (Synthetic Heuristic Engine)
              </span>
            )}
            <span className="badge badge-pass" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldCheck size={14} /> RLS Forced
            </span>
          </div>
        </div>
      </header>

      {/* Main Tab Navigation */}
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '22px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { id: 'receiving', label: 'Receiving', icon: Camera },
            { id: 'history', label: `Inspection History (${records.length})`, icon: History },
            { id: 'purchase_orders', label: 'Purchase Orders', icon: Package },
            { id: 'reports', label: 'Reports', icon: BarChart3 },
            { id: 'settings', label: 'Settings', icon: Settings }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                className={`btn ${isActive ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '9px 16px', fontSize: '0.85rem' }}
                onClick={() => setActiveTab(tab.id as any)}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Separated Demo / Test Mode Action Button */}
        <div>
          <button
            className={`btn ${activeTab === 'demo' ? 'btn-primary' : 'btn-secondary'}`}
            style={{
              padding: '9px 16px',
              fontSize: '0.85rem',
              background: activeTab === 'demo' ? 'linear-gradient(135deg, #f59e0b, #d97706)' : 'rgba(245, 158, 11, 0.12)',
              color: activeTab === 'demo' ? '#ffffff' : '#fbbf24',
              borderColor: 'rgba(245, 158, 11, 0.35)'
            }}
            onClick={() => setActiveTab('demo')}
          >
            <FlaskConical size={16} />
            Demo / Test Mode
          </button>
        </div>
      </nav>

      {/* Main Tab Content */}
      <main style={{ flex: 1 }}>
        {activeTab === 'receiving' && (
          <ReceivingInspectionStation
            orgId={orgId}
            onRecordCreated={loadData}
            onOpenOverride={r => setOverrideRecord(r)}
            onViewContract={r => { setSelectedRecord(r); setActiveTab('reports'); }}
            preselectedPoNumber={preselectedPo}
          />
        )}

        {activeTab === 'history' && (
          <HistoryTable
            records={records}
            onSelectRecord={r => setSelectedRecord(r)}
            onOpenOverride={r => setOverrideRecord(r)}
            onViewContract={r => { setSelectedRecord(r); setActiveTab('reports'); }}
            onRetryRecord={async r => {
              try {
                await retryInspection(r.record_id, orgId);
                await loadData();
                alert(`Inspection retry complete for record ${r.record_id}!`);
              } catch (err: any) {
                alert(`Retry failed: ${err.message}`);
              }
            }}
          />
        )}

        {activeTab === 'purchase_orders' && (
          <PurchaseOrdersView
            orgId={orgId}
            records={records}
            onSelectPoToReceive={handleSelectPoToReceive}
          />
        )}

        {activeTab === 'reports' && (
          <ReportsView
            selectedRecord={selectedRecord || records[0] || null}
            orgId={orgId}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            orgId={orgId}
            setOrgId={setOrgId}
            health={health}
          />
        )}

        {activeTab === 'demo' && (
          <DemoTestMode
            orgId={orgId}
            onRecordCreated={loadData}
            onLoadInReceiving={handleSelectPoToReceive}
          />
        )}
      </main>

      {/* Modals */}
      <EvidenceModal record={selectedRecord} onClose={() => setSelectedRecord(null)} />
      <OverrideModal record={overrideRecord} orgId={orgId} onClose={() => setOverrideRecord(null)} onSaved={loadData} />
    </div>
  );
};
