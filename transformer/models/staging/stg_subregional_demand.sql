with source as (
        select * from {{ source('eia_energy', 'raw_subregional_demand') }}
  ),
  renamed as (
    select
        -- raw_json_str:request.command::string as request_command
      d.value:period::string as period
      ,d.value:subba::string as sub_ba_code
      ,d.value:"subba-name"::string as sub_ba_name
      ,d.value:parent::string as ba_code
      ,d.value:"parent-name"::string as ba_name
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
    