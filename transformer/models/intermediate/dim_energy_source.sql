with stg_source as (
    select * from {{ ref('stg_generation_energy_source') }}
)
select distinct
     fuel_code
    ,fuel_name
from stg_source
group by all