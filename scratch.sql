CREATE OR REPLACE TABLE TIL_DATA_ENGINEERING.AEA_LK_RAW.RAW_REGIONAL_OPERATING_METRICS (
    run_id VARCHAR,
    loaded_at TIMESTAMP_NTZ,
    status_code NUMBER,
    status_msg VARCHAR,
    api_target_hour VARCHAR,
    page NUMBER,
    record_count NUMBER,
    raw_json_str VARIANT,
    payload_hash VARCHAR,
    updated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE TIL_DATA_ENGINEERING.AEA_LK_RAW.RAW_GENERATION_ENERGY_SOURCE (
    run_id VARCHAR,
    loaded_at TIMESTAMP_NTZ,
    status_code NUMBER,
    status_msg VARCHAR,
    api_target_hour VARCHAR,
    page NUMBER,
    record_count NUMBER,
    raw_json_str VARIANT,
    payload_hash VARCHAR,
    updated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE TIL_DATA_ENGINEERING.AEA_LK_RAW.RAW_SUBREGIONAL_DEMAND (
    run_id VARCHAR,
    loaded_at TIMESTAMP_NTZ,
    status_code NUMBER,
    status_msg VARCHAR,
    api_target_hour VARCHAR,
    page NUMBER,
    record_count NUMBER,
    raw_json_str VARIANT,
    payload_hash VARCHAR,
    updated_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE TIL_DATA_ENGINEERING.AEA_LK_RAW.RAW_BALANCING_AUTHORITY_INTERCHANGE (
    run_id VARCHAR,
    loaded_at TIMESTAMP_NTZ,
    status_code NUMBER,
    status_msg VARCHAR,
    api_target_hour VARCHAR,
    page NUMBER,
    record_count NUMBER,
    raw_json_str VARIANT,
    payload_hash VARCHAR,
    updated_at TIMESTAMP_NTZ
);