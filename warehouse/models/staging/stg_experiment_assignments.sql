create or replace table stg_experiment_assignments as
select
    cast(assignment_id as integer) as assignment_id,
    lower(trim(experiment_name)) as experiment_name,
    cast(user_id as integer) as user_id,
    lower(trim(variant)) as variant,
    cast(assigned_at as timestamp) as assigned_at
from raw_experiment_assignments;
