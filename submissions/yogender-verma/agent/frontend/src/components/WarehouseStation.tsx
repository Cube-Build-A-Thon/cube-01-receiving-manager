import React, { useState } from 'react';
import {
  Camera, RefreshCw, AlertTriangle, CheckCircle, ShieldAlert, Layers, Box, Cpu,
  FileText, Upload, Sparkles, HelpCircle, ArrowRight, ShieldCheck, ChevronRight
} from 'lucide-react';
import { runInspection, uploadPhoto, retryInspection, InspectionPayload } from '../api';

interface Props {
  orgId: string;
  onRecordCreated: () => void;
}

const PRESET_SCENARIOS = [
  {
    id: 's1',
    label: '1. Correct Shipment',
    tag: 'PASS',
    unitId: 'UNIT-0101',
    po: 'PO-1001',
    sku: 'BLUE-BOTTLE-001',
    title: 'Blue Stainless Steel Bottle',
    colour: 'Blue',
    variant: 'Standard',
    components: 'bottle; lid',
    cartonsOrd: 2,
    cartonsRec: 2,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/clean_pallet.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's2',
    label: '2. Short Shipment (-4 Units)',
    tag: 'FAIL',
    unitId: 'UNIT-0102',
    po: 'PO-1002',
    sku: 'BLUE-BOTTLE-001',
    title: 'Blue Stainless Steel Bottle',
    colour: 'Blue',
    variant: 'Standard',
    components: 'bottle; lid',
    cartonsOrd: 2,
    cartonsRec: 2,
    unitsOrd: 12,
    unitsCnt: 10,
    photo: 'fixtures/receiving/short_shipment.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's3',
    label: '3. Extra Units (+4 Over)',
    tag: 'FAIL',
    unitId: 'UNIT-0103',
    po: 'PO-1003',
    sku: 'BLUE-BOTTLE-001',
    title: 'Blue Stainless Steel Bottle',
    colour: 'Blue',
    variant: 'Standard',
    components: 'bottle; lid',
    cartonsOrd: 2,
    cartonsRec: 2,
    unitsOrd: 12,
    unitsCnt: 14,
    photo: 'fixtures/receiving/extra_units.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's4',
    label: '4. Wrong SKU Contradiction',
    tag: 'FAIL',
    unitId: 'UNIT-0104',
    po: 'PO-1004',
    sku: 'BLUE-BOTTLE-001',
    title: 'Blue Stainless Steel Bottle',
    colour: 'Blue',
    variant: 'Standard',
    components: 'bottle; lid',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/wrong_sku.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: false,
    idMatch: 'no'
  },
  {
    id: 's5',
    label: '5. Wrong Variant / Colour',
    tag: 'FAIL',
    unitId: 'UNIT-0105',
    po: 'PO-1005',
    sku: 'BLUE-BOTTLE-001',
    title: 'Blue Stainless Steel Bottle',
    colour: 'Blue',
    variant: 'Standard',
    components: 'bottle; lid',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/red_variant.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: true,
    idMatch: 'yes'
  },
  {
    id: 's6',
    label: '6. Crushed Carton',
    tag: 'FAIL',
    unitId: 'UNIT-0106',
    po: 'PO-1006',
    sku: 'CANDLE-3PK',
    title: 'Soy Candle Set 3-Pack',
    colour: 'Cream',
    variant: '3-pack',
    components: 'candles x3; gift box',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 6,
    unitsCnt: 6,
    photo: 'fixtures/receiving/pallet_crushing.jpg',
    failOpen: false,
    damage: 'crushing',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's7',
    label: '7. Water Damaged Carton',
    tag: 'FAIL',
    unitId: 'UNIT-0107',
    po: 'PO-1007',
    sku: 'CANDLE-3PK',
    title: 'Soy Candle Set 3-Pack',
    colour: 'Cream',
    variant: '3-pack',
    components: 'candles x3; gift box',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 6,
    unitsCnt: 6,
    photo: 'fixtures/receiving/carton_water_soaked.jpg',
    failOpen: false,
    damage: 'water',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's8',
    label: '8. Torn Outer Packaging',
    tag: 'FAIL',
    unitId: 'UNIT-0108',
    po: 'PO-1008',
    sku: 'TOWEL-BLU',
    title: 'Cotton Bath Towel',
    colour: 'Blue',
    variant: 'Bath',
    components: 'towel',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/packaging_tears.jpg',
    failOpen: false,
    damage: 'tears',
    specMismatch: false,
    idMatch: 'yes'
  },
  {
    id: 's9',
    label: '9. Missing Components (No Scoop)',
    tag: 'FAIL',
    unitId: 'UNIT-0109',
    po: 'PO-1009',
    sku: 'PROT-1KG',
    title: 'Whey Protein Tub',
    colour: 'n/a',
    variant: '1kg Vanilla',
    components: 'tub; scoop',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/missing_scoop.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: true,
    idMatch: 'yes'
  },
  {
    id: 's10',
    label: '10. Ambiguous (UNCERTAIN)',
    tag: 'UNCERTAIN',
    unitId: 'UNIT-0110',
    po: 'PO-1010',
    sku: 'SERUM-30ML',
    title: 'Vitamin C Facial Serum',
    colour: 'Amber',
    variant: '30ml',
    components: 'bottle; dropper',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/blur_dark_occluded.jpg',
    failOpen: false,
    damage: 'none',
    specMismatch: false,
    idMatch: 'uncertain'
  },
  {
    id: 's11',
    label: '11. Model Timeout (Fail-Open)',
    tag: 'PENDING',
    unitId: 'UNIT-0111',
    po: 'PO-1011',
    sku: 'LAMP-LED',
    title: 'LED Desk Lamp',
    colour: 'White',
    variant: 'Standard',
    components: 'lamp; power adapter',
    cartonsOrd: 1,
    cartonsRec: 1,
    unitsOrd: 12,
    unitsCnt: 12,
    photo: 'fixtures/receiving/lamp.jpg',
    failOpen: true,
    damage: 'none',
    specMismatch: false,
    idMatch: 'yes'
  }
];

export const WarehouseStation: React.FC<Props> = ({ orgId, onRecordCreated }) => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>('s1');
  const [unitId, setUnitId] = useState('UNIT-0101');
  const [poNumber, setPoNumber] = useState('PO-1001');
  const [supplier, setSupplier] = useState('Supplier East');
  const [sku, setSku] = useState('BLUE-BOTTLE-001');
  const [asin, setAsin] = useState('B0DUMMY600');
  const [productTitle, setProductTitle] = useState('Blue Stainless Steel Bottle');
  const [specColour, setSpecColour] = useState('Blue');
  const [specVariant, setSpecVariant] = useState('Standard');
  const [specComponents, setSpecComponents] = useState('bottle; lid');

  const [cartonsOrdered, setCartonsOrdered] = useState(2);
  const [cartonsReceived, setCartonsReceived] = useState(2);
  const [unitsPerCartonOrdered, setUnitsPerCartonOrdered] = useState(12);
  const [unitsPerCartonCounted, setUnitsPerCartonCounted] = useState(12);

  const [photoRefs, setPhotoRefs] = useState<string[]>(['fixtures/receiving/clean_pallet.jpg']);
  const [simFailOpen, setSimFailOpen] = useState(false);
  const [simDamage, setSimDamage] = useState<'none' | 'crushing' | 'water' | 'tears' | 'blur'>('none');
  const [simSpecMismatch, setSimSpecMismatch] = useState(false);
  const [overrideIdentity, setOverrideIdentity] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const handleApplyPreset = (preset: typeof PRESET_SCENARIOS[0]) => {
    setSelectedPresetId(preset.id);
    setUnitId(preset.unitId);
    setPoNumber(preset.po);
    setSku(preset.sku);
    setProductTitle(preset.title);
    setSpecColour(preset.colour);
    setSpecVariant(preset.variant);
    setSpecComponents(preset.components);
    setCartonsOrdered(preset.cartonsOrd);
    setCartonsReceived(preset.cartonsRec);
    setUnitsPerCartonOrdered(preset.unitsOrd);
    setUnitsPerCartonCounted(preset.unitsCnt);
    setPhotoRefs([preset.photo]);
    setSimFailOpen(preset.failOpen);
    setSimDamage(preset.damage as any);
    setSimSpecMismatch(preset.specMismatch);
    setOverrideIdentity(preset.idMatch === 'yes' ? null : preset.idMatch);
    setLastResult(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploading(true);
    try {
      const res = await uploadPhoto(file, orgId);
      setPhotoRefs([res.relative_path]);
      alert(`Photo uploaded securely to tenant storage: ${res.filename}`);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    let activePhotos = [...photoRefs];
    if (simDamage !== 'none' && !activePhotos[0].includes(simDamage)) {
      activePhotos.push(`fixtures/receiving/${unitId}_carton_${simDamage}.jpg`);
    }

    const payload: InspectionPayload = {
      unit_id: unitId,
      po_number: poNumber,
      po_line: 1,
      supplier,
      sku,
      asin,
      product_title: productTitle,
      spec_colour: specColour,
      spec_variant: specVariant,
      spec_components: specComponents,
      cartons_ordered: cartonsOrdered,
      cartons_received: cartonsReceived,
      units_per_carton_ordered: unitsPerCartonOrdered,
      units_per_carton_counted: unitsPerCartonCounted,
      photo_refs: activePhotos,
      simulate_fail_open: simFailOpen,
      override_identity_match: overrideIdentity || undefined,
      override_quality_flags: simSpecMismatch ? ['wrong_colour', 'missing_components'] : []
    };

    try {
      const res = await runInspection(payload, orgId);
      setLastResult(res);
      onRecordCreated();
    } catch (err: any) {
      alert('Inspection error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!lastResult || !lastResult.record_id) return;
    setLoading(true);
    try {
      const res = await retryInspection(lastResult.record_id, orgId);
      setLastResult(res);
      onRecordCreated();
      alert(`Record ${res.record_id} successfully reprocessed from fail-open!`);
    } catch (err: any) {
      alert('Retry failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Parse structured evidence if available
  const structuredEvidence = lastResult?.structured_evidence || (lastResult?.evidence_data ? JSON.parse(lastResult.evidence_data) : null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Scenario Quick-Loader Bar */}
      <div className="glass-panel" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} style={{ color: 'var(--accent-amber)' }} />
            <span style={{ fontSize: '0.9rem', fontWeight: 700 }}>Evaluation Scenario Quick-Load:</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Click to load any of the 11 required CUBE buildathon test scenarios</span>
          </div>
          <span className="badge badge-pass" style={{ fontSize: '0.7rem' }}>
            Deterministic Test Fixtures Active
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {PRESET_SCENARIOS.map(p => (
            <button
              key={p.id}
              type="button"
              onClick={() => handleApplyPreset(p)}
              style={{
                background: selectedPresetId === p.id ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
                color: selectedPresetId === p.id ? '#ffffff' : 'var(--text-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 1fr', gap: '20px' }}>
        {/* Left Column: Dock Station Input & Image Capture Form */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Camera style={{ color: 'var(--accent-blue)' }} size={24} />
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Point-of-Receipt Station</h2>
            </div>
            <span className="badge badge-pass" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Cpu size={14} /> Batch Single-Pass Active
            </span>
          </div>

          <form onSubmit={handleInspect}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Unit ID</label>
                <input type="text" className="form-control code-font" value={unitId} onChange={e => setUnitId(e.target.value)} required />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Purchase Order (PO)</label>
                <input type="text" className="form-control code-font" value={poNumber} onChange={e => setPoNumber(e.target.value)} required />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>SKU (Expected)</label>
                <input type="text" className="form-control code-font" value={sku} onChange={e => setSku(e.target.value)} required />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Product Title</label>
                <input type="text" className="form-control" value={productTitle} onChange={e => setProductTitle(e.target.value)} required />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '12px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Spec Colour</label>
                <input type="text" className="form-control" value={specColour} onChange={e => setSpecColour(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Spec Variant</label>
                <input type="text" className="form-control" value={specVariant} onChange={e => setSpecVariant(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Spec Components</label>
                <input type="text" className="form-control" value={specComponents} onChange={e => setSpecComponents(e.target.value)} />
              </div>
            </div>

            {/* Quantity Arithmetic Card */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', marginBottom: '14px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span>Quantity Math (Expected vs Counted)</span>
                <span className="code-font" style={{ color: cartonsReceived * unitsPerCartonCounted !== cartonsOrdered * unitsPerCartonOrdered ? 'var(--accent-rose)' : '#34d399' }}>
                  Total: {cartonsReceived * unitsPerCartonCounted} / {cartonsOrdered * unitsPerCartonOrdered} units
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Ctns Ord</span>
                  <input type="number" className="form-control" value={cartonsOrdered} onChange={e => setCartonsOrdered(Number(e.target.value))} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Ctns Rec</span>
                  <input type="number" className="form-control" value={cartonsReceived} onChange={e => setCartonsReceived(Number(e.target.value))} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Units/Ctn (Ord)</span>
                  <input type="number" className="form-control" value={unitsPerCartonOrdered} onChange={e => setUnitsPerCartonOrdered(Number(e.target.value))} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Units/Ctn (Cnt)</span>
                  <input type="number" className="form-control" value={unitsPerCartonCounted} onChange={e => setUnitsPerCartonCounted(Number(e.target.value))} />
                </div>
              </div>
            </div>

            {/* Photo Capture & Upload */}
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', marginBottom: '14px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)' }}>Photo Evidence ({photoRefs.length} attached)</span>
                <label className="btn btn-secondary" style={{ padding: '3px 8px', fontSize: '0.72rem', cursor: 'pointer' }}>
                  <Upload size={12} /> {uploading ? 'Uploading...' : 'Upload Real Image'}
                  <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileUpload} style={{ display: 'none' }} />
                </label>
              </div>
              <div className="code-font" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                {photoRefs.join('; ')}
              </div>
            </div>

            {/* Simulation Toggles */}
            <div style={{ background: 'rgba(0,0,0,0.15)', padding: '10px', borderRadius: '6px', marginBottom: '16px', border: '1px dashed var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>Rule Verification Overrides:</div>
              <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', fontSize: '0.75rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="checkbox" checked={simFailOpen} onChange={e => setSimFailOpen(e.target.checked)} />
                  <span>Rule 3 Timeout (Fail-Open)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="checkbox" checked={simSpecMismatch} onChange={e => setSimSpecMismatch(e.target.checked)} />
                  <span>Spec Quality Mismatch</span>
                </label>
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px' }} disabled={loading}>
              {loading ? <RefreshCw className="pulse-active" size={18} /> : <Camera size={18} />}
              {loading ? 'Executing Single-Pass Batch Inspection...' : 'Capture & Execute Batch Agent Inspection'}
            </button>
          </form>
        </div>

        {/* Right Column: Live Decision, Structured Verdict & Visual Evidence */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Box style={{ color: 'var(--accent-purple)' }} size={22} />
              Inspection Decision & Evidence
            </h2>
            {lastResult && (
              <span className="code-font" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {lastResult.batch_execution_time_ms}ms · {Math.round((lastResult.agent_confidence || 0) * 100)}% Conf
              </span>
            )}
          </div>

          {/* Evidence Image Viewer with Bounding Box Overlay */}
          <div style={{
            position: 'relative',
            height: '220px',
            background: '#090d16',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            marginBottom: '16px'
          }}>
            {photoRefs[0] && (
              <img
                src={`${(import.meta.env.VITE_API_BASE_URL || '')}/api/${photoRefs[0].replace('fixtures/', 'fixtures/')}`}
                alt="Receiving evidence"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onError={(e: any) => {
                  e.target.style.display = 'none';
                }}
              />
            )}

            {/* Watermark Tag */}
            <div style={{
              position: 'absolute',
              top: '8px',
              left: '8px',
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(255,255,255,0.1)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.68rem',
              color: '#94a3b8'
            }}>
              DEMO / SYNTHETIC FIXTURE · DOCK CAMERA 01
            </div>

            {/* Bounding Box Visual Overlay if Result Available */}
            {lastResult && lastResult.overall_verdict !== 'PENDING_REVIEW' && (
              <div style={{
                position: 'absolute',
                top: '25px',
                left: '25px',
                right: '25px',
                bottom: '25px',
                border: `2px dashed ${lastResult.overall_verdict === 'PASS' ? '#10b981' : (lastResult.overall_verdict === 'FAIL' ? '#f43f5e' : '#f59e0b')}`,
                borderRadius: '6px',
                pointerEvents: 'none',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'flex-end',
                padding: '6px'
              }}>
                <span className={`badge ${lastResult.overall_verdict === 'PASS' ? 'badge-pass' : (lastResult.overall_verdict === 'FAIL' ? 'badge-fail' : 'badge-uncertain')}`} style={{ fontSize: '0.68rem' }}>
                  {lastResult.overall_decision || lastResult.overall_verdict}
                </span>
              </div>
            )}
          </div>

          {/* Decision Outcome Card */}
          {lastResult ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Overall Decision Banner */}
              <div style={{
                padding: '12px 16px',
                borderRadius: '8px',
                background: lastResult.overall_decision === 'PASS' ? 'rgba(16, 185, 129, 0.12)' : (lastResult.overall_decision === 'EXCEPTION' || lastResult.overall_verdict === 'FAIL' ? 'rgba(244, 63, 94, 0.15)' : (lastResult.overall_verdict === 'PENDING_REVIEW' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(245, 158, 11, 0.15)')),
                border: `1px solid ${lastResult.overall_decision === 'PASS' ? 'rgba(16, 185, 129, 0.3)' : (lastResult.overall_decision === 'EXCEPTION' || lastResult.overall_verdict === 'FAIL' ? 'rgba(244, 63, 94, 0.4)' : (lastResult.overall_verdict === 'PENDING_REVIEW' ? 'rgba(139, 92, 246, 0.3)' : 'rgba(245, 158, 11, 0.3)'))}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
                    Overall Receiving Decision
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                    {lastResult.overall_decision || (lastResult.overall_verdict === 'FAIL' ? 'EXCEPTION' : lastResult.overall_verdict)}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span className={`badge ${lastResult.overall_verdict === 'PASS' ? 'badge-pass' : (lastResult.overall_verdict === 'FAIL' ? 'badge-fail' : (lastResult.overall_verdict === 'PENDING_REVIEW' ? 'badge-pending' : 'badge-uncertain'))}`}>
                    {lastResult.overall_verdict}
                  </span>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {lastResult.record_id}
                  </div>
                </div>
              </div>

              {/* Individual Checks Table */}
              <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: '8px', padding: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>Individual Inspection Checks:</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '6px', fontSize: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '4px', fontWeight: 600, color: 'var(--text-muted)' }}>
                  <div>Check Name</div>
                  <div>Observed</div>
                  <div>Verdict</div>
                </div>

                {structuredEvidence?.individual_checks?.map((c: any, i: number) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '6px', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', alignItems: 'center' }}>
                    <div style={{ fontWeight: 600 }}>{c.check_name}</div>
                    <div className="code-font" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{String(c.observed_value).slice(0, 18)}</div>
                    <div>
                      <span className={`badge ${c.verdict === 'PASS' ? 'badge-pass' : (c.verdict === 'FAIL' ? 'badge-fail' : (c.verdict === 'PENDING' ? 'badge-pending' : 'badge-uncertain'))}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                        {c.verdict}
                      </span>
                    </div>
                  </div>
                )) || (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '6px 0' }}>
                    Identity: {lastResult.identity_match} | Qty: {lastResult.qty_received}/{lastResult.qty_ordered} | Carton: {lastResult.carton_damage} | Spec: {lastResult.quality_flags || 'Confirmed'}
                  </div>
                )}
              </div>

              {/* Why / Explanation Section */}
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', fontSize: '0.78rem' }}>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2px' }}>Why:</div>
                <div style={{ color: 'var(--text-secondary)' }}>
                  {structuredEvidence?.decision_rationale || `Inspection evaluated with ${Math.round((lastResult.agent_confidence || 0) * 100)}% confidence.`}
                </div>

                {structuredEvidence?.uncertain_explanation && (
                  <div style={{ marginTop: '8px', padding: '6px 8px', background: 'rgba(245, 158, 11, 0.1)', borderLeft: '3px solid #f59e0b', borderRadius: '2px' }}>
                    <div style={{ fontWeight: 700, color: '#fbbf24' }}>Uncertainty Cause:</div>
                    <div style={{ color: '#fde68a', fontSize: '0.72rem' }}>{structuredEvidence.uncertain_explanation}</div>
                    <div style={{ fontWeight: 700, color: '#fbbf24', marginTop: '4px' }}>Recommended Next Evidence:</div>
                    <div style={{ color: '#fde68a', fontSize: '0.72rem' }}>{structuredEvidence.recommended_next_evidence}</div>
                  </div>
                )}

                {lastResult.overall_verdict === 'PENDING_REVIEW' && (
                  <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: '#c084fc', fontSize: '0.75rem' }}>Fail-Open Active · Operations not blocked</span>
                    <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={handleRetry}>
                      <RefreshCw size={12} /> Retry Inspection
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', gap: '8px' }}>
              <Layers size={36} style={{ opacity: 0.25 }} />
              <div>Ready for shipment intake.</div>
              <div style={{ fontSize: '0.75rem' }}>Select a scenario preset above or click 'Capture & Execute Batch Agent Inspection'.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
