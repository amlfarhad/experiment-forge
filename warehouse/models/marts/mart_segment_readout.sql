create or replace table mart_segment_readout as
select
    experiment_name,
    segment,
    variant,
    count(*) as assigned_users,
    avg(converted) as conversion_rate,
    avg(revenue) as revenue_per_user,
    avg(sessions) as sessions_per_user,
    avg(support_tickets) as support_tickets_per_user
from int_user_experiment_metrics
group by 1, 2, 3;
