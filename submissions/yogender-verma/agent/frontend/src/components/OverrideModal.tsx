import React, { useState } from 'react';
import { ReceivingRecord, submitOverride } from '../api';
import { X, Edit3, Save } from 'lucide-react';

interface Props {
  record: ReceivingRecord | null;
  orgId: string;
  onClose: () => void;
  onSaved: () => void;
}

export const OverrideModal: React.FC<Props> = ({ record, orgId, onClose, onSaved }) => {
  if (!record) return null;

  const [operatorId, setOperatorId] = useState('op_shift_lead');
  const [overrideReason, setOverrideReason] = useState('');
  const [identityMatch, setIdentityMatch] = useState(record.identity_match);
  const [cartonDamage, setCartonDamage] = useState(record.carton_damage);
  const [unitDamage, setUnitDamage] = useState(record.unit_damage);
  const [qualityFlags, setQualityFlags] = useState(record.quality_flags);

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideReason.trim()) {
      alert('Engineering Rule: Override reason is mandatory when altering agent decisions.');
      return;
    }
    setLoading(true);

    try {
      await submitOverride(record.record_id, orgId, {
        operator_id: operatorId,
        override_reason: overrideReason,
        identity_match: identityMatch,
        carton_damage: cartonDamage,
        unit_damage: unitDamage,
        quality_flags: qualityFlags
      });
      onSaved();
      onClose();
    } catch (err: any) {
      alert('Override error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '600px', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Edit3 style={{ color: 'var(--accent-amber)' }} size={20} />
              Operator Override Audit Drawer ({record.record_id})
            </h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Honesty Rule: Overrides are data. Original verdicts are preserved permanently.
            </div>
          </div>
          <button className="btn btn-secondary" style={{ padding: '6px' }} onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Operator ID</label>
              <input type="text" className="form-control" value={operatorId} onChange={e => setOperatorId(e.target.value)} required />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Identity Match</label>
              <select className="form-control" value={identityMatch} onChange={e => setIdentityMatch(e.target.value)}>
                <option value="yes">yes (PASS)</option>
                <option value="no">no (FAIL)</option>
                <option value="uncertain">uncertain (UNCERTAIN)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Carton Damage</label>
              <select className="form-control" value={cartonDamage} onChange={e => setCartonDamage(e.target.value)}>
                <option value="none">none</option>
                <option value="crushing">crushing</option>
                <option value="water">water</option>
                <option value="tears">tears</option>
                <option value="uncertain">uncertain</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Unit Damage</label>
              <select className="form-control" value={unitDamage} onChange={e => setUnitDamage(e.target.value)}>
                <option value="none">none</option>
                <option value="crushing">crushing</option>
                <option value="water">water</option>
                <option value="tears">tears</option>
                <option value="uncertain">uncertain</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Quality Flags</label>
            <input type="text" className="form-control" placeholder="e.g. wrong_colour;missing_components" value={qualityFlags} onChange={e => setQualityFlags(e.target.value)} />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-amber)' }}>
              Mandatory Override Justification Reason *
            </label>
            <textarea
              className="form-control"
              rows={3}
              placeholder="Explain why operator judgment differs from automated vision decision (e.g. Supplier confirmed replacement shipment attached)."
              value={overrideReason}
              onChange={e => setOverrideReason(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <Save size={16} /> {loading ? 'Logging Override...' : 'Commit Audit Override'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
