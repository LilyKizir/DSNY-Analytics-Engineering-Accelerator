select *
from AEA_LK_RAW.EIA_DAILY_REGION_DATA_RAW;

select *
from STG_EIA_DAILY;

DROP SCHEMA IF EXISTS TIL_DATA_ENGINEERING.AEA_LK_AEA_LK_STAGE CASCADE;

DROP VIEW IF EXISTS TIL_DATA_ENGINEERING.AEA_LK_STAGE.STG_EIA_DAILY;

DROP TABLE IF EXISTS TIL_DATA_ENGINEERING.AEA_LK_RAW.MY_FIRST_DBT_MODEL;

-- -- -- -- -- --
use warehouse DATASCHOOL_WH;
use database TIL_DATA_ENGINEERING;
use schema AEA_LK_RAW;

select raw_json_str
from raw_electricity_operations
limit 1;

select
    -- RAW_DATA:request.command::string as request_command
    , d.value:"period"::date as period
    , d.value:"respondent"::string as respondent_code
    , d.value:"respondent-name"::string as respondent_name
    , d.value:"timezone"::string as timezone
    , d.value:"timezone-description"::string as timezone_description
    , d.value:"type"::string as type_code
    , d.value:"type-name"::string as type_name
    , d.value:"value"::numeric as value_mwh
    , d.value:"value-units"::string as value_units
from EIA_DAILY_REGION_DATA_RAW,
lateral flatten(input => parse_json(RAW_DATA):response:data) d;

use database TIL_DATA_ENGINEERING;
use schema AEA_LK_STAGE;

select *
from stg_eia_electricity_operations;

-- ROW TYPES
select distinct
    type_code
    ,type_name
from STG_EIA_DAILY;

-- RESPONDENTS
select distinct
    respondent_code
    ,respondent_name
from stg_eia_daily;

select distinct
    TIMEZONE
    ,TIMEZONE_DESCRIPTION
from stg_eia_daily;


create table IF NOT EXISTS TIL_DATA_ENGINEERING.AEA_LK_RAW.RAW_ELECTRICITY_OPERATIONS (
      RUN_ID VARCHAR
    , UTC_RESPONSE_TIMESTAMP VARCHAR
    , STATUS_CODE int
    , STATUS_MSG VARCHAR
    , UTC_TIMESTAMP VARCHAR
    , PAGE int
    , RECORD_COUNT int
    , RAW_JSON_STR VARIANT
);

select *
from stg_eia_electricity_operations;

with renames as(
    select *
    from stg_eia_electricity_operations
)
select
    to_date(period, 'YYYY-MM-DDTHH') as post_date
    ,to_time(period, 'YYYY-MM-DDTHH') as post_time
    ,* exclude period
from renames;

