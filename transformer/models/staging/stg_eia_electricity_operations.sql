with source as (
        select * from {{ source('eia', 'electricity_operations') }}
  ),
  renamed as (
    select
        raw_json_str:request.command::string as request_command
      ,d.value:period::string as period
      ,d.value:respondent::string as respondent_code
      ,d.value:"respondent-name"::string as respondent_name
      ,d.value:type::string as type_code
      ,d.value:"type-name"::string as type_name
      ,d.value:value::numeric as value_mwh
      ,d.value:"value-units"::string as value_units

    from source,
      lateral flatten(input => parse_json(RAW_JSON_STR):response:data) d
  ),
  json_parsed as (
    select
      *
    from renamed
      
  )
  select * from json_parsed
    