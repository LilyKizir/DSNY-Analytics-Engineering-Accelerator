with fact_sub as (
    select * from {{ ref('fact_subregional_demand') }}
),

fact_reg as (
    select * from {{ ref('fact_regional_operating_metrics') }}
),

dim_sub_ba as (
    select * from {{ ref('dim_sub_balancing_authority') }}
),

dim_ba as (
    select * from {{ ref('dim_balancing_authority') }}
),

-- Aggregate sub-regional utility demand to daily grain
daily_sub_ba_load as (
    select
        s.post_date as operating_date,
        s.ba_code,
        s.sub_ba_code,
        
        sum(s.value_mwh::numeric(18,2)) as total_sub_ba_demand_mwh,
        max(s.value_mwh::numeric(18,2)) as peak_sub_ba_demand_mw,
        avg(s.value_mwh::numeric(18,2)) as avg_sub_ba_demand_mw

    from fact_sub s
    group by 1, 2, 3
),

-- Aggregate total parent BA daily demand for context and share calculations
daily_parent_ba_load as (
    select
        r.post_date as operating_date,
        r.ba_code,
        sum(r.value_mwh::numeric(18,2)) as total_parent_ba_demand_mwh
    from fact_reg r
    where r.type_code = 'D'
    group by 1, 2
)

-- Final model joining load profiles and computing business KPIs
select
    sub.operating_date,
    sub.ba_code,
    b.ba_name,
    sub.sub_ba_code,
    sb.sub_ba_name,

    -- Absolute Sub-Regional Volumes
    sub.total_sub_ba_demand_mwh,
    sub.peak_sub_ba_demand_mw,
    round(sub.avg_sub_ba_demand_mw, 2) as avg_sub_ba_demand_mw,

    -- Load Factor: Measures demand stability (1.0 = flat demand, closer to 0.0 = volatile peak spikes)
    -- lf = (total energy usedn (in units/time period)/(peak demand (units) *))
    round(
        (sub.avg_sub_ba_demand_mw / nullif(sub.peak_sub_ba_demand_mw, 0)),
        2
    ) as load_factor,

    -- Parent Grid Context & Share Percentage
    coalesce(parent.total_parent_ba_demand_mwh, 0) as total_parent_ba_demand_mwh,
    round(
        (sub.total_sub_ba_demand_mwh / nullif(parent.total_parent_ba_demand_mwh, 0)) * 100,
        2
    ) as sub_ba_demand_share_pct

from daily_sub_ba_load sub
left join daily_parent_ba_load parent
    on sub.operating_date = parent.operating_date
   and sub.ba_code = parent.ba_code
left join dim_sub_ba sb
    on sub.sub_ba_code = sb.sub_ba_code
left join dim_ba b
    on sub.ba_code = b.ba_code