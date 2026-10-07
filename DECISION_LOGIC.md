# Decision Logic

The final receiving verdict is computed by the deterministic Python decision engine, not by the AI model.

## Rules

- Any required `FAIL` => `EXCEPTION`
- No fails, but at least one `UNCERTAIN` => `UNCERTAIN`
- All required checks pass => `PASS`

## Required checks

- SKU
- quantity
- cartons
- variant
- damage
- components

## Example

```text
Expected quantity: 24
Observed quantity: 22
=> quantity_check = FAIL
=> overall decision = EXCEPTION
```

```text
Quantity cannot be reliably counted
=> quantity_check = UNCERTAIN
=> overall decision = UNCERTAIN
```

The business logic remains conservative and avoids guessing when evidence is insufficient.
