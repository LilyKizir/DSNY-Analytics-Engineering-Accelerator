with source as (
        select * from {{ source('eia_energy', 'raw_balancing_authority_interchange') }}
  ),
  renamed as (
    select
        -- raw_json_str:request.command::string as request_command
      d.value:period::string as period
      ,d.value:fromba::string as fromba_code
      ,d.value:"fromba-name"::string as fromba_name
      ,d.value:toba::string as toba_code
      ,d.value:"toba-name"::string as toba_name
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
    