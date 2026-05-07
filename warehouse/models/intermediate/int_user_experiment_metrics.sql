create or replace table int_user_experiment_metrics as
with event_metrics as (
    select
        a.experiment_name,
        a.user_id,
        count(distinct e.event_id) as events,
        count(distinct case when e.event_name = 'search' then e.event_id end) as searches,
        count(distinct case when e.event_name = 'checkout_start' then e.event_id end) as checkout_starts,
        count(distinct case when e.event_name = 'purchase' then e.event_id end) as purchase_events
    from int_canonical_assignments a
    left join stg_events e
        on a.user_id = e.user_id
       and e.event_at >= a.assigned_at
    group by 1, 2
),
session_metrics as (
    select
        a.experiment_name,
        a.user_id,
        count(distinct s.session_id) as sessions,
        avg(s.duration_seconds) as avg_session_duration_seconds
    from int_canonical_assignments a
    left join stg_sessions s
        on a.user_id = s.user_id
       and s.started_at >= a.assigned_at
    group by 1, 2
),
order_metrics as (
    select
        a.experiment_name,
        a.user_id,
        count(distinct case when o.revenue > 0 then o.order_id end) as orders,
        sum(case when o.revenue > 0 then o.revenue else 0 end) as revenue
    from int_canonical_assignments a
    left join stg_orders o
        on a.user_id = o.user_id
       and o.order_at >= a.assigned_at
    group by 1, 2
),
ticket_metrics as (
    select
        a.experiment_name,
        a.user_id,
        count(distinct t.ticket_id) as support_tickets,
        count(distinct case when t.priority in ('high', 'urgent') then t.ticket_id end) as high_priority_tickets
    from int_canonical_assignments a
    left join stg_support_tickets t
        on a.user_id = t.user_id
       and t.created_at >= a.assigned_at
    group by 1, 2
)
select
    a.experiment_name,
    a.user_id,
    a.variant,
    a.assigned_at,
    a.segment,
    a.device,
    a.region,
    a.acquisition_channel,
    coalesce(em.events, 0) as events,
    coalesce(em.searches, 0) as searches,
    coalesce(em.checkout_starts, 0) as checkout_starts,
    case when coalesce(em.purchase_events, 0) > 0 then 1 else 0 end as converted,
    coalesce(sm.sessions, 0) as sessions,
    coalesce(sm.avg_session_duration_seconds, 0) as avg_session_duration_seconds,
    coalesce(om.orders, 0) as orders,
    coalesce(om.revenue, 0) as revenue,
    coalesce(tm.support_tickets, 0) as support_tickets,
    coalesce(tm.high_priority_tickets, 0) as high_priority_tickets
from int_canonical_assignments a
left join event_metrics em
    on a.experiment_name = em.experiment_name and a.user_id = em.user_id
left join session_metrics sm
    on a.experiment_name = sm.experiment_name and a.user_id = sm.user_id
left join order_metrics om
    on a.experiment_name = om.experiment_name and a.user_id = om.user_id
left join ticket_metrics tm
    on a.experiment_name = tm.experiment_name and a.user_id = tm.user_id;
