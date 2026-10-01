import React, { useState, useEffect } from 'react';
import { fetchTenancyTest, fetchRecords } from '../api';
import { ShieldCheck, Lock, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

export const TenancySandbox: React.FC = () => {
  const [testResult, setTestResult] = useState<any>(null);
  const [alphaRecords, setAlphaRecords] = useState<any[]>([]);
  const [bravoRecords, setBravoRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const runTest = async () => {
    setLoading(true);
    try {
      const res = await fetchTenancyTest();
      setTestResult(res);
      const alpha = await fetchRecords('org_demo_alpha');
      const bravo = await fetchRecords('org_demo_bravo');
      setAlphaRecords(alpha);
      setBravoRecords(bravo);
    } catch (err: any) {
      alert('Tenancy test failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runTest();
  }, []);

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Lock style={{ color: 'var(--accent-purple)' }} size={24} />
            Engineering Rule 1: Tenancy Isolation Sandbox
          </h2>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Proves that row-level security (RLS) is forced across tenants (Org Alpha vs Org Bravo).
          </div>
        </div>

        <button className="btn btn-primary" onClick={runTest} disabled={loading}>
          <RefreshCw className={loading ? 'pulse-active' : ''} size={16} /> Run Isolation Security Test
        </button>
      </div>

      {testResult && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Isolation Status Box */}
          <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '20px', borderRadius: '10px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <ShieldCheck size={28} style={{ color: 'var(--accent-emerald)' }} />
              <div>
                <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--accent-emerald)' }}>
                  {testResult.tenancy_isolation_status}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Row-Level Security Scoped to Header & Context</div>
              </div>
            </div>

            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '12px' }}>
              <strong>Cross-Tenant Leak Test Result:</strong>
              <div className="code-font" style={{ background: 'black', padding: '10px', borderRadius: '6px', color: '#34d399', marginTop: '6px' }}>
                Target Record: {testResult.leak_test_target_record} (Belongs to Org Alpha)<br />
                Querying as Org Bravo -&gt; Result: {JSON.stringify(testResult.org_bravo_query_for_alpha_record)}<br />
                Status: {testResult.leak_result}
              </div>
            </div>
          </div>

          {/* Org Row Counts */}
          <div style={{ background: 'var(--bg-tertiary)', padding: '20px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '14px' }}>Tenant Row Isolation Breakdown</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', textAlign: 'center' }}>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>org_demo_alpha</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800 }}>{alphaRecords.length}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Scoped Rows Only</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-purple)', fontWeight: 700 }}>org_demo_bravo</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800 }}>{bravoRecords.length}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Scoped Rows Only</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
