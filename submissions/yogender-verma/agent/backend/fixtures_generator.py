"""
Deterministic Fixture & Synthetic Image Generator for CUBE Track RCV#1
Creates deterministic, reproducible test images for all 14 required evaluation scenarios.

CRITICAL COMPLIANCE RULE:
Every generated image is prominently stamped:
"DEMO / SYNTHETIC FIXTURE - [SCENARIO]"
Never presented as real warehouse evidence.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
RECEIVING_DIR = os.path.join(FIXTURES_DIR, "receiving")
EVAL_DIR = os.path.join(FIXTURES_DIR, "eval")
ALPHA_DIR = os.path.join(FIXTURES_DIR, "org_demo_alpha")
BRAVO_DIR = os.path.join(FIXTURES_DIR, "org_demo_bravo")

def ensure_dirs():
    for d in [FIXTURES_DIR, RECEIVING_DIR, EVAL_DIR, ALPHA_DIR, BRAVO_DIR]:
        os.makedirs(d, exist_ok=True)

def draw_header_banner(draw, width, scenario_name, defect_type="NONE"):
    # Dark industrial header
    draw.rectangle([(0, 0), (width, 60)], fill="#0f172a")
    # Top accent line
    accent_color = "#10b981" if defect_type == "NONE" else ("#f59e0b" if defect_type == "UNCERTAIN" else "#ef4444")
    draw.rectangle([(0, 0), (width, 4)], fill=accent_color)
    
    # Text watermarks
    draw.text((15, 12), "DEMO / SYNTHETIC FIXTURE", fill="#94a3b8")
    draw.text((15, 32), f"SCENARIO: {scenario_name.upper()} | STATUS: {defect_type}", fill="#ffffff")

def create_base_carton(width=640, height=480, carton_color="#c29b68", bg_color="#1e293b"):
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Warehouse dock floor pattern
    for y in range(350, height, 25):
        draw.line([(0, y), (width, y)], fill="#334155", width=1)
    
    # Wooden pallet base
    draw.rectangle([(80, 360), (560, 400)], fill="#78350f", outline="#451a03", width=2)
    for x in range(120, 530, 80):
        draw.rectangle([(x, 380), (x+40, 400)], fill="#451a03")
        
    # Main Carton
    carton_box = [(140, 140), (500, 360)]
    draw.rectangle(carton_box, fill=carton_color, outline="#78350f", width=3)
    
    # Center carton sealing tape
    draw.rectangle([(305, 140), (335, 360)], fill="#d97706", outline="#b45309", width=1)
    
    # Shipping Label on Carton
    draw.rectangle([(160, 180), (280, 300)], fill="#ffffff", outline="#64748b", width=1)
    draw.text((170, 190), "SHIP TO: DOCK-01", fill="#000000")
    draw.text((170, 205), "CARRIER: FBA-EXP", fill="#000000")
    
    # Barcode representation
    for bx in range(170, 270, 5):
        w = 3 if bx % 10 == 0 else 1
        draw.line([(bx, 225), (bx, 260)], fill="#000000", width=w)
    draw.text((170, 268), "FNSKU: X00123AB", fill="#000000")
    
    return img, draw

def generate_clean_shipment(filename, sku="BLUE-BOTTLE-001", variant="Blue"):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Correct Shipment (PASS)", "NONE")
    draw.text((170, 282), f"SKU: {sku}", fill="#1e3a8a")
    
    # Draw product preview inset
    draw.rectangle([(360, 180), (470, 310)], fill="#ffffff", outline="#3b82f6", width=2)
    draw.text((370, 188), f"ITEM: {variant}", fill="#0f172a")
    # Draw bottle silhouette
    bottle_color = "#2563eb" if variant.lower() == "blue" else "#dc2626"
    draw.rectangle([(400, 230), (430, 290)], fill=bottle_color)
    draw.rectangle([(408, 215), (422, 230)], fill="#94a3b8")
    draw.text((370, 292), "UNITS: 24/24 OK", fill="#16a34a")
    
    img.save(filename, "JPEG", quality=90)

def generate_short_shipment(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Short Shipment (Qty Discrepancy)", "FAIL")
    draw.rectangle([(360, 180), (475, 310)], fill="#fef2f2", outline="#ef4444", width=2)
    draw.text((370, 188), "COUNT DISCREPANCY", fill="#b91c1c")
    draw.text((370, 210), "EXP: 24 UNITS", fill="#475569")
    draw.text((370, 230), "OBS: 20 UNITS", fill="#b91c1c")
    draw.text((370, 255), "DELTA: -4 UNITS", fill="#dc2626")
    # Missing slot visual
    draw.rectangle([(370, 280), (410, 300)], fill="#fee2e2", outline="#ef4444")
    draw.text((375, 283), "EMPTY", fill="#b91c1c")
    img.save(filename, "JPEG", quality=90)

def generate_extra_units(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Extra Units (Over-shipment)", "FAIL")
    draw.rectangle([(360, 180), (475, 310)], fill="#fffbeb", outline="#d97706", width=2)
    draw.text((370, 188), "OVER-SHIPMENT", fill="#b45309")
    draw.text((370, 210), "EXP: 24 UNITS", fill="#475569")
    draw.text((370, 230), "OBS: 28 UNITS", fill="#b45309")
    draw.text((370, 255), "DELTA: +4 EXTRA", fill="#d97706")
    img.save(filename, "JPEG", quality=90)

def generate_wrong_sku(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Wrong SKU Identity", "FAIL")
    # Overwrite shipping label with incorrect SKU
    draw.rectangle([(160, 180), (285, 305)], fill="#fef2f2", outline="#dc2626", width=2)
    draw.text((170, 190), "LABEL IDENTITY MISMATCH", fill="#b91c1c")
    draw.text((170, 215), "OBSERVED SKU:", fill="#475569")
    draw.text((170, 230), "RED-MUG-002", fill="#b91c1c")
    draw.text((170, 255), "EXPECTED SKU:", fill="#475569")
    draw.text((170, 270), "BLUE-BOTTLE-001", fill="#16a34a")
    img.save(filename, "JPEG", quality=90)

def generate_wrong_variant(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Wrong Variant / Colour", "FAIL")
    draw.rectangle([(360, 180), (475, 310)], fill="#fef2f2", outline="#dc2626", width=2)
    draw.text((370, 188), "VARIANT MISMATCH", fill="#b91c1c")
    draw.text((370, 208), "EXP: Blue", fill="#16a34a")
    draw.text((370, 224), "OBS: Red", fill="#b91c1c")
    # Red bottle drawn instead of blue
    draw.rectangle([(400, 245), (430, 295)], fill="#dc2626", outline="#7f1d1d")
    draw.rectangle([(408, 235), (422, 245)], fill="#94a3b8")
    img.save(filename, "JPEG", quality=90)

def generate_crushed_carton(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Crushed Carton Damage", "FAIL")
    # Draw crushing damage on top-left corner
    crush_polygon = [(140, 140), (230, 140), (190, 210), (140, 230)]
    draw.polygon(crush_polygon, fill="#92400e", outline="#451a03")
    draw.line([(140, 140), (190, 210)], fill="#451a03", width=4)
    draw.line([(190, 210), (230, 140)], fill="#451a03", width=3)
    draw.line([(160, 175), (140, 230)], fill="#451a03", width=3)
    
    # Highlight bounding box
    draw.rectangle([(130, 130), (240, 240)], outline="#ef4444", width=3)
    draw.rectangle([(130, 105), (240, 130)], fill="#ef4444")
    draw.text((135, 110), "DEFECT: CRUSHING", fill="#ffffff")
    img.save(filename, "JPEG", quality=90)

def generate_water_damage(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Water Damage / Moisture Stain", "FAIL")
    # Draw dark irregular moisture seep ring at bottom of carton
    draw.ellipse([(200, 280), (440, 360)], fill="#78350f", outline="#451a03", width=2)
    draw.ellipse([(240, 300), (400, 355)], fill="#451a03")
    
    # Defect Callout Box
    draw.rectangle([(190, 270), (450, 365)], outline="#ef4444", width=3)
    draw.rectangle([(190, 245), (330, 270)], fill="#ef4444")
    draw.text((195, 250), "DEFECT: WATER INTRUSION", fill="#ffffff")
    img.save(filename, "JPEG", quality=90)

def generate_torn_packaging(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Torn Packaging Defect", "FAIL")
    # Jagged tear lines on right side
    tear_pts = [(420, 200), (450, 220), (430, 245), (465, 270), (440, 290), (420, 260)]
    draw.polygon(tear_pts, fill="#1e293b", outline="#ef4444", width=2)
    
    # Defect Callout
    draw.rectangle([(410, 190), (475, 300)], outline="#ef4444", width=3)
    draw.rectangle([(390, 165), (495, 190)], fill="#ef4444")
    draw.text((395, 170), "DEFECT: PACK TEAR", fill="#ffffff")
    img.save(filename, "JPEG", quality=90)

def generate_missing_component(filename):
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Missing Component (Scoop / Accessory)", "FAIL")
    draw.rectangle([(350, 180), (485, 320)], fill="#fef2f2", outline="#dc2626", width=2)
    draw.text((360, 188), "MISSING ACCESSORY", fill="#b91c1c")
    draw.text((360, 208), "SPEC: Tub + Scoop", fill="#475569")
    draw.text((360, 228), "OBS: Tub Only", fill="#b91c1c")
    draw.rectangle([(370, 255), (420, 305)], fill="#93c5fd", outline="#1d4ed8") # Tub
    draw.text((375, 275), "TUB", fill="#1e3a8a")
    # Dotted missing scoop outline
    draw.rectangle([(430, 265), (470, 295)], fill="#fee2e2", outline="#dc2626", width=2)
    draw.text((435, 273), "[?]", fill="#dc2626")
    img.save(filename, "JPEG", quality=90)

def generate_ambiguous_case(filename):
    # Severe blur and dark glare condition causing UNCERTAIN outcome
    img, draw = create_base_carton()
    draw_header_banner(draw, 640, "Ambiguous Case (Blur / Glare)", "UNCERTAIN")
    draw.text((150, 200), "LOW LIGHT & MOTION OCCLUSION", fill="#fbbf24")
    
    # Add simulated heavy blur and glare circle
    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    draw2 = ImageDraw.Draw(img)
    # Bright glare spot
    draw2.ellipse([(200, 160), (380, 320)], fill="#ffffff")
    draw_header_banner(draw2, 640, "Ambiguous Case (Blur / Glare)", "UNCERTAIN")
    draw2.rectangle([(160, 340), (480, 380)], fill="#0f172a", outline="#fbbf24", width=2)
    draw2.text((170, 350), "UNCERTAIN: Visual clarity below reliable threshold (0.35 < 0.60)", fill="#fbbf24")
    img.save(filename, "JPEG", quality=80)

def generate_all_fixtures():
    ensure_dirs()
    print("Generating deterministic test fixtures...")
    
    # 1. Clean Pallet / Standard PASS
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "clean_pallet.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "default_pallet.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "UNIT-0001_pallet.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "UNIT-0001_carton.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "UNIT-0001_unit.jpg"))
    generate_clean_shipment(os.path.join(ALPHA_DIR, "UNIT-0001_pallet.jpg"))
    
    # 2. Short Shipment
    generate_short_shipment(os.path.join(RECEIVING_DIR, "short_shipment.jpg"))
    generate_short_shipment(os.path.join(RECEIVING_DIR, "UNIT-0002_carton_short.jpg"))
    generate_short_shipment(os.path.join(ALPHA_DIR, "UNIT-0002_short.jpg"))
    
    # 3. Extra Units
    generate_extra_units(os.path.join(RECEIVING_DIR, "extra_units.jpg"))
    generate_extra_units(os.path.join(RECEIVING_DIR, "UNIT-0003_carton_extra.jpg"))
    generate_extra_units(os.path.join(ALPHA_DIR, "UNIT-0003_extra.jpg"))
    
    # 4. Wrong SKU
    generate_wrong_sku(os.path.join(RECEIVING_DIR, "wrong_sku.jpg"))
    generate_wrong_sku(os.path.join(RECEIVING_DIR, "UNIT-0004_carton_wrong_sku.jpg"))
    generate_wrong_sku(os.path.join(ALPHA_DIR, "UNIT-0004_wrong_sku.jpg"))
    
    # 5. Wrong Variant
    generate_wrong_variant(os.path.join(RECEIVING_DIR, "red_variant.jpg"))
    generate_wrong_variant(os.path.join(RECEIVING_DIR, "UNIT-0005_carton_wrong_variant.jpg"))
    generate_wrong_variant(os.path.join(ALPHA_DIR, "UNIT-0005_wrong_variant.jpg"))
    
    # 6. Crushed Carton
    generate_crushed_carton(os.path.join(RECEIVING_DIR, "pallet_crushing.jpg"))
    generate_crushed_carton(os.path.join(RECEIVING_DIR, "UNIT-0006_carton_crushing.jpg"))
    generate_crushed_carton(os.path.join(ALPHA_DIR, "UNIT-0006_crushing.jpg"))
    
    # 7. Water Damage
    generate_water_damage(os.path.join(RECEIVING_DIR, "carton_water_soaked.jpg"))
    generate_water_damage(os.path.join(RECEIVING_DIR, "UNIT-0007_carton_water.jpg"))
    generate_water_damage(os.path.join(ALPHA_DIR, "UNIT-0007_water.jpg"))
    
    # 8. Torn Packaging
    generate_torn_packaging(os.path.join(RECEIVING_DIR, "packaging_tears.jpg"))
    generate_torn_packaging(os.path.join(RECEIVING_DIR, "UNIT-0008_carton_tears.jpg"))
    generate_torn_packaging(os.path.join(ALPHA_DIR, "UNIT-0008_tears.jpg"))
    
    # 9. Missing Component
    generate_missing_component(os.path.join(RECEIVING_DIR, "missing_scoop.jpg"))
    generate_missing_component(os.path.join(RECEIVING_DIR, "UNIT-0009_missing_component.jpg"))
    generate_missing_component(os.path.join(ALPHA_DIR, "UNIT-0009_missing_component.jpg"))
    
    # 10. Ambiguous Case (UNCERTAIN)
    generate_ambiguous_case(os.path.join(RECEIVING_DIR, "blur_dark_occluded.jpg"))
    generate_ambiguous_case(os.path.join(RECEIVING_DIR, "UNIT-0010_blur_dark.jpg"))
    generate_ambiguous_case(os.path.join(ALPHA_DIR, "UNIT-0010_blur.jpg"))
    
    # 11. Model Failure simulation fixture
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "lamp.jpg"), sku="LAMP-LED", variant="LED")
    generate_clean_shipment(os.path.join(ALPHA_DIR, "UNIT-0011_lamp.jpg"), sku="LAMP-LED", variant="LED")
    
    # 12. Multi-image fixtures
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "pallet_overall.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "carton_label.jpg"))
    generate_clean_shipment(os.path.join(RECEIVING_DIR, "unit_contents.jpg"))
    generate_clean_shipment(os.path.join(ALPHA_DIR, "UNIT-0012_multi_1.jpg"))
    generate_clean_shipment(os.path.join(ALPHA_DIR, "UNIT-0012_multi_2.jpg"))
    generate_clean_shipment(os.path.join(ALPHA_DIR, "UNIT-0012_multi_3.jpg"))
    
    # 13. Operator Override fixture
    generate_crushed_carton(os.path.join(RECEIVING_DIR, "UNIT-0013_operator_override.jpg"))
    generate_crushed_carton(os.path.join(ALPHA_DIR, "UNIT-0013_override.jpg"))
    
    # 14. Tenant Isolation Fixture (Org Bravo secure container)
    img_bravo, draw_bravo = create_base_carton(carton_color="#475569")
    draw_header_banner(draw_bravo, 640, "Org Bravo Secure Container", "NONE")
    draw_bravo.text((170, 282), "TENANT: org_demo_bravo SECURE", fill="#3b82f6")
    img_bravo.save(os.path.join(BRAVO_DIR, "UNIT-0014_bravo_secure.jpg"), "JPEG", quality=90)
    
    # Generate 50 held-out evaluation fixtures in fixtures/eval/
    for i in range(1, 26):
        generate_clean_shipment(os.path.join(EVAL_DIR, f"EVAL-{i:04d}_pallet.jpg"), sku=f"SKU-EVAL-{i:02d}")
    for i in range(26, 36):
        generate_crushed_carton(os.path.join(EVAL_DIR, f"EVAL-{i:04d}_crushing.jpg"))
    for i in range(36, 44):
        generate_wrong_variant(os.path.join(EVAL_DIR, f"EVAL-{i:04d}_wrong_variant.jpg"))
    for i in range(44, 51):
        generate_ambiguous_case(os.path.join(EVAL_DIR, f"EVAL-{i:04d}_blur_dark.jpg"))
        
    print(f"Fixture generation complete! All files generated in {FIXTURES_DIR}")

if __name__ == "__main__":
    generate_all_fixtures()
