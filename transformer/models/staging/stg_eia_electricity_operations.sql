with source as (
        select * from {{ source('eia', 'electricity_operations') }}
  ),
  renamed as (
    select
        -- raw_json_str:request.command::string as request_command
      d.value:period::string as period
      ,d.value:respondent::string as respondent_code
      ,d.value:"respondent-name"::string as respondent_name
      ,d.value:type::string as type_code
      ,d.value:"type-name"::string as type_name
      ,d.value:value::numeric as value_mwh
      ,d.value:"value-units"::string as value_units

    from source,
      lateral flatten(input => parse_json(RAW_JSON_STR):response:data) d
  ),
  typecast as (
    select
      to_date(period, 'YYYY-MM-DDTHH') as post_date
      ,to_time(period, 'YYYY-MM-DDTHH') as post_time
      ,* exclude period
    from renamed
      
  )
  select * from typecast
    