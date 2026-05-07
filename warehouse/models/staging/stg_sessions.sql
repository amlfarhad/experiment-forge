create or replace table stg_sessions as
select
    cast(session_id as integer) as session_id,
    cast(user_id as integer) as user_id,
    cast(started_at as timestamp) as started_at,
    cast(duration_seconds as integer) as duration_seconds,
    lower(trim(device)) as device
from raw_sessions;
