create or replace table mart_metric_guardrails as
select
    experiment_name,
    variant,
    avg(sessions) as sessions_per_user,
    avg(avg_session_duration_seconds) as avg_session_duration_seconds,
    avg(support_tickets) as support_tickets_per_user,
    avg(high_priority_tickets) as high_priority_tickets_per_user,
    avg(case when revenue < 0 then 1 else 0 end) as negative_revenue_user_rate
from int_user_experiment_metrics
group by 1, 2;
