with stg_source as (
    select * from {{ ref('stg_balancing_authority_interchange') }}
)
select * exclude (fromba_name, toba_name, value_units)
from stg_source