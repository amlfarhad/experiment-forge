# Experiment Quality Audit

Overall status: **FAIL**

| Check | Status | Severity | Observed | Threshold | Detail |
|---|---:|---:|---:|---:|---|
| sample_ratio_mismatch | PASS | critical | 0.005389129493047165 | 0.001 | Assignment split p-value is 0.00539. |
| duplicate_assignments | FAIL | critical | 8 | 0 | 8 duplicate experiment/user assignment rows found. |
| multiple_variant_assignments | FAIL | critical | 2 | 0 | 2 users were assigned to multiple variants. |
| missing_assignment_timestamps | PASS | critical | 0 | 0 | 0 assignment timestamps are missing. |
| events_before_assignment | FAIL | critical | 12 | 0 | 12 events occurred before canonical assignment. |
| null_event_names | WARN | warning | 15 | 0 | 15 events have null event_name values. |
| negative_revenue | FAIL | critical | 2 | 0 | 2 order rows have negative revenue without refund modeling. |
| mart_experiment_readout_rows | PASS | critical | 2 | 2 | mart_experiment_readout has 2 rows. |
| mart_segment_readout_rows | PASS | critical | 6 | 6 | mart_segment_readout has 6 rows. |
| guardrail_sessions_per_user | PASS | warning | 1.0750624957773123 | 0.98 | Treatment/control sessions per user ratio is 1.075. |
