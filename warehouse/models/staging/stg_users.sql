create or replace table stg_users as
select
    cast(user_id as integer) as user_id,
    cast(signup_date as date) as signup_date,
    lower(trim(segment)) as segment,
    lower(trim(device)) as device,
    lower(trim(region)) as region,
    lower(trim(acquisition_channel)) as acquisition_channel
from raw_users;
