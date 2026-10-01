import React, { useState, useEffect } from 'react';
import { fetchContract, fetchAuthoritativeRules, ReceivingRecord } from '../api';
import { FileText, Copy, Check, ExternalLink, ShieldAlert } from 'lucide-react';

interface Props {
  selectedRecord: ReceivingRecord | null;
  orgId: string;
}

export const ContractViewer: React.FC<Props> = ({ selectedRecord, orgId }) => {
  const [contractJson, setContractJson] = useState<any>(null);
  const [authoritativeRules, setAuthoritativeRules] = useState<any[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (selectedRecord) {
      fetchContract(selectedRecord.record_id, orgId).then(setContractJson).catch(console.error);
    }
    fetchAuthoritativeRules().then(setAuthoritativeRules).catch(console.error);
  }, [selectedRecord, orgId]);

  const handleCopy = () => {
    if (contractJson) {
      navigator.clipboard.writeText(JSON.stringify(contractJson, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
      {/* Left: Standard JSON Contract Output */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText style={{ color: 'var(--accent-blue)' }} size={20} />
              Cross-Pod Evidence Contract Output (Step 01 -&gt; Step 02 &amp; 05)
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Target: {selectedRecord ? selectedRecord.record_id : 'Select record from History'}
            </div>
          </div>

          <button className="btn btn-secondary" onClick={handleCopy} disabled={!contractJson}>
            {copied ? <Check size={16} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={16} />}
            {copied ? 'Copied JSON' : 'Copy Contract JSON'}
          </button>
        </div>

        {contractJson ? (
          <pre className="code-font" style={{
            background: 'black',
            color: '#38bdf8',
            padding: '16px',
            borderRadius: '8px',
            fontSize: '0.78rem',
            maxHeight: '520px',
            overflowY: 'auto',
            border: '1px solid var(--border-color)'
          }}>
            {JSON.stringify(contractJson, null, 2)}
          </pre>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Select any record from History tab to inspect its standardized evidence contract JSON.
          </div>
        )}
      </div>

      {/* Right: Authoritative Rules Lookup (Engineering Rule 5) */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert style={{ color: 'var(--accent-amber)' }} size={20} />
          Authoritative Channel Rules Registry (Rule 5)
        </h2>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Authoritative rules retrieved directly from channel policy specifications instead of memory/dummy examples.
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {authoritativeRules.map((cat: any, idx: number) => (
            <div key={idx} style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '6px' }}>
                {cat.channel} · {cat.doc_title}
              </div>

              {cat.rules.map((r: any, rIdx: number) => (
                <div key={rIdx} style={{ fontSize: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px', marginTop: '6px' }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.rule_id}: {r.name}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>{r.condition}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--accent-rose)', marginTop: '2px' }}>Action: {r.action_on_violation}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
