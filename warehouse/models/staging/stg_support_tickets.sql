create or replace table stg_support_tickets as
select
    cast(ticket_id as integer) as ticket_id,
    cast(user_id as integer) as user_id,
    cast(created_at as timestamp) as created_at,
    lower(trim(category)) as category,
    lower(trim(priority)) as priority,
    cast(first_response_minutes as integer) as first_response_minutes
from raw_support_tickets;
