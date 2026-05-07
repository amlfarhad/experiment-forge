# Metrics

Metric definitions live in `config/metrics.yml`. The warehouse implements the same definitions in SQL.

## Primary Metric

`conversion_rate`

- Grain: assigned user
- Numerator: users with at least one post-assignment purchase event
- Denominator: canonically assigned users

## Secondary Metrics

- `revenue_per_user`: positive post-assignment order revenue per assigned user
- `sessions_per_user`: post-assignment sessions per assigned user
- `avg_session_duration_seconds`: average post-assignment session duration

## Guardrails

- `support_tickets_per_user`
- `sessions_per_user`
- `avg_session_duration_seconds`

These guardrails keep the readout from optimizing conversion while quietly harming engagement or customer operations.
