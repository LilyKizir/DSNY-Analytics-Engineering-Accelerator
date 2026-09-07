with fact_gen as (
    select * from {{ ref('fact_generation_energy_source') }}
),

dim_fuel as (
    select * from {{ ref('dim_energy_source') }}
),

dim_ba as (
    select * from {{ ref('dim_balancing_authority') }}
),

-- Map fuel codes into standardized generation categories
categorized_generation as (
    select
        f.ba_code,
        b.ba_name,
        f.post_date as generation_date,
        f.fuel_code,
        d.fuel_name,
        f.value_mwh as generation_mwh,
        
        -- EIA Fuel Category Groupings
        case 
            when f.fuel_code in ('SUN', 'WND', 'WAT', 'GEO', 'BIO') then 'Renewable'
            when f.fuel_code = 'NUC' then 'Nuclear'
            when f.fuel_code in ('COL', 'NG', 'OIL') then 'Fossil / Thermal'
            else 'Other / Storage'
        end as energy_category,
        
        case 
            when f.fuel_code in ('SUN', 'WND', 'WAT', 'GEO', 'BIO', 'NUC') then 1 
            else 0 
        end as is_carbon_free,

        case 
            when f.fuel_code in ('SUN', 'WND', 'WAT', 'GEO', 'BIO') then 1 
            else 0 
        end as is_renewable

    from fact_gen f
    left join dim_fuel d
        on f.fuel_code = d.fuel_code
    left join dim_ba b
        on f.ba_code = b.ba_code
),

-- Aggregate hourly generation to daily grain and pivot major fuels
daily_pivoted as (
    select
        generation_date,
        ba_code,
        ba_name,
        
        -- Major Fuel Type Aggregations (MWh)
        sum(case when fuel_code = 'COL' then generation_mwh else 0 end) as coal_mwh,
        sum(case when fuel_code = 'NG' then generation_mwh else 0 end) as natural_gas_mwh,
        sum(case when fuel_code = 'NUC' then generation_mwh else 0 end) as nuclear_mwh,
        sum(case when fuel_code = 'OIL' then generation_mwh else 0 end) as petroleum_mwh,
        sum(case when fuel_code = 'SUN' then generation_mwh else 0 end) as solar_mwh,
        sum(case when fuel_code = 'WND' then generation_mwh else 0 end) as wind_mwh,
        sum(case when fuel_code = 'WAT' then generation_mwh else 0 end) as hydro_mwh,
        sum(case when fuel_code not in ('COL', 'NG', 'NUC', 'OIL', 'SUN', 'WND', 'WAT') then generation_mwh else 0 end) as other_mwh,

        -- High-Level Category Aggregations (MWh)
        sum(case when is_renewable = 1 then generation_mwh else 0 end) as renewable_mwh,
        sum(case when is_carbon_free = 1 then generation_mwh else 0 end) as carbon_free_mwh,
        sum(case when energy_category = 'Fossil / Thermal' then generation_mwh else 0 end) as thermal_mwh,
        sum(generation_mwh) as total_generation_mwh

    from categorized_generation
    group by 1, 2, 3
)

-- Final business metrics calculation
select
    generation_date,
    ba_code,
    ba_name,
    
    -- Absolute Volumes
    total_generation_mwh,
    renewable_mwh,
    carbon_free_mwh,
    thermal_mwh,
    
    -- Detailed Fuel Breakdown
    coal_mwh,
    natural_gas_mwh,
    nuclear_mwh,
    petroleum_mwh,
    solar_mwh,
    wind_mwh,
    hydro_mwh,
    other_mwh,

    -- Key KPI Ratios (Safe Division)
    round((renewable_mwh / nullif(total_generation_mwh, 0)) * 100, 2) as renewable_penetration_pct,
    round((carbon_free_mwh / nullif(total_generation_mwh, 0)) * 100, 2) as carbon_free_share_pct,
    round((thermal_mwh / nullif(total_generation_mwh, 0)) * 100, 2) as thermal_share_pct

from daily_pivoted