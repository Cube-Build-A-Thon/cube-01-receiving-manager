# Evaluation Report · Receiving Manager Agent

**Participant:** Yogender Verma  
**Repository Fork:** `cube26-rcv-0088-yogender-verma`  
**Track:** 01 · Receiving Manager (Step 1 of 5 in Commerce Stream)  
**Evaluation Target:** Single-Pass Batch Vision Receiving Inspection Agent (`ReceivingManagerAgent`)  
**Methodology:** Deterministic Rule & Heuristic Validation on Synthetic Fixture Suite  

---

## 1. Executive Summary & Honest Methodology Statement

Evaluation was conducted against a test suite of **50 synthetic units** (`EVAL-UNIT-0001` through `EVAL-UNIT-0050`) generated deterministically to validate rule enforcement, schema safety, fail-open circuit breaking, and uncertainty propagation across five core receiving dimensions: SKU Identity, Quantity Verification, Carton Damage, Unit Damage, and Spec Quality.

### Methodology Disclosures:
- **Synthetic Data:** All 50 units and images are programmatic synthetic fixtures generated with Pillow (`fixtures_generator.py`). They are not human-captured real warehouse dock photographs.
- **Annotators:** "Labeller A" and "Labeller B" are programmatic consensus fixtures used to validate the implementation of the Cohen's Kappa scoring formula, not independent human auditors.
- **Metric Scope:** The 100% accuracy result represents **Synthetic Fixture Decision Accuracy** (exact agreement between deterministic rules and synthetic fixtures). It demonstrates rule adherence and schema compliance, but does not claim empirical open-world generalization.
- **AI Separation:** Runs in **Demo Mode (Synthetic Heuristic Engine)** by default when `GEMINI_API_KEY` is not set; invokes **Real AI Mode (Google Gemini Multimodal API)** when `GEMINI_API_KEY` is configured. If live AI fails, it triggers the fail-open circuit breaker and never silently fabricates mock results.

### Key Metrics:
- **Total Units Evaluated:** 50
- **Evaluation Type:** Synthetic Fixture Rule Validation
- **Cohen's Kappa (Formula Verification):** **1.00** (calculated via $\kappa = \frac{p_o - p_e}{1 - p_e}$ using programmatic consensus labels)
- **Synthetic Fixture Decision Accuracy (excl. UNCERTAIN):** **100.0%** (43 of 43 judged units match rule specs; $\frac{18+25}{43} = 100.0\%$)
- **Precision:** **1.000** ($\frac{TP}{TP + FP} = \frac{18}{18 + 0}$)
- **Recall:** **1.000** ($\frac{TP}{TP + FN} = \frac{18}{18 + 0}$)
- **F1-Score:** **1.000** ($2 \times \frac{P \times R}{P + R}$)
- **False Positives (FP):** **0** (per-check comparison against synthetic specs)
- **False Negatives (FN):** **0** (per-check comparison against synthetic specs)
- **UNCERTAIN Verdict Rate:** **14.0% (7 units)** (Cleanly identified due to visual clarity index $< 0.45$; $7 / 50 = 14.0\%$)
- **Fail-Open Recovery Rate:** **100%** (Timeouts produce `PENDING_REVIEW`; retry re-evaluates cleanly)
- **Single-Pass Heuristic Latency:** **6.16 ms average** across 50 runs (measured via `time.perf_counter()`; min 4.99ms, max 13.89ms)

---

## 2. Dataset Composition Table

| Scenario Category | Unit ID Range | Count | Ground Truth | Visual Evidence State |
|---|---|---|---|---|
| **Clean Inbound (PASS)** | `EVAL-0001` – `EVAL-0025` | 25 | **PASS** | Intact cartons, matching SKU barcode, verified 24/24 count |
| **Carton Crushing (FAIL)** | `EVAL-0026` – `EVAL-0035` | 10 | **FAIL** | Visible corner deformation, structural compression |
| **Spec / Component Mismatch (FAIL)** | `EVAL-0036` – `EVAL-0043` | 8 | **FAIL** | Wrong colour (Red vs Blue), missing accessories (no scoop) |
| **Ambiguous / Occluded (UNCERTAIN)** | `EVAL-0044` – `EVAL-0050` | 7 | **UNCERTAIN** | Severe motion blur, warehouse spotlight glare, unreadable barcode |

---

## 3. Confusion Matrix

| Metric | Ground Truth EXCEPTION (FAIL) | Ground Truth PASS | Ground Truth UNCERTAIN |
|---|---|---|---|
| **Agent EXCEPTION (FAIL)** | **18 (TP)** | 0 (FP) | 0 |
| **Agent PASS** | 0 (FN) | **25 (TN)** | 0 |
| **Agent UNCERTAIN** | 0 | 0 | **7 (Correct Uncertainty)** |

---

## 4. Per-Check Sub-Dimension Metrics (Dynamically Computed)

| Check Name | Evaluated Units | Accuracy on Evaluated | False Positives | False Negatives | UNCERTAIN Count | Measurement Method |
|---|---|---|---|---|---|---|
| **Product / SKU Identity** | 43 | 100.0% | 0 | 0 | 7 | $\frac{\text{Correct}}{\text{Evaluated}} = \frac{43}{43}$; 7 units deferred due to clarity $< 0.45$ |
| **Quantity Verification** | 50 | 100.0% | 0 | 0 | 0 | $\frac{\text{Correct}}{\text{Evaluated}} = \frac{50}{50}$; carton $\times$ unit multiplication comparison |
| **Carton Physical Damage** | 43 | 100.0% | 0 | 0 | 7 | $\frac{\text{Correct}}{\text{Evaluated}} = \frac{43}{43}$; deformation detection vs expected labels |
| **Unit Physical Damage** | 43 | 100.0% | 0 | 0 | 7 | $\frac{\text{Correct}}{\text{Evaluated}} = \frac{43}{43}$; visual unit inspection vs expected labels |
| **Spec Quality Flags** | 50 | 100.0% | 0 | 0 | 0 | $\frac{\text{Correct}}{\text{Evaluated}} = \frac{50}{50}$; set equality comparison vs expected flags |

---

## 5. Documented Failure Modes

1. **Visual Glare & Polybag Reflection:** Ceiling lighting reflecting on shrink wrap (7 units). Correctly routed to UNCERTAIN.
2. **Subtle Corner Compression:** Corner compression < 10% volume requires multi-angle captures.
3. **Foreign Supplier Typography:** Non-standard dot-matrix fonts require fallback to barcode scanning.
4. **Sealed Packaging:** Directly observed count separated from inferred count to prevent hallucination.
