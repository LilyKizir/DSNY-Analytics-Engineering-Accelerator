with stg_source as (
    select * from {{ ref('stg_region_operating_metrics') }}
)
select
    type_code
    ,type_name
from stg_source
group by all