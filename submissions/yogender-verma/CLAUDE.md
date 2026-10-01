# CLAUDE.md · Durable Constraints & Engineering Rules

## Core Non-Negotiable Rules

1. **Tenancy Isolation Before Any Feature**:
   - Every table and query MUST be scoped to `org_id`. Row-Level Security (RLS) forced.
   - Org B querying Org A's ID MUST return ZERO rows (verified in `tests/test_security_tenancy.py`).

2. **Batch Model Calls**:
   - Make ONE call per unit carrying all 5 checks (Identity, Quantity, Carton Damage, Unit Damage, Quality Flags).
   - NEVER make 1 model call per check ($1 - 1/5 = 80\%$ reduction in API calls).

3. **Fail Open**:
   - Model timeout or network error MUST save capture as `pending_review` with `UNCERTAIN` / `PENDING_REVIEW` verdicts.
   - Warehouse receiving line NEVER blocks.

4. **Uncertain as First-Class Verdict**:
   - Low visual clarity or ambiguous damage MUST output `UNCERTAIN`. It is NOT a low-confidence PASS.

5. **Look Authoritative Rules Up**:
   - Channel requirements MUST be retrieved from authoritative specification tables (`channel_rules`), not inferred from dummy CSV data.

6. **Overrides are Data**:
   - When operator modifies verdict, save original verdict, new verdict, operator ID, and mandatory justification reason in `operator_overrides`. Never delete original rows.
