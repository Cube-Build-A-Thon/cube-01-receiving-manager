/**
 * Purchase Order Adapter & Repository
 * 
 * In a production warehouse environment, this adapter connects to an ERP / WMS
 * (e.g., SAP, NetSuite, Manhattan Associates) via REST / GraphQL / Kafka.
 * 
 * For this receiving workstation, it provides structured purchase orders derived from
 * inbound delivery notices and the CUBE Buildathon challenge test scenarios.
 * 
 * Operators select or scan a PO number, and all expected shipment metadata
 * (SKU, description, quantities, carton specs) is automatically loaded without manual data entry.
 */

export interface PurchaseOrderItem {
  po_number: string;
  po_line: number;
  shipment_id?: string | null;
  supplier: string;
  unit_id: string;
  sku: string;
  asin: string;
  product_title: string;
  spec_colour: string;
  spec_variant: string;
  spec_components: string;
  cartons_ordered: number;
  units_per_carton_ordered: number;
  qty_ordered: number;
  default_photo: string;
  notes?: string;
  scenario_id?: string;
  scenario_label?: string;
  scenario_tag?: 'PASS' | 'FAIL' | 'UNCERTAIN' | 'PENDING';
  // Associated simulation context if tested in Demo Mode
  sim_context?: {
    cartons_received: number;
    units_per_carton_counted: number;
    fail_open?: boolean;
    damage?: 'none' | 'crushing' | 'water' | 'tears' | 'blur';
    spec_mismatch?: boolean;
    id_match?: 'yes' | 'no' | 'uncertain';
  };
}

export const PURCHASE_ORDERS_CATALOG: PurchaseOrderItem[] = [
  // --- Standard Inbound Challenge POs (Scenarios 1-11) ---
  {
    po_number: 'PO-1001',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-0101',
    sku: 'BLUE-BOTTLE-001',
    asin: 'B0DUMMY600',
    product_title: 'Blue Stainless Steel Bottle',
    spec_colour: 'Blue',
    spec_variant: 'Standard',
    spec_components: 'bottle; lid',
    cartons_ordered: 2,
    units_per_carton_ordered: 12,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/clean_pallet.jpg',
    notes: 'Standard clean inbound pallet · 2 cartons x 12 units',
    scenario_id: 's1',
    scenario_label: '1. Correct Shipment',
    scenario_tag: 'PASS',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1002',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-0102',
    sku: 'BLUE-BOTTLE-001',
    asin: 'B0DUMMY600',
    product_title: 'Blue Stainless Steel Bottle',
    spec_colour: 'Blue',
    spec_variant: 'Standard',
    spec_components: 'bottle; lid',
    cartons_ordered: 2,
    units_per_carton_ordered: 12,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/short_shipment.jpg',
    notes: 'Discrepancy: Short shipment (-4 units received)',
    scenario_id: 's2',
    scenario_label: '2. Short Shipment (-4 Units)',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 10,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1003',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-0103',
    sku: 'BLUE-BOTTLE-001',
    asin: 'B0DUMMY600',
    product_title: 'Blue Stainless Steel Bottle',
    spec_colour: 'Blue',
    spec_variant: 'Standard',
    spec_components: 'bottle; lid',
    cartons_ordered: 2,
    units_per_carton_ordered: 12,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/extra_units.jpg',
    notes: 'Discrepancy: Over-shipment (+4 extra units)',
    scenario_id: 's3',
    scenario_label: '3. Extra Units (+4 Over)',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 14,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1004',
    po_line: 1,
    supplier: 'Supplier North Distributors',
    unit_id: 'UNIT-0104',
    sku: 'BLUE-BOTTLE-001',
    asin: 'B0DUMMY600',
    product_title: 'Blue Stainless Steel Bottle',
    spec_colour: 'Blue',
    spec_variant: 'Standard',
    spec_components: 'bottle; lid',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/wrong_sku.jpg',
    notes: 'Discrepancy: Label contradicts expected SKU identity',
    scenario_id: 's4',
    scenario_label: '4. Wrong SKU Contradiction',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'no'
    }
  },
  {
    po_number: 'PO-1005',
    po_line: 1,
    supplier: 'Supplier North Distributors',
    unit_id: 'UNIT-0105',
    sku: 'BLUE-BOTTLE-001',
    asin: 'B0DUMMY600',
    product_title: 'Blue Stainless Steel Bottle',
    spec_colour: 'Blue',
    spec_variant: 'Standard',
    spec_components: 'bottle; lid',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/red_variant.jpg',
    notes: 'Discrepancy: Wrong colour variant (Red received vs Blue ordered)',
    scenario_id: 's5',
    scenario_label: '5. Wrong Variant / Colour',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: true,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1006',
    po_line: 1,
    supplier: 'Coastal Fragrance & Living',
    unit_id: 'UNIT-0106',
    sku: 'CANDLE-3PK',
    asin: 'B0DUMMY964',
    product_title: 'Soy Candle Set 3-Pack',
    spec_colour: 'Cream',
    spec_variant: '3-pack',
    spec_components: 'candles x3; gift box',
    cartons_ordered: 1,
    units_per_carton_ordered: 6,
    qty_ordered: 6,
    default_photo: 'fixtures/receiving/pallet_crushing.jpg',
    notes: 'Discrepancy: Visible structural carton crushing and compression',
    scenario_id: 's6',
    scenario_label: '6. Crushed Carton',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 6,
      damage: 'crushing',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1007',
    po_line: 1,
    supplier: 'Coastal Fragrance & Living',
    unit_id: 'UNIT-0107',
    sku: 'CANDLE-3PK',
    asin: 'B0DUMMY964',
    product_title: 'Soy Candle Set 3-Pack',
    spec_colour: 'Cream',
    spec_variant: '3-pack',
    spec_components: 'candles x3; gift box',
    cartons_ordered: 1,
    units_per_carton_ordered: 6,
    qty_ordered: 6,
    default_photo: 'fixtures/receiving/carton_water_soaked.jpg',
    notes: 'Discrepancy: Liquid stains and moisture absorption detected on carton bottom',
    scenario_id: 's7',
    scenario_label: '7. Water Damaged Carton',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 6,
      damage: 'water',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1008',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-0108',
    sku: 'TOWEL-BLU',
    asin: 'B0DUMMY600',
    product_title: 'Cotton Bath Towel',
    spec_colour: 'Blue',
    spec_variant: 'Bath',
    spec_components: 'towel',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/packaging_tears.jpg',
    notes: 'Discrepancy: Outer cardboard punctures and packaging tears',
    scenario_id: 's8',
    scenario_label: '8. Torn Outer Packaging',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      damage: 'tears',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1009',
    po_line: 1,
    supplier: 'Apex Nutrition Supplies',
    unit_id: 'UNIT-0109',
    sku: 'PROT-1KG',
    asin: 'B0DUMMY357',
    product_title: 'Whey Protein Tub',
    spec_colour: 'n/a',
    spec_variant: '1kg Vanilla',
    spec_components: 'tub; scoop',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/missing_scoop.jpg',
    notes: 'Discrepancy: Missing component (Measuring scoop absent from tub)',
    scenario_id: 's9',
    scenario_label: '9. Missing Components (No Scoop)',
    scenario_tag: 'FAIL',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: true,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-1010',
    po_line: 1,
    supplier: 'DermaCare Labs',
    unit_id: 'UNIT-0110',
    sku: 'SERUM-30ML',
    asin: 'B0DUMMY031',
    product_title: 'Vitamin C Facial Serum',
    spec_colour: 'Amber',
    spec_variant: '30ml',
    spec_components: 'bottle; dropper',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/blur_dark_occluded.jpg',
    notes: 'Ambiguous: Low lighting and heavy blur prevents definitive verification',
    scenario_id: 's10',
    scenario_label: '10. Ambiguous (UNCERTAIN)',
    scenario_tag: 'UNCERTAIN',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'uncertain'
    }
  },
  {
    po_number: 'PO-1011',
    po_line: 1,
    supplier: 'Lumina Home Products',
    unit_id: 'UNIT-0111',
    sku: 'LAMP-LED',
    asin: 'B0DUMMY357',
    product_title: 'LED Desk Lamp',
    spec_colour: 'White',
    spec_variant: 'Standard',
    spec_components: 'lamp; power adapter',
    cartons_ordered: 1,
    units_per_carton_ordered: 12,
    qty_ordered: 12,
    default_photo: 'fixtures/receiving/lamp.jpg',
    notes: 'Fail-Open Resilience: Model timeout triggers PENDING_REVIEW without blocking dock',
    scenario_id: 's11',
    scenario_label: '11. Model Timeout (Fail-Open)',
    scenario_tag: 'PENDING',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 12,
      fail_open: true,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },

  // --- Additional Warehouse Inbound POs from Enterprise Catalog ---
  {
    po_number: 'PO-7000',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-7001',
    sku: 'SKU-TOWEL-BLU',
    asin: 'B0DUMMY600',
    product_title: 'Cotton Bath Towel',
    spec_colour: 'Blue',
    spec_variant: 'Bath',
    spec_components: 'towel',
    cartons_ordered: 1,
    units_per_carton_ordered: 24,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/UNIT-0001_pallet.jpg',
    notes: 'Scheduled receiving dock intake · Bay 04',
    sim_context: {
      cartons_received: 1,
      units_per_carton_counted: 24,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-7001',
    po_line: 1,
    supplier: 'Supplier East (Logistics Hub)',
    unit_id: 'UNIT-7004',
    sku: 'SKU-PROT-1KG',
    asin: 'B0DUMMY357',
    product_title: 'Whey Protein',
    spec_colour: 'n/a',
    spec_variant: '1kg Vanilla',
    spec_components: 'tub; scoop',
    cartons_ordered: 2,
    units_per_carton_ordered: 24,
    qty_ordered: 48,
    default_photo: 'fixtures/receiving/clean_pallet.jpg',
    notes: 'Inbound high-turnover inventory · Bay 02',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 24,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-7002',
    po_line: 1,
    supplier: 'Supplier North Distributors',
    unit_id: 'UNIT-7008',
    sku: 'SKU-BOTTLE-750',
    asin: 'B0DUMMY622',
    product_title: 'Steel Water Bottle',
    spec_colour: 'Black',
    spec_variant: '750ml',
    spec_components: 'bottle; lid',
    cartons_ordered: 2,
    units_per_carton_ordered: 12,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/clean_pallet.jpg',
    notes: 'Inbound beverage container shipment · Bay 01',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  },
  {
    po_number: 'PO-7003',
    po_line: 1,
    supplier: 'Supplier Coastal (DUMMY)',
    unit_id: 'UNIT-7014',
    sku: 'SKU-LAMP-LED',
    asin: 'B0DUMMY357',
    product_title: 'LED Desk Lamp',
    spec_colour: 'Grey',
    spec_variant: 'Standard',
    spec_components: 'lamp; usb cable; manual',
    cartons_ordered: 2,
    units_per_carton_ordered: 12,
    qty_ordered: 24,
    default_photo: 'fixtures/receiving/clean_pallet.jpg',
    notes: 'Electronics receiving lane · Bay 03',
    sim_context: {
      cartons_received: 2,
      units_per_carton_counted: 12,
      damage: 'none',
      spec_mismatch: false,
      id_match: 'yes'
    }
  }
];

/**
 * Returns available purchase orders.
 * In production, queries ERP API filtered by organization ID.
 */
export async function getPurchaseOrders(orgId: string): Promise<PurchaseOrderItem[]> {
  try {
    const res = await fetch(`${(import.meta.env.VITE_API_BASE_URL || '')}/api/purchase-orders`, {
      headers: { 'X-Org-ID': orgId }
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.purchase_orders) && data.purchase_orders.length > 0) {
        return data.purchase_orders;
      }
    }
  } catch (e) {
    // Graceful fallback to catalog adapter if backend endpoint is not yet queried
  }
  return PURCHASE_ORDERS_CATALOG;
}

export function getPurchaseOrderByNumber(poNumber: string): PurchaseOrderItem | undefined {
  return PURCHASE_ORDERS_CATALOG.find(p => p.po_number.toLowerCase() === poNumber.toLowerCase().trim());
}
