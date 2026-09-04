with stg_source as (
    select * from {{ ref('stg_subregional_demand') }}
)
select * exclude (ba_name, sub_ba_name, value_units)
from stg_source