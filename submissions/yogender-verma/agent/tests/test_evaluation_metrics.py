"""
Automated Evaluation Metrics & Held-Out Suite Test
Tests:
- Execution of 50 held-out evaluation units
- Dual annotator agreement (Cohen's Kappa)
- Calculation of Precision, Recall, F1, TP, TN, FP, FN
- Measurement of UNCERTAIN rate
- Failure mode categorization
"""

import pytest
from backend.eval_runner import run_evaluation_suite, calculate_cohens_kappa

def test_cohens_kappa_perfect_agreement():
    labels_a = ["PASS", "FAIL", "UNCERTAIN", "PASS"]
    labels_b = ["PASS", "FAIL", "UNCERTAIN", "PASS"]
    assert calculate_cohens_kappa(labels_a, labels_b) == 1.0

def test_cohens_kappa_partial_agreement():
    labels_a = ["PASS", "FAIL", "PASS", "PASS"]
    labels_b = ["PASS", "FAIL", "FAIL", "PASS"]
    kappa = calculate_cohens_kappa(labels_a, labels_b)
    assert 0.0 < kappa < 1.0

def test_run_evaluation_suite_complete_metrics():
    eval_result = run_evaluation_suite()
    assert "evaluation_summary" in eval_result
    summary = eval_result["evaluation_summary"]

    assert summary["total_units_evaluated"] == 50
    assert summary["cohens_kappa_inter_annotator_agreement"] > 0.80
    assert summary["precision"] > 0.85
    assert summary["recall"] > 0.85
    assert summary["f1_score"] > 0.85
    assert summary["uncertain_verdicts_count"] >= 5
    assert summary["uncertain_rate_pct"] > 0.0

    # Verify per-check metrics
    assert "per_check_metrics" in eval_result
    pcm = eval_result["per_check_metrics"]
    for check in ["identity_match", "quantity_verification", "carton_damage", "unit_damage", "quality_flags"]:
        assert check in pcm
        assert "accuracy" in pcm[check]
        assert "fp" in pcm[check]
        assert "fn" in pcm[check]

    # Verify failure modes
    assert "failure_modes_breakdown" in eval_result
    fmb = eval_result["failure_modes_breakdown"]
    assert "visual_glare_reflections" in fmb
    assert "subtle_crushing_corner_occlusion" in fmb
    assert "spec_variant_text_resolution" in fmb
