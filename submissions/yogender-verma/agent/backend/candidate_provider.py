"""
Candidate Product Provider Interface & Catalog Adapter (Rule 4 / Priority 4 & 5)
Provides candidate product sets for multi-class visual SKU discrimination.
"""

from typing import List, Dict, Any, Optional
import os
import csv

class CandidateProvider:
    """
    Candidate Product Provider Interface & Catalog Adapter.
    In enterprise deployments, this connects to product master databases, ERP,
    or vector-embedding nearest-neighbor SKU search.
    In the current repository, it adapts available product catalog records from receiving data.
    """
    def __init__(self, catalog_csv_path: Optional[str] = None):
        self.catalog_csv_path = catalog_csv_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "receiving_sample.csv")
        )
        self._catalog_items = self._load_catalog()

    def _load_catalog(self) -> List[Dict[str, Any]]:
        items = []
        seen_skus = set()
        if os.path.exists(self.catalog_csv_path):
            try:
                with open(self.catalog_csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sku = row.get("sku", "").strip()
                        if sku and sku not in seen_skus:
                            seen_skus.add(sku)
                            items.append({
                                "sku": sku,
                                "asin": row.get("asin", ""),
                                "product_title": row.get("product_title", ""),
                                "spec_colour": row.get("spec_colour", ""),
                                "spec_variant": row.get("spec_variant", ""),
                                "spec_components": row.get("spec_components", "")
                            })
            except Exception:
                pass
        
        # Fallback baseline catalog if CSV is missing or empty
        if not items:
            items = [
                {"sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Stainless Steel Bottle", "spec_colour": "Blue", "spec_variant": "Standard", "spec_components": "bottle; lid"},
                {"sku": "SKU-BOTTLE-750", "asin": "B0DUMMY622", "product_title": "Steel Water Bottle", "spec_colour": "black", "spec_variant": "750ml", "spec_components": "bottle; lid"},
                {"sku": "SKU-MUG-11", "asin": "B0DUMMY351", "product_title": "Ceramic Mug 11oz, set of 2", "spec_colour": "white", "spec_variant": "11oz", "spec_components": "mug x2"},
                {"sku": "RED-MUG-002", "asin": "B0002REDMUG", "product_title": "Ceramic Red Mug", "spec_colour": "red", "spec_variant": "11oz", "spec_components": "mug x1"},
                {"sku": "SKU-TOWEL-BLU", "asin": "B0DUMMY600", "product_title": "Cotton Bath Towel", "spec_colour": "blue", "spec_variant": "bath", "spec_components": "towel"},
                {"sku": "SKU-CANDLE-3", "asin": "B0DUMMY964", "product_title": "Soy Candle Trio", "spec_colour": "cream", "spec_variant": "3-pack", "spec_components": "candle x3; gift box"},
                {"sku": "SKU-LAMP-LED", "asin": "B0DUMMY357", "product_title": "LED Desk Lamp", "spec_colour": "grey", "spec_variant": "standard", "spec_components": "lamp; usb cable; manual"},
                {"sku": "SKU-PROT-1KG", "asin": "B0DUMMY357", "product_title": "Whey Protein Tub", "spec_colour": "n/a", "spec_variant": "1kg vanilla", "spec_components": "tub; scoop"}
            ]
        return items

    def get_candidate_set(self, expected_sku: str, po_spec: Dict[str, Any], max_candidates: int = 4) -> List[Dict[str, Any]]:
        """
        Builds a candidate product list containing the expected SKU plus plausible catalogue decoys/alternatives.
        """
        candidates = []
        
        # 1. Candidate 1 is the Expected SKU
        expected_candidate = {
            "sku": expected_sku,
            "product_title": po_spec.get("product_title", "Expected Product"),
            "spec_colour": po_spec.get("spec_colour", "n/a"),
            "spec_variant": po_spec.get("spec_variant", "n/a"),
            "spec_components": po_spec.get("spec_components", "n/a"),
            "is_expected": True
        }
        candidates.append(expected_candidate)
        
        # 2. Select look-alikes or catalogue alternatives from available catalog items
        for item in self._catalog_items:
            if item["sku"].lower() != expected_sku.lower():
                candidates.append({
                    "sku": item["sku"],
                    "product_title": item["product_title"],
                    "spec_colour": item.get("spec_colour", "n/a"),
                    "spec_variant": item.get("spec_variant", "n/a"),
                    "spec_components": item.get("spec_components", "n/a"),
                    "is_expected": False
                })
            if len(candidates) >= max_candidates:
                break
                
        return candidates

# Singleton instance for repository-wide reuse
candidate_provider = CandidateProvider()
