import React, { useState, useEffect, useRef } from 'react';
import {
  Camera, CheckCircle, AlertTriangle, HelpCircle, ShieldAlert,
  ArrowRight, Upload, RefreshCw, Box, ShieldCheck, Cpu,
  FileText, Edit3, Image as ImageIcon, Check, ChevronDown,
  Layers, Package, AlertCircle, Info, ExternalLink, Trash2,
  Plus, History
} from 'lucide-react';
import { runInspection, uploadPhoto, retryInspection, reinspectWithEvidence, fetchRecordAttempts, InspectionPayload, ReceivingRecord } from '../api';
import { PURCHASE_ORDERS_CATALOG, PurchaseOrderItem, getPurchaseOrders } from '../data/purchaseOrders';

interface Props {
  orgId: string;
  onRecordCreated: () => void;
  onOpenOverride?: (record: any) => void;
  onViewContract?: (record: any) => void;
  preselectedPoNumber?: string | null;
}

const BACKEND_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function getImageUrl(photoRef: string, orgId: string): string {
  if (!photoRef) return '';
  if (photoRef.startsWith('http://') || photoRef.startsWith('https://') || photoRef.startsWith('blob:')) {
    return photoRef;
  }
  const clean = photoRef.replace(/\\/g, '/');
  if (clean.includes('/images/')) {
    return `${BACKEND_BASE}${clean.startsWith('/') ? '' : '/'}${clean}?org_id=${orgId}`;
  }
  if (clean.startsWith('fixtures/org_') || clean.startsWith('org_')) {
    const parts = clean.split('/');
    const fileOrg = parts[parts.length - 2] || orgId;
    const filename = parts[parts.length - 1];
    return `${BACKEND_BASE}/api/images/${fileOrg}/${filename}?org_id=${orgId}`;
  }
  if (clean.startsWith('fixtures/')) {
    return `${BACKEND_BASE}/api/${clean}`;
  }
  return `${BACKEND_BASE}/api/fixtures/receiving/${clean}`;
}

export const ReceivingInspectionStation: React.FC<Props> = ({
  orgId,
  onRecordCreated,
  onOpenOverride,
  onViewContract,
  preselectedPoNumber
}) => {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrderItem[]>(PURCHASE_ORDERS_CATALOG);
  const [selectedPoNumber, setSelectedPoNumber] = useState<string>('PO-1001');
  const [activePo, setActivePo] = useState<PurchaseOrderItem | null>(PURCHASE_ORDERS_CATALOG[0]);
  const [searchPoTerm, setSearchPoTerm] = useState<string>('');

  // Receiving Photos state
  const [photoRefs, setPhotoRefs] = useState<string[]>(['fixtures/receiving/clean_pallet.jpg']);
  const [uploading, setUploading] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Inspection states
  const [loading, setLoading] = useState<boolean>(false);
  const [progressState, setProgressState] = useState<string>('');
  const [lastResult, setLastResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Additional evidence workflow (Priority 7)
  const [additionalPhotoRefs, setAdditionalPhotoRefs] = useState<string[]>([]);
  const [additionalNotes, setAdditionalNotes] = useState<string>('');
  const [reinspecting, setReinspecting] = useState<boolean>(false);

  // Selected bounding box highlight
  const [highlightedCheck, setHighlightedCheck] = useState<string | null>(null);

  // Load PO list
  useEffect(() => {
    let isMounted = true;
    getPurchaseOrders(orgId).then(pos => {
      if (isMounted && pos && pos.length > 0) {
        setPurchaseOrders(pos);
      }
    });
    return () => { isMounted = false; };
  }, [orgId]);

  // Handle preselected PO from other tabs
  useEffect(() => {
    if (preselectedPoNumber) {
      const match = purchaseOrders.find(p => p.po_number.toLowerCase() === preselectedPoNumber.toLowerCase());
      if (match) {
        setSelectedPoNumber(match.po_number);
        setActivePo(match);
        setPhotoRefs([match.default_photo]);
        setLastResult(null);
        setErrorMessage(null);
      }
    }
  }, [preselectedPoNumber, purchaseOrders]);

  // Handle PO selection change
  const handleSelectPo = (poNumber: string) => {
    const match = purchaseOrders.find(p => p.po_number === poNumber);
    if (match) {
      setSelectedPoNumber(match.po_number);
      setActivePo(match);
      setPhotoRefs([match.default_photo]);
      setLastResult(null);
      setErrorMessage(null);
    }
  };

  // Upload handler
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setErrorMessage(null);

    try {
      const uploadedPaths: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
          throw new Error(`File '${file.name}' is not supported. Please upload JPEG, PNG, or WebP.`);
        }
        const res = await uploadPhoto(file, orgId);
        uploadedPaths.push(res.relative_path);
      }
      setPhotoRefs(prev => [...uploadedPaths, ...prev.filter(p => !uploadedPaths.includes(p))]);
    } catch (err: any) {
      setErrorMessage(`Photo upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const handleRemovePhoto = (index: number) => {
    setPhotoRefs(prev => prev.filter((_, i) => i !== index));
  };

  // Run AI Inspection
  const handleRunInspection = async () => {
    if (!activePo) {
      setErrorMessage('Please select a purchase order before running inspection.');
      return;
    }
    if (photoRefs.length === 0) {
      setErrorMessage('Please capture or upload at least one receiving photograph.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    // Realistic meaningful pipeline states without fake percentages
    setProgressState('Uploading & verifying receiving photos...');
    
    const timer1 = setTimeout(() => {
      setProgressState('Analyzing physical shipment condition & packaging...');
    }, 300);

    const timer2 = setTimeout(() => {
      setProgressState('Comparing observed goods against Purchase Order specifications...');
    }, 650);

    const timer3 = setTimeout(() => {
      setProgressState('Synthesizing evidence contract & computing confidence...');
    }, 1000);

    // Build payload using expected PO specification
    // Any simulation context (e.g. for testing short shipment, crushing, timeout)
    // is cleanly passed through if present from the PO's test profile.
    const sim = activePo.sim_context || {
      cartons_received: activePo.cartons_ordered,
      units_per_carton_counted: activePo.units_per_carton_ordered,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    };

    let activePhotos = [...photoRefs];
    if (sim.damage && sim.damage !== 'none' && !activePhotos[0].includes(sim.damage)) {
      activePhotos.push(`fixtures/receiving/${activePo.unit_id}_carton_${sim.damage}.jpg`);
    }

    const payload: InspectionPayload = {
      unit_id: activePo.unit_id,
      shipment_id: activePo.shipment_id || null,
      po_number: activePo.po_number,
      po_line: activePo.po_line,
      supplier: activePo.supplier,
      sku: activePo.sku,
      asin: activePo.asin,
      product_title: activePo.product_title,
      spec_colour: activePo.spec_colour,
      spec_variant: activePo.spec_variant,
      spec_components: activePo.spec_components,
      cartons_ordered: activePo.cartons_ordered,
      cartons_received: sim.cartons_received ?? activePo.cartons_ordered,
      units_per_carton_ordered: activePo.units_per_carton_ordered,
      units_per_carton_counted: sim.units_per_carton_counted ?? activePo.units_per_carton_ordered,
      photo_refs: activePhotos,
      simulate_fail_open: Boolean(sim.fail_open),
      override_identity_match: sim.id_match === 'yes' ? undefined : sim.id_match,
      override_quality_flags: sim.spec_mismatch ? ['wrong_colour', 'missing_components'] : []
    };

    try {
      const res = await runInspection(payload, orgId);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setLastResult(res);
      onRecordCreated();
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setErrorMessage(`Inspection error: ${err.message}. If real AI is offline, retry or hold for manual review.`);
    } finally {
      setLoading(false);
      setProgressState('');
    }
  };

  // Retry from Fail-Open (Priority 2: Preserves Attempt 1 in inspection_attempts table)
  const handleRetry = async () => {
    if (!lastResult || !lastResult.record_id) return;
    setLoading(true);
    setProgressState('Reprocessing fail-open shipment...');
    try {
      const res = await retryInspection(lastResult.record_id, orgId);
      setLastResult(res);
      onRecordCreated();
    } catch (err: any) {
      setErrorMessage(`Retry failed: ${err.message}`);
    } finally {
      setLoading(false);
      setProgressState('');
    }
  };

  // Priority 7: Re-inspection with additional photographic evidence (occlusion/uncertainty workflow)
  const handleReinspectWithEvidence = async () => {
    if (!lastResult || !lastResult.record_id) return;
    if (additionalPhotoRefs.length === 0) {
      setErrorMessage('Please attach or select at least one additional evidence photo before reinspecting.');
      return;
    }
    setReinspecting(true);
    setErrorMessage(null);
    setProgressState('Submitting additional photographic evidence & running reinspection...');
    try {
      const res = await reinspectWithEvidence(lastResult.record_id, orgId, additionalPhotoRefs, additionalNotes);
      setLastResult(res);
      setAdditionalPhotoRefs([]);
      setAdditionalNotes('');
      onRecordCreated();
    } catch (err: any) {
      setErrorMessage(`Reinspection failed: ${err.message}`);
    } finally {
      setReinspecting(false);
      setProgressState('');
    }
  };

  // Structured evidence parsing
  const structuredEvidence = lastResult?.structured_evidence || (lastResult?.evidence_data ? JSON.parse(lastResult.evidence_data) : null);
  const individualChecks = structuredEvidence?.individual_checks || [];

  // Filter purchase orders by search term
  const filteredPos = purchaseOrders.filter(p => 
    p.po_number.toLowerCase().includes(searchPoTerm.toLowerCase()) ||
    p.sku.toLowerCase().includes(searchPoTerm.toLowerCase()) ||
    p.product_title.toLowerCase().includes(searchPoTerm.toLowerCase()) ||
    p.supplier.toLowerCase().includes(searchPoTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Station Header Banner */}
      <div className="glass-panel" style={{ padding: '18px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Package style={{ color: 'var(--accent-blue)' }} size={24} />
              Receiving Inspection
            </h2>
            <span className="badge badge-pass" style={{ fontSize: '0.7rem' }}>
              Dock Station 01 · Inbound Intake
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Verify physical shipments against purchase orders with multimodal vision AI.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Selected PO: <strong style={{ color: 'var(--accent-cyan)' }}>{activePo?.po_number || 'None'}</strong>
          </div>
          {lastResult && (
            <button
              className="btn btn-secondary"
              style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              onClick={() => {
                setLastResult(null);
                setErrorMessage(null);
              }}
            >
              <RefreshCw size={14} /> New Inspection
            </button>
          )}
        </div>
      </div>

      {/* Two-Column Receiving Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.05fr) minmax(460px, 1.25fr)', gap: '22px', alignItems: 'start' }}>
        
        {/* LEFT COLUMN: Steps 1, 2, and Primary Inspection Action */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* STEP 1: Purchase Order Selection & Expected Data */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ background: 'var(--accent-blue)', color: 'white', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700 }}>
                  1
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Purchase Order</h3>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {purchaseOrders.length} Inbound POs Available
              </span>
            </div>

            {/* PO Selector Dropdown */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Select or Scan Purchase Order
              </label>
              <div style={{ position: 'relative' }}>
                <select
                  value={selectedPoNumber}
                  onChange={e => handleSelectPo(e.target.value)}
                  className="form-control"
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    background: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  {purchaseOrders.map(po => (
                    <option key={po.po_number} value={po.po_number} style={{ background: '#121824' }}>
                      {po.po_number} · {po.product_title} ({po.supplier}) — {po.qty_ordered} Units
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Expected Shipment Details (Auto-populated from PO — zero manual typing) */}
            {activePo && (
              <div style={{
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '8px',
                padding: '14px',
                border: '1px solid var(--border-color)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Expected Shipment Data (PO Spec)
                  </span>
                  <span className="badge" style={{ fontSize: '0.68rem', background: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)' }}>
                    PO Line {activePo.po_line}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '8px', fontSize: '0.82rem' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Product:</span>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{activePo.product_title}</div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>Supplier:</span>
                    <div style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>{activePo.supplier}</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', fontSize: '0.82rem', background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '6px' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>SKU</span>
                    <div className="code-font" style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.78rem' }}>{activePo.sku}</div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Variant / Colour</span>
                    <div style={{ fontWeight: 600, color: 'var(--text-secondary)', fontSize: '0.78rem' }}>{activePo.spec_variant} / {activePo.spec_colour}</div>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Components</span>
                    <div style={{ fontWeight: 500, color: 'var(--text-secondary)', fontSize: '0.78rem' }}>{activePo.spec_components}</div>
                  </div>
                </div>

                {/* Expected Quantity Breakdown */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '8px', paddingTop: '4px' }}>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '6px 10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Ordered Cartons</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{activePo.cartons_ordered} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-muted)' }}>ctns</span></div>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '6px 10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Units / Carton</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{activePo.units_per_carton_ordered} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-muted)' }}>units</span></div>
                  </div>
                  <div style={{ background: 'rgba(6, 182, 212, 0.1)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(6, 182, 212, 0.25)' }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)' }}>Total Expected Units</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>{activePo.qty_ordered} Units</div>
                  </div>
                </div>

                {activePo.notes && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '2px' }}>
                    Dock notes: {activePo.notes}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* STEP 2: Receiving Photos Capture & Upload Area */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ background: 'var(--accent-blue)', color: 'white', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700 }}>
                  2
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Receiving Photographs</h3>
              </div>
              <span className="badge badge-pass" style={{ fontSize: '0.68rem' }}>
                {photoRefs.length} Photo{photoRefs.length === 1 ? '' : 's'} Attached
              </span>
            </div>

            {/* Drag & Drop Upload Zone */}
            <div
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              style={{
                border: `2px dashed ${isDragging ? 'var(--accent-blue)' : 'var(--border-color)'}`,
                background: isDragging ? 'rgba(59, 130, 246, 0.08)' : 'rgba(0, 0, 0, 0.2)',
                borderRadius: '10px',
                padding: '18px',
                textAlign: 'center',
                transition: 'all 0.2s ease',
                marginBottom: '14px'
              }}
            >
              <Camera size={32} style={{ color: 'var(--accent-blue)', opacity: 0.8, marginBottom: '8px' }} />
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Drag & drop receiving photos here
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                Capture the carton label and physical condition of shipment. Supports JPEG, PNG, WebP.
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  <Upload size={14} />
                  {uploading ? 'Uploading...' : 'Take / Upload Photos'}
                </button>

                {activePo && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                    onClick={() => {
                      if (!photoRefs.includes(activePo.default_photo)) {
                        setPhotoRefs(prev => [activePo.default_photo, ...prev]);
                      }
                    }}
                  >
                    <ImageIcon size={14} /> Attach Dock Feed Photo
                  </button>
                )}
              </div>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={e => handleFileUpload(e.target.files)}
                style={{ display: 'none' }}
              />
            </div>

            {/* Thumbnail Gallery */}
            {photoRefs.length > 0 ? (
              <div>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Attached Photos for Inspection:
                </div>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {photoRefs.map((ref, idx) => (
                    <div
                      key={idx}
                      style={{
                        position: 'relative',
                        width: '84px',
                        height: '84px',
                        borderRadius: '6px',
                        overflow: 'hidden',
                        border: '1px solid var(--border-color)',
                        background: '#090d16'
                      }}
                    >
                      <img
                        src={getImageUrl(ref, orgId)}
                        alt={`Photo ${idx + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        onError={(e: any) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => handleRemovePhoto(idx)}
                        style={{
                          position: 'absolute',
                          top: '4px',
                          right: '4px',
                          background: 'rgba(0,0,0,0.7)',
                          color: '#fb7185',
                          border: 'none',
                          borderRadius: '4px',
                          width: '20px',
                          height: '20px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: 0
                        }}
                        title="Remove photo"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertCircle size={14} /> Upload at least one receiving photo to run inspection.
              </div>
            )}
          </div>

          {/* STEP 3: RUN AI INSPECTION CTA */}
          <div>
            {errorMessage && (
              <div style={{
                background: 'rgba(244, 63, 94, 0.15)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                padding: '12px 16px',
                borderRadius: '8px',
                color: '#fb7185',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '12px'
              }}>
                <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                <span>{errorMessage}</span>
              </div>
            )}

            <button
              type="button"
              className="btn btn-primary"
              style={{
                width: '100%',
                padding: '15px 20px',
                fontSize: '1rem',
                fontWeight: 700,
                letterSpacing: '0.02em',
                boxShadow: '0 6px 20px 0 rgba(59, 130, 246, 0.4)'
              }}
              onClick={handleRunInspection}
              disabled={loading || photoRefs.length === 0}
            >
              {loading ? (
                <>
                  <RefreshCw className="pulse-active" size={20} />
                  <span>{progressState || 'Analyzing shipment...'}</span>
                </>
              ) : (
                <>
                  <Camera size={20} />
                  <span>RUN AI INSPECTION</span>
                </>
              )}
            </button>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: '6px' }}>
              Single-pass multimodal vision engine · Evaluates identity, quantity math, carton damage & specs
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Results, Visual Evidence, Expected vs Observed, Recommended Action */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          
          {/* Header of Results Panel */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Box style={{ color: 'var(--accent-purple)' }} size={22} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Inspection Results & Evidence</h3>
            </div>

            {lastResult && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge" style={{ fontSize: '0.68rem', background: lastResult.is_real_ai ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)', color: lastResult.is_real_ai ? '#34d399' : '#fbbf24', border: `1px solid ${lastResult.is_real_ai ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}` }}>
                  <Cpu size={12} /> {lastResult.execution_mode}
                </span>
                <span className="code-font" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {lastResult.batch_execution_time_ms}ms
                </span>
              </div>
            )}
          </div>

          {/* Result Outcome Display */}
          {lastResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Large Status Hero Banner */}
              <div style={{
                padding: '16px 20px',
                borderRadius: '10px',
                background:
                  lastResult.overall_verdict === 'PASS'
                    ? 'rgba(16, 185, 129, 0.15)'
                    : lastResult.overall_verdict === 'FAIL'
                    ? 'rgba(244, 63, 94, 0.16)'
                    : lastResult.overall_verdict === 'PENDING_REVIEW'
                    ? 'rgba(139, 92, 246, 0.16)'
                    : 'rgba(245, 158, 11, 0.16)',
                border: `1px solid ${
                  lastResult.overall_verdict === 'PASS'
                    ? 'rgba(16, 185, 129, 0.35)'
                    : lastResult.overall_verdict === 'FAIL'
                    ? 'rgba(244, 63, 94, 0.4)'
                    : lastResult.overall_verdict === 'PENDING_REVIEW'
                    ? 'rgba(139, 92, 246, 0.4)'
                    : 'rgba(245, 158, 11, 0.4)'
                }`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  {lastResult.overall_verdict === 'PASS' && (
                    <div style={{ background: 'rgba(16, 185, 129, 0.25)', padding: '10px', borderRadius: '10px', color: '#10b981' }}>
                      <CheckCircle size={32} />
                    </div>
                  )}
                  {lastResult.overall_verdict === 'FAIL' && (
                    <div style={{ background: 'rgba(244, 63, 94, 0.25)', padding: '10px', borderRadius: '10px', color: '#f43f5e' }}>
                      <AlertTriangle size={32} />
                    </div>
                  )}
                  {lastResult.overall_verdict === 'UNCERTAIN' && (
                    <div style={{ background: 'rgba(245, 158, 11, 0.25)', padding: '10px', borderRadius: '10px', color: '#f59e0b' }}>
                      <HelpCircle size={32} />
                    </div>
                  )}
                  {lastResult.overall_verdict === 'PENDING_REVIEW' && (
                    <div style={{ background: 'rgba(139, 92, 246, 0.25)', padding: '10px', borderRadius: '10px', color: '#a78bfa' }}>
                      <ShieldAlert size={32} />
                    </div>
                  )}

                  <div>
                    <div style={{ fontSize: '1.45rem', fontWeight: 900, letterSpacing: '0.02em' }}>
                      {lastResult.overall_verdict}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {lastResult.overall_verdict === 'PASS' && 'Shipment matches the purchase order.'}
                      {lastResult.overall_verdict === 'FAIL' && 'Receiving discrepancy detected.'}
                      {lastResult.overall_verdict === 'UNCERTAIN' && 'The evidence is insufficient to verify the shipment.'}
                      {lastResult.overall_verdict === 'PENDING_REVIEW' && 'AI inspection could not be completed. Retry or perform manual inspection.'}
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>RECORD ID</div>
                  <div className="code-font" style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {lastResult.record_id}
                  </div>
                  {lastResult.shipment_id && (
                    <div style={{ marginTop: '4px' }}>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>SHIPMENT ID</div>
                      <div className="code-font" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                        {lastResult.shipment_id}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Visual Evidence Image Viewer with Bounding Box Overlays */}
              <div style={{
                position: 'relative',
                height: '240px',
                background: '#070a10',
                borderRadius: '10px',
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden'
              }}>
                {photoRefs[0] && (
                  <img
                    src={getImageUrl(photoRefs[0], orgId)}
                    alt="Received shipment photograph"
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    onError={(e: any) => {
                      e.target.style.display = 'none';
                    }}
                  />
                )}

                {/* Watermark Tag */}
                <div style={{
                  position: 'absolute',
                  top: '10px',
                  left: '10px',
                  background: 'rgba(10, 13, 20, 0.85)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '0.68rem',
                  color: '#94a3b8',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <Camera size={12} />
                  <span>RECEIVING EVIDENCE · DOCK 01</span>
                </div>

                {/* Bounding Box Visual Overlays (Rendered from backend check coordinates) */}
                {individualChecks.map((check: any, idx: number) => {
                  if (!check.bounding_box) return null;
                  const bbox = check.bounding_box;
                  const isIssue = check.verdict === 'FAIL';
                  const isUncertain = check.verdict === 'UNCERTAIN';
                  const borderColor = isIssue ? '#f43f5e' : (isUncertain ? '#f59e0b' : '#10b981');
                  const isHighlighted = highlightedCheck === check.check_name;

                  return (
                    <div
                      key={idx}
                      style={{
                        position: 'absolute',
                        left: `${bbox.x * 100}%`,
                        top: `${bbox.y * 100}%`,
                        width: `${bbox.w * 100}%`,
                        height: `${bbox.h * 100}%`,
                        border: `2px ${isIssue ? 'solid' : 'dashed'} ${borderColor}`,
                        borderRadius: '4px',
                        background: isHighlighted ? 'rgba(244,63,94,0.15)' : 'transparent',
                        pointerEvents: 'none',
                        transition: 'all 0.2s ease',
                        boxShadow: isIssue ? '0 0 12px rgba(244,63,94,0.4)' : 'none'
                      }}
                    >
                      <span
                        style={{
                          position: 'absolute',
                          top: '-18px',
                          left: '0',
                          background: borderColor,
                          color: '#ffffff',
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '3px',
                          whiteSpace: 'nowrap',
                          textTransform: 'uppercase'
                        }}
                      >
                        {check.check_name}: {check.observed_value}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Evidence Text Display (Directly from engine) */}
              <div style={{
                background: 'rgba(0,0,0,0.25)',
                padding: '12px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                fontSize: '0.82rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  <Info size={14} style={{ color: 'var(--accent-blue)' }} />
                  <span>Evidence:</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  "{structuredEvidence?.decision_rationale || `Inspection evaluated with ${Math.round((lastResult.agent_confidence || 0) * 100)}% confidence.`}"
                </div>

                {structuredEvidence?.uncertain_explanation && (
                  <div style={{ marginTop: '10px', padding: '8px 10px', background: 'rgba(245, 158, 11, 0.1)', borderLeft: '3px solid #f59e0b', borderRadius: '4px' }}>
                    <div style={{ fontWeight: 700, color: '#fbbf24', fontSize: '0.78rem' }}>Uncertainty Cause:</div>
                    <div style={{ color: '#fde68a', fontSize: '0.75rem', marginTop: '2px' }}>{structuredEvidence.uncertain_explanation}</div>
                    <div style={{ fontWeight: 700, color: '#fbbf24', fontSize: '0.78rem', marginTop: '6px' }}>Recommended Next Evidence:</div>
                    <div style={{ color: '#fde68a', fontSize: '0.75rem', marginTop: '2px' }}>{structuredEvidence.recommended_next_evidence}</div>
                  </div>
                )}
              </div>

              {/* Expected vs Observed Comparison Table */}
              <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Expected vs Observed Comparison</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Actual observations from visual inspection</span>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '6px 8px' }}>CHECK</th>
                        <th style={{ padding: '6px 8px' }}>EXPECTED</th>
                        <th style={{ padding: '6px 8px' }}>OBSERVED</th>
                        <th style={{ padding: '6px 8px', textAlign: 'right' }}>STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* 1. Product / SKU */}
                      <tr
                        onMouseEnter={() => setHighlightedCheck('Product/SKU Identity')}
                        onMouseLeave={() => setHighlightedCheck(null)}
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'default' }}
                      >
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Product / SKU</td>
                        <td style={{ padding: '7px 8px' }} className="code-font">{activePo?.sku}</td>
                        <td style={{ padding: '7px 8px' }} className="code-font">
                          {lastResult.identity_match === 'yes' ? activePo?.sku : (lastResult.identity_match === 'no' ? 'SKU Contradiction' : 'UNKNOWN / UNCERTAIN')}
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${lastResult.identity_match === 'yes' ? 'badge-pass' : (lastResult.identity_match === 'no' ? 'badge-fail' : 'badge-uncertain')}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {lastResult.identity_match === 'yes' ? '✓' : (lastResult.identity_match === 'no' ? '✕' : '?')}
                          </span>
                        </td>
                      </tr>

                      {/* 2. Total Quantity */}
                      <tr
                        onMouseEnter={() => setHighlightedCheck('Quantity Verification')}
                        onMouseLeave={() => setHighlightedCheck(null)}
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'default' }}
                      >
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Total Quantity</td>
                        <td style={{ padding: '7px 8px' }}>{lastResult.qty_ordered} Units ({lastResult.cartons_ordered} ctns)</td>
                        <td style={{ padding: '7px 8px', color: lastResult.qty_received !== lastResult.qty_ordered ? 'var(--accent-rose)' : 'inherit', fontWeight: lastResult.qty_received !== lastResult.qty_ordered ? 700 : 400 }}>
                          {lastResult.qty_received} Units ({lastResult.cartons_received} ctns)
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${lastResult.qty_received === lastResult.qty_ordered ? 'badge-pass' : 'badge-fail'}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {lastResult.qty_received === lastResult.qty_ordered ? '✓' : '✕'}
                          </span>
                        </td>
                      </tr>

                      {/* 3. Colour */}
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Colour</td>
                        <td style={{ padding: '7px 8px' }}>{activePo?.spec_colour || 'n/a'}</td>
                        <td style={{ padding: '7px 8px' }}>
                          {lastResult.quality_flags?.includes('wrong_colour') ? 'Wrong Colour (Mismatched)' : (activePo?.spec_colour || 'Verified')}
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${!lastResult.quality_flags?.includes('wrong_colour') ? 'badge-pass' : 'badge-fail'}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {!lastResult.quality_flags?.includes('wrong_colour') ? '✓' : '✕'}
                          </span>
                        </td>
                      </tr>

                      {/* 4. Variant */}
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Variant</td>
                        <td style={{ padding: '7px 8px' }}>{activePo?.spec_variant || 'Standard'}</td>
                        <td style={{ padding: '7px 8px' }}>
                          {lastResult.quality_flags?.includes('wrong_variant') ? 'Wrong Variant' : (activePo?.spec_variant || 'Verified')}
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${!lastResult.quality_flags?.includes('wrong_variant') ? 'badge-pass' : 'badge-fail'}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {!lastResult.quality_flags?.includes('wrong_variant') ? '✓' : '✕'}
                          </span>
                        </td>
                      </tr>

                      {/* 5. Carton Physical Integrity */}
                      <tr
                        onMouseEnter={() => setHighlightedCheck('Carton Physical Integrity')}
                        onMouseLeave={() => setHighlightedCheck(null)}
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
                      >
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Carton Condition</td>
                        <td style={{ padding: '7px 8px' }}>Intact / Undamaged</td>
                        <td style={{ padding: '7px 8px', color: lastResult.carton_damage !== 'none' ? 'var(--accent-rose)' : 'inherit', fontWeight: lastResult.carton_damage !== 'none' ? 700 : 400 }}>
                          {lastResult.carton_damage === 'none' ? 'Intact' : (lastResult.carton_damage === 'uncertain' ? 'UNCERTAIN / NOT VISIBLE' : lastResult.carton_damage.toUpperCase())}
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${lastResult.carton_damage === 'none' ? 'badge-pass' : (lastResult.carton_damage === 'uncertain' ? 'badge-uncertain' : 'badge-fail')}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {lastResult.carton_damage === 'none' ? '✓' : (lastResult.carton_damage === 'uncertain' ? '?' : '✕')}
                          </span>
                        </td>
                      </tr>

                      {/* 6. Components */}
                      <tr>
                        <td style={{ padding: '7px 8px', fontWeight: 600 }}>Components</td>
                        <td style={{ padding: '7px 8px' }}>{activePo?.spec_components || 'Complete'}</td>
                        <td style={{ padding: '7px 8px' }}>
                          {lastResult.quality_flags?.includes('missing_components') ? 'Missing Components' : (lastResult.overall_verdict === 'UNCERTAIN' ? 'UNKNOWN / NOT VISIBLE' : (activePo?.spec_components || 'Complete'))}
                        </td>
                        <td style={{ padding: '7px 8px', textAlign: 'right' }}>
                          <span className={`badge ${!lastResult.quality_flags?.includes('missing_components') && lastResult.overall_verdict !== 'UNCERTAIN' ? 'badge-pass' : (lastResult.overall_verdict === 'UNCERTAIN' ? 'badge-uncertain' : 'badge-fail')}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                            {!lastResult.quality_flags?.includes('missing_components') && lastResult.overall_verdict !== 'UNCERTAIN' ? '✓' : (lastResult.overall_verdict === 'UNCERTAIN' ? '?' : '✕')}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Confidence Display */}
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    Inspection Confidence
                  </span>
                  <span className="code-font" style={{ fontSize: '0.85rem', fontWeight: 800, color: lastResult.overall_verdict === 'UNCERTAIN' ? '#fbbf24' : '#34d399' }}>
                    {Math.round((lastResult.agent_confidence || 0) * 100)}%
                    {lastResult.overall_verdict === 'UNCERTAIN' && ' (Uncertain)'}
                  </span>
                </div>
                <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.round((lastResult.agent_confidence || 0) * 100)}%`,
                      background: lastResult.overall_verdict === 'PASS' ? '#10b981' : (lastResult.overall_verdict === 'FAIL' ? '#f43f5e' : (lastResult.overall_verdict === 'PENDING_REVIEW' ? '#8b5cf6' : '#f59e0b')),
                      borderRadius: '4px',
                      transition: 'width 0.4s ease'
                    }}
                  />
                </div>
              </div>

              {/* Recommended Next Action */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                padding: '14px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)'
              }}>
                <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Recommended Next Action
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px' }}>
                  {lastResult.overall_verdict === 'PASS' && 'Proceed with receiving. Goods verified against PO.'}
                  {lastResult.overall_verdict === 'FAIL' && 'Hold shipment for operator review.'}
                  {lastResult.overall_verdict === 'UNCERTAIN' && 'Capture a clearer label/photo or inspect the item manually.'}
                  {lastResult.overall_verdict === 'PENDING_REVIEW' && 'AI inspection could not be completed. Retry or perform manual inspection.'}
                </div>

                {/* Operator Actions / Override Buttons */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {lastResult.overall_verdict === 'PENDING_REVIEW' && (
                    <button
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: '0.8rem', background: '#8b5cf6' }}
                      onClick={handleRetry}
                    >
                      <RefreshCw size={14} /> Retry Inspection
                    </button>
                  )}

                  {onOpenOverride && (
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                      onClick={() => onOpenOverride(lastResult)}
                    >
                      <Edit3 size={14} /> Operator Override
                    </button>
                  )}

                  {onViewContract && (
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                      onClick={() => onViewContract(lastResult)}
                    >
                      <FileText size={14} /> View Evidence JSON Contract
                    </button>
                  )}
                </div>

                {/* Priority 7: Occlusion / Additional Evidence Workflow for UNCERTAIN results */}
                {lastResult.overall_verdict === 'UNCERTAIN' && (
                  <div style={{
                    marginTop: '16px',
                    padding: '14px',
                    background: 'rgba(245, 158, 11, 0.08)',
                    borderRadius: '8px',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                      <HelpCircle size={20} style={{ color: '#f59e0b', flexShrink: 0, marginTop: '2px' }} />
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24' }}>
                          Occlusion / Insufficient Visual Evidence
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                          The visual evidence is insufficient to verify this delivery with certainty (e.g. barcode/label is obscured, carton packaging angle does not reveal contents, or lighting is inadequate). Please attach additional photos to resolve the uncertainty.
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                        Add Additional Evidence Photo(s):
                      </div>

                      {/* Quick Evidence Photo Selection Buttons */}
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {[
                          { label: '+ Clear Pallet Photo', ref: 'fixtures/receiving/clean_pallet.jpg' },
                          { label: '+ Carton Detail Angle', ref: 'fixtures/receiving/UNIT-0101_carton_clean.jpg' },
                          { label: '+ Label Close-up', ref: 'fixtures/receiving/clean_label_closeup.jpg' }
                        ].map((photoPreset, idx) => (
                          <button
                            key={idx}
                            type="button"
                            className="btn btn-secondary"
                            style={{
                              fontSize: '0.74rem',
                              padding: '4px 10px',
                              background: additionalPhotoRefs.includes(photoPreset.ref) ? 'rgba(59,130,246,0.3)' : undefined,
                              borderColor: additionalPhotoRefs.includes(photoPreset.ref) ? 'var(--accent-blue)' : undefined
                            }}
                            onClick={() => {
                              if (additionalPhotoRefs.includes(photoPreset.ref)) {
                                setAdditionalPhotoRefs(prev => prev.filter(r => r !== photoPreset.ref));
                              } else {
                                setAdditionalPhotoRefs(prev => [...prev, photoPreset.ref]);
                              }
                            }}
                          >
                            {additionalPhotoRefs.includes(photoPreset.ref) ? '✓ ' : ''}{photoPreset.label}
                          </button>
                        ))}
                      </div>

                      {/* Additional Evidence File Upload */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          style={{ display: 'none' }}
                          id="additional-evidence-upload"
                          onChange={async (e) => {
                            if (e.target.files && e.target.files.length > 0) {
                              try {
                                const res = await uploadPhoto(e.target.files[0], orgId);
                                setAdditionalPhotoRefs(prev => [...prev, res.relative_path]);
                              } catch (err: any) {
                                setErrorMessage(`Additional photo upload failed: ${err.message}`);
                              }
                            }
                          }}
                        />
                        <label
                          htmlFor="additional-evidence-upload"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '4px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Upload size={13} /> Upload Photo from Device
                        </label>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {additionalPhotoRefs.length} photo(s) selected
                        </span>
                      </div>

                      {/* Optional Notes */}
                      <input
                        type="text"
                        placeholder="Operator observation notes (e.g. Cleared shrink-wrap to expose barcode)..."
                        value={additionalNotes}
                        onChange={(e) => setAdditionalNotes(e.target.value)}
                        className="form-control"
                        style={{ fontSize: '0.78rem', padding: '6px 10px', marginTop: '4px' }}
                      />

                      {/* Reinspect Action Button */}
                      <button
                        className="btn btn-primary"
                        style={{
                          marginTop: '6px',
                          padding: '8px 14px',
                          fontSize: '0.82rem',
                          background: '#d97706',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px'
                        }}
                        onClick={handleReinspectWithEvidence}
                        disabled={reinspecting || additionalPhotoRefs.length === 0}
                      >
                        <RefreshCw size={14} className={reinspecting ? 'spin' : ''} />
                        {reinspecting ? 'Reinspecting with Evidence...' : 'Add Evidence & Reinspect'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Priority 2: Preserved Inspection Attempts Audit Trail */}
              {lastResult.attempts && lastResult.attempts.length > 0 && (
                <div style={{
                  background: 'rgba(0,0,0,0.25)',
                  padding: '14px 16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  marginTop: '14px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <History size={14} style={{ color: 'var(--accent-blue)' }} />
                      Inspection Attempts Audit History ({lastResult.attempts.length})
                    </span>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      Attempt 1 preserved · Immutable Audit Trail
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {lastResult.attempts.map((att: any, idx: number) => {
                      const verdict = att.overall_verdict;
                      const badgeClass = verdict === 'PASS' ? 'badge-pass' : (verdict === 'FAIL' ? 'badge-fail' : (verdict === 'PENDING_REVIEW' ? 'badge-pending' : 'badge-uncertain'));
                      return (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '8px 12px',
                            background: idx === lastResult.attempts.length - 1 ? 'rgba(59,130,246,0.08)' : 'rgba(255,255,255,0.02)',
                            borderRadius: '6px',
                            border: `1px solid ${idx === lastResult.attempts.length - 1 ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)'}`,
                            fontSize: '0.75rem'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                              Attempt #{att.attempt_number}
                            </span>
                            <span className={`badge ${badgeClass}`} style={{ fontSize: '0.65rem' }}>
                              {verdict}
                            </span>
                            <span style={{ color: 'var(--text-muted)' }}>
                              Mode: {att.execution_mode}
                            </span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{ color: 'var(--text-secondary)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={att.decision_rationale}>
                              {att.decision_rationale || 'Completed'}
                            </span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                              {att.created_at ? new Date(att.created_at).toLocaleTimeString() : ''}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

            </div>
          ) : (
            /* Empty State */
            <div style={{
              flex: 1,
              minHeight: '380px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              textAlign: 'center',
              gap: '12px',
              padding: '30px'
            }}>
              <div style={{ background: 'var(--bg-tertiary)', padding: '18px', borderRadius: '50%', opacity: 0.7 }}>
                <Layers size={40} style={{ color: 'var(--accent-blue)' }} />
              </div>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Your inspection results will appear here.
              </div>
              <div style={{ fontSize: '0.82rem', maxWidth: '360px', lineHeight: 1.5 }}>
                Select a purchase order, attach receiving photos, and click <strong>RUN AI INSPECTION</strong> to inspect the inbound delivery.
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
