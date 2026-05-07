create or replace table mart_experiment_health as
select
    experiment_name,
    count(*) as canonical_assigned_users,
    count(distinct user_id) as distinct_users,
    sum(case when variant = 'control' then 1 else 0 end) as control_users,
    sum(case when variant = 'treatment' then 1 else 0 end) as treatment_users,
    min(assigned_at) as first_assignment_at,
    max(assigned_at) as last_assignment_at
from int_canonical_assignments
group by 1;
