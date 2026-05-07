create or replace table stg_events as
select
    cast(event_id as integer) as event_id,
    cast(session_id as integer) as session_id,
    cast(user_id as integer) as user_id,
    lower(trim(event_name)) as event_name,
    cast(event_at as timestamp) as event_at,
    lower(trim(source)) as source
from raw_events;
