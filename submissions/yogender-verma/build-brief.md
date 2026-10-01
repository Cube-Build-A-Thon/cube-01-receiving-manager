# Build Brief · Receiving Manager (Step 01 of 5)

## Overview
Receiving Manager is the first link in the 5-stage e-commerce chain (Receiving -> Prep -> Pack -> Returns -> Recovery).
It records supplier delivery condition from dock photographs.

## Objectives
- Implement single-pass batch vision agent evaluating 5 core checks.
- Enforce tenancy RLS across `org_demo_alpha` and `org_demo_bravo`.
- Implement fail-open safeguard and first-class uncertainty handling.
- Export standardized evidence JSON contract matching Cube Evidence Contract v1.1 for Step 02 Prep and Step 05 Recovery.
