create or replace table int_daily_experiment_metrics as
select
    experiment_name,
    snapshot_date,
    variant,
    segment,
    count(distinct user_id) as users,
    sum(cumulative_sessions) as cumulative_sessions,
    sum(cumulative_events) as cumulative_events,
    sum(cumulative_revenue) as cumulative_revenue
from stg_user_daily_snapshots
group by 1, 2, 3, 4;
