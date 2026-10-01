import React, { useState, useEffect } from 'react';
import { Search, Package, ArrowRight, CheckCircle, AlertTriangle, Clock, Filter, Eye } from 'lucide-react';
import { PURCHASE_ORDERS_CATALOG, PurchaseOrderItem, getPurchaseOrders } from '../data/purchaseOrders';
import { ReceivingRecord } from '../api';

interface Props {
  orgId: string;
  records: ReceivingRecord[];
  onSelectPoToReceive: (poNumber: string) => void;
}

export const PurchaseOrdersView: React.FC<Props> = ({ orgId, records, onSelectPoToReceive }) => {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrderItem[]>(PURCHASE_ORDERS_CATALOG);
  const [searchTerm, setSearchTerm] = useState('');
  const [supplierFilter, setSupplierFilter] = useState('ALL');

  useEffect(() => {
    let isMounted = true;
    getPurchaseOrders(orgId).then(pos => {
      if (isMounted && pos && pos.length > 0) {
        setPurchaseOrders(pos);
      }
    });
    return () => { isMounted = false; };
  }, [orgId]);

  // Find if PO has already been inspected in the records
  const getPoStatus = (poNumber: string) => {
    const inspected = records.filter(r => r.po_number.toLowerCase() === poNumber.toLowerCase());
    if (inspected.length === 0) return { label: 'Awaiting Intake', type: 'pending' };
    const latest = inspected[0];
    return {
      label: `Inspected (${latest.overall_verdict})`,
      type: latest.overall_verdict.toLowerCase(),
      recordId: latest.record_id
    };
  };

  const suppliers = Array.from(new Set(purchaseOrders.map(p => p.supplier)));

  const filtered = purchaseOrders.filter(p => {
    const matchSearch =
      p.po_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.product_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.supplier.toLowerCase().includes(searchTerm.toLowerCase());
    const matchSupplier = supplierFilter === 'ALL' || p.supplier === supplierFilter;
    return matchSearch && matchSupplier;
  });

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package style={{ color: 'var(--accent-blue)' }} size={22} />
            Inbound Purchase Orders Directory
          </h2>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Enterprise ERP Inbound Feed · Scoped to {orgId} · {filtered.length} POs Available for Dock Intake
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Supplier Filter */}
          <select
            className="form-control"
            style={{ width: 'auto', fontSize: '0.8rem', padding: '6px 10px' }}
            value={supplierFilter}
            onChange={e => setSupplierFilter(e.target.value)}
          >
            <option value="ALL">All Suppliers</option>
            {suppliers.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Search Input */}
          <div style={{ position: 'relative', width: '220px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-control"
              placeholder="Search PO, SKU, Title..."
              style={{ paddingLeft: '32px' }}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* PO Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '10px' }}>PO Number</th>
              <th style={{ padding: '10px' }}>Supplier</th>
              <th style={{ padding: '10px' }}>Product & Description</th>
              <th style={{ padding: '10px' }}>SKU</th>
              <th style={{ padding: '10px' }}>Variant / Spec</th>
              <th style={{ padding: '10px' }}>Cartons</th>
              <th style={{ padding: '10px' }}>Expected Units</th>
              <th style={{ padding: '10px' }}>Intake Status</th>
              <th style={{ padding: '10px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(po => {
              const status = getPoStatus(po.po_number);
              return (
                <tr key={po.po_number} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.15s' }}>
                  <td style={{ padding: '10px', fontWeight: 700 }} className="code-font">
                    <div>{po.po_number}</div>
                    {po.shipment_id && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                        {po.shipment_id}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                    {po.supplier}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <div style={{ fontWeight: 600 }}>{po.product_title}</div>
                    {po.notes && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{po.notes}</div>
                    )}
                  </td>
                  <td style={{ padding: '10px' }} className="code-font">
                    {po.sku}
                  </td>
                  <td style={{ padding: '10px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    {po.spec_variant} / {po.spec_colour}
                  </td>
                  <td style={{ padding: '10px' }}>
                    {po.cartons_ordered} ctns
                  </td>
                  <td style={{ padding: '10px', fontWeight: 600 }}>
                    {po.qty_ordered} units
                  </td>
                  <td style={{ padding: '10px' }}>
                    <span
                      className={`badge ${
                        status.type === 'pass'
                          ? 'badge-pass'
                          : status.type === 'fail'
                          ? 'badge-fail'
                          : status.type === 'uncertain'
                          ? 'badge-uncertain'
                          : 'badge'
                      }`}
                      style={{
                        fontSize: '0.68rem',
                        background: status.type === 'pending' ? 'rgba(255,255,255,0.06)' : undefined,
                        color: status.type === 'pending' ? 'var(--text-muted)' : undefined
                      }}
                    >
                      {status.label}
                    </span>
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <button
                      className="btn btn-primary"
                      style={{ padding: '5px 12px', fontSize: '0.75rem' }}
                      onClick={() => onSelectPoToReceive(po.po_number)}
                    >
                      Receive Shipment <ArrowRight size={12} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No purchase orders found matching '{searchTerm}'.
        </div>
      )}
    </div>
  );
};
