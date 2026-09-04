with stg_source as (
    select * from {{ ref('stg_generation_energy_source') }}
)
select * exclude (ba_name, fuel_name, value_units)
from stg_source