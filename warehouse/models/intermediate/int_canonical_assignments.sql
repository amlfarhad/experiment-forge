create or replace table int_canonical_assignments as
with ranked as (
    select
        a.*,
        row_number() over (
            partition by experiment_name, user_id
            order by assigned_at, assignment_id
        ) as assignment_rank
    from stg_experiment_assignments a
)
select
    r.experiment_name,
    r.user_id,
    r.variant,
    r.assigned_at,
    u.segment,
    u.device,
    u.region,
    u.acquisition_channel
from ranked r
left join stg_users u
    on r.user_id = u.user_id
where r.assignment_rank = 1;
