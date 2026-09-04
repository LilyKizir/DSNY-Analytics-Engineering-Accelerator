with stg_source as (
    select * from {{ ref('stg_regional_operating_metrics') }}
)
select * exclude (ba_name, type_name, value_units)
from stg_source