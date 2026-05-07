create or replace table stg_orders as
select
    cast(order_id as integer) as order_id,
    cast(user_id as integer) as user_id,
    cast(session_id as integer) as session_id,
    cast(order_at as timestamp) as order_at,
    cast(revenue as double) as revenue,
    upper(trim(currency)) as currency
from raw_orders;
