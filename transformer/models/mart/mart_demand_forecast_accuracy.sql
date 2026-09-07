with fact_metrics as (
    select * from {{ ref('fact_regional_operating_metrics') }}
),

dim_ba as (
    select * from {{ ref('dim_balancing_authority') }}
),

-- Pivot demand (D) and forecasted demand (DF) at the hourly grain
pivoted_hourly_demand as (
    select
        f.post_date as operating_date,
        f.post_time as operating_hour,
        f.ba_code,
        b.ba_name,
        
        max(case when f.type_code = 'D'  then f.value_mwh end) as actual_demand_mw,
        max(case when f.type_code = 'DF' then f.value_mwh end) as forecasted_demand_mw,
        max(case when f.type_code = 'NG' then f.value_mwh end) as net_generation_mw,
        max(case when f.type_code = 'TI' then f.value_mwh end) as total_interchange_mw

    from fact_metrics f
    left join dim_ba b
        on f.ba_code = b.ba_code
    group by 1, 2, 3, 4
),

-- Calculate hourly error metrics and operational flags
hourly_metrics as (
    select
        operating_date,
        operating_hour,
        ba_code,
        ba_name,
        
        actual_demand_mw,
        forecasted_demand_mw,
        net_generation_mw,
        total_interchange_mw,

        -- Variance calculations
        (actual_demand_mw - forecasted_demand_mw) as forecast_error_mw,
        abs(actual_demand_mw - forecasted_demand_mw) as abs_forecast_error_mw,

        -- Absolute Percentage Error (APE)
        round(
            (abs(actual_demand_mw - forecasted_demand_mw) / nullif(actual_demand_mw, 0)) * 100, 
            2
        ) as ape_pct,

        -- Forecast Bias Categorization
        case 
            when actual_demand_mw > forecasted_demand_mw then 'UNDER FORECAST'
            when actual_demand_mw < forecasted_demand_mw then 'OVER FORECAST'
            when actual_demand_mw = forecasted_demand_mw then 'EXACT'
            else 'MISSING DATA'
        end as forecast_bias_status

    from pivoted_hourly_demand
    where actual_demand_mw is not null 
       or forecasted_demand_mw is not null
)

select
    operating_date,
    operating_hour,
    ba_code,
    ba_name,
    
    actual_demand_mw,
    forecasted_demand_mw,
    net_generation_mw,
    total_interchange_mw,
    
    forecast_error_mw,
    abs_forecast_error_mw,
    ape_pct,
    forecast_bias_status,

    -- Risk Flag: Highlight severe under-forecasts (> 5% error) during peak stress hours
    case 
        when forecast_bias_status = 'UNDER FORECAST' and ape_pct > 5.0 then 1 
        else 0 
    end as is_high_ramp_risk

from hourly_metrics