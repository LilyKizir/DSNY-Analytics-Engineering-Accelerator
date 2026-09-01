with source as (
        select * from {{ source('eia_daily_raw', 'EIA_DAILY_REGION_DATA_RAW') }}
  ),
  renamed as (
      select
        {{ adapter.quote("UID") }},
        {{ adapter.quote("REQUEST_TIMESTAMP") }},
        {{ adapter.quote("RUN_ID") }},
        {{ adapter.quote("TARGET_START_DATE") }},
        {{ adapter.quote("TARGET_END_DATE") }},
        {{ adapter.quote("OFFSET_VALUE") }},
        {{ adapter.quote("HTTP_STATUS_CODE") }},
        {{ adapter.quote("RECORD_COUNT") }},
        {{ adapter.quote("ERROR_MESSAGE") }},
        {{ adapter.quote("RAW_DATA") }}

      from source
  )
  select * from renamed
    