with fact_int as (
    select * from {{ ref('fact_balancing_authority_interchange') }}
),

dim_ba as (
    select * from {{ ref('dim_balancing_authority') }}
),

-- Aggregate trade directly off fromba_code
daily_ba_trade as (
    select
        f.post_date as trade_date,
        f.fromba_code as ba_code,
        b.ba_name,
        
        -- Positive value_mwh = Outflow (Export)
        sum(case when f.value_mwh >= 0 then f.value_mwh::numeric(18,2) else 0 end) as total_exports_mwh,
        
        -- Negative value_mwh = Inflow (Import)
        sum(case when f.value_mwh < 0  then abs(f.value_mwh)::numeric(18,2) else 0 end) as total_imports_mwh

    from fact_int f
    left join dim_ba b
        on f.fromba_code = b.ba_code
    group by 1, 2, 3
)

select
    trade_date,
    ba_code,
    ba_name,
    
    total_exports_mwh,
    total_imports_mwh,
    (total_exports_mwh - total_imports_mwh) as net_interchange_mwh,
    (total_exports_mwh + total_imports_mwh) as total_trade_volume_mwh,

    case 
        when (total_exports_mwh - total_imports_mwh) > 0 then 'NET EXPORTER'
        when (total_exports_mwh - total_imports_mwh) < 0 then 'NET IMPORTER'
        else 'BALANCED'
    end as trade_position_status,

    -- Normalized index scaled bounded strictly between -1.00 and +1.00
    round(
        coalesce(
            (total_exports_mwh - total_imports_mwh) / nullif(total_exports_mwh + total_imports_mwh, 0),
            0
        ),
        2
    ) as net_trade_index

from daily_ba_trade