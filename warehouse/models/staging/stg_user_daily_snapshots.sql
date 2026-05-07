create or replace table stg_user_daily_snapshots as
select
    cast(snapshot_date as date) as snapshot_date,
    cast(user_id as integer) as user_id,
    lower(trim(experiment_name)) as experiment_name,
    lower(trim(variant)) as variant,
    lower(trim(segment)) as segment,
    cast(cumulative_sessions as integer) as cumulative_sessions,
    cast(cumulative_events as integer) as cumulative_events,
    cast(cumulative_revenue as double) as cumulative_revenue
from raw_user_daily_snapshots;
