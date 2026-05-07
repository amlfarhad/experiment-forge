create or replace table mart_experiment_readout as
select
    experiment_name,
    variant,
    count(*) as assigned_users,
    sum(converted) as conversions,
    avg(converted) as conversion_rate,
    sum(revenue) as total_revenue,
    avg(revenue) as revenue_per_user,
    avg(sessions) as sessions_per_user,
    avg(avg_session_duration_seconds) as avg_session_duration_seconds,
    avg(support_tickets) as support_tickets_per_user,
    avg(high_priority_tickets) as high_priority_tickets_per_user
from int_user_experiment_metrics
group by 1, 2;
