with stg_source as (
    select * from {{ ref('stg_region_operating_metrics') }}
)
select distinct
    respondent_code
    ,respondent_name
from stg_source
group by all