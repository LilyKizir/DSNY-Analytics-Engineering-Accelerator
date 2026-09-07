with source as (
        select * from {{ source('eia_energy', 'raw_generation_energy_source') }}
  ),
  renamed as (
    select
      {{ dbt_utils.generate_surrogate_key([
            'd.value:period::string', 
            'd.value:respondent::string', 
            'd.value:fueltype::string'
        ]) }} as ges_id
        -- raw_json_str:request.command::string as request_command
      ,d.value:period::string as period
      ,d.value:respondent::string as ba_code
      ,d.value:"respondent-name"::string as ba_name
      ,d.value:fueltype::string as fuel_code
      ,d.value:"type-name"::string as fuel_name
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
    