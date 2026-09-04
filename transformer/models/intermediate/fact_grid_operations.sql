with stg_source as (
    select * from {{ ref('stg_region_operating_metrics') }}
)
select * exclude (respondent_name, type_name, value_units)
from stg_source