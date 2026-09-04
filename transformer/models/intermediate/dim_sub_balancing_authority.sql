with stg_source as (
    select * from {{ ref('stg_subregional_demand') }}
)
select distinct
    sub_ba_code
    ,sub_ba_name
from stg_source
group by all