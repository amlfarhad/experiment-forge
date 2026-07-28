# Data Quality

Product Experiments treats data validity as part of experimentation, not as a cleanup step after analysis.

## Check Groups

| Group | Checks |
|---|---|
| Assignment validity | sample ratio mismatch, duplicate assignments, users assigned to multiple variants |
| Source completeness | missing assignment timestamps, null event names |
| Temporal validity | events before assignment |
| Metric validity | negative revenue, required mart row counts |
| Guardrails | sessions-per-user treatment/control ratio |

## Severity

- `critical`: should block launch decisions.
- `warning`: should be reviewed but may not block analysis alone.

The demo data intentionally includes a few failures so the audit report shows how the platform behaves when experiment data is not trustworthy.
