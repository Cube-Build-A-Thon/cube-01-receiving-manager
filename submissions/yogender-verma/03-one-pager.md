# One-Pager · Receiving Manager Agent

## Executive Summary
Supplier delivery shortages and transit defects frequently surface weeks after arrival during warehouse prep or customer fulfillment, resulting in 100% seller liability due to lack of verifiable point-of-receipt proof. Receiving Manager provides automated single-pass batch visual inspection at the receiving dock, producing standardized Evidence Contract v1.1 records for Step 02 Prep and Step 05 Recovery.

## Solution Architecture
- **Multimodal Vision Pipeline**: Executes 5 core checks in a single batch pass (Product Identity, Quantity Verification, Carton Damage, Unit Damage, and Spec Quality Flags).
- **Fail-Open Safeguard**: Preserves warehouse throughput during network or API outages by routing unverified captures to `PENDING_REVIEW` without blocking dock lines.
- **Tenancy Isolation**: Forced SQLite Row-Level Security (RLS) scoping every query to `org_id` and preventing cross-tenant record or image leakage.
- **First-Class UNCERTAIN Verdict**: Explicitly declines to guess on ambiguous or degraded photographs, routing them to supervisor review with actionable guidance.

## Metrics Table

| Metric | Target / Benchmark | Measured Result | Measurement Method & Population | Status |
|---|---|---|---|---|
| **Single-Pass Batch Execution Time** | < 1,000 ms | **6.16 ms avg** (local heuristic) / < 800 ms (Gemini API) | Measured via `time.perf_counter()` per unit across 50 runs in `backend/eval_runner.py` (range: 4.99ms – 13.89ms) | ✅ PASS |
| **Inter-Annotator Agreement (Cohen's Kappa)** | > 0.75 | **1.00** | Calculated via $\kappa = \frac{p_o - p_e}{1 - p_e}$ using dual programmatic synthetic consensus fixtures in `backend/eval_runner.py` (formula verification; not independent human annotators) | ✅ PASS |
| **Tenancy RLS Security Leak Rate** | 0.0% | **0.0% (Zero Rows)** | Verified by executing cross-tenant queries from Org Bravo targeting Org Alpha across 8 test vectors in `tests/test_security_tenancy.py` (0 rows leaked) | ✅ PASS |
| **Synthetic Fixture Decision Accuracy** | > 90.0% | **100.0%** (43 of 43 judged units) | Calculated as $\frac{TP + TN}{\text{Total} - \text{UNCERTAIN}} = \frac{18 + 25}{43}$ on 50 deterministic synthetic fixtures in `fixtures/eval/` (evaluates deterministic rule adherence) | ✅ PASS |
| **UNCERTAIN Verdict Rate** | 5.0% – 15.0% | **14.0%** (7 of 50 units) | Count of units with visual clarity index $< 0.45$ divided by total units ($7 / 50 = 14.0\%$) in `fixtures/eval/` | ✅ PASS |
| **Automated Test Suite Pass Rate** | 100.0% | **100.0% (70 of 70 passing)** | Verified via `pytest` executing 70 tests across 8 test suites (including 12 dedicated Evidence Contract v1.1 tests) in 5.26s | ✅ PASS |
| **API Call Batching Efficiency** | > 75.0% | **80.0% reduction** | Calculated as 1 batch vision call instead of 5 individual check calls per unit: $1 - \frac{1}{5} = \frac{4}{5} = 80\%$ | ✅ PASS |

## Kill Condition
If multi-tenant isolation fails to prevent cross-tenant data access, or single-pass batch inspection execution time exceeds 2,500ms on 95% of dock captures, the agent is halted immediately.
