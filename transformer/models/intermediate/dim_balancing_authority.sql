with 
stg_region_source as (
    select distinct
         ba_code
        ,ba_name
    from {{ ref('stg_regional_operating_metrics') }}
),
stg_subreg_source as (
    select distinct
         ba_code
        ,ba_name
    from {{ ref('stg_subregional_demand') }}
),
stg_gen_source as (
    select distinct
         ba_code
        ,ba_name 
    from {{ ref('stg_generation_energy_source') }}
),
stg_int_source1 as (
    select distinct
         toba_code as ba_code
        ,toba_name as ba_name
    from {{ ref('stg_balancing_authority_interchange') }}
),
stg_int_source2 as (
    select distinct
         fromba_code as ba_code
        ,fromba_name as ba_name
    from {{ ref('stg_balancing_authority_interchange') }}
),
unioned as (
    select * from stg_region_source
    union
    select * from stg_subreg_source
    union
    select * from stg_gen_source
    union
    select * from stg_int_source1
    union
    select * from stg_int_source2
)
select distinct *
from unioned
group by all