from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import sys
import snowflake.connector
from datetime import datetime, timezone
import hashlib

# --- Core Configuration ---
load_dotenv()
EIA_API_KEY = os.getenv('EIA_API_KEY')
LENGTH = 5000
FREQUENCY = "hourly"

# --- Rate Limiting Configuration ---
MIN_REQUEST_INTERVAL = 0.45  
LAST_REQUEST_TIMESTAMP = 0.0

# --- Snowflake Configuration ---
SF_USER = os.getenv('SNOWFLAKE_USERNAME')
SF_TOKEN = os.getenv('SNOWFLAKE_PAT')
SF_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SF_WAREHOUSE = "DATASCHOOL_WH"
SF_DATABASE = "TIL_DATA_ENGINEERING"
SF_SCHEMA = "AEA_LK_RAW"

def verify_env_secrets():
    """Sanity check to confirm required secrets are available before running."""
    print("--- 1. VERIFYING ENVIRONMENT SECRETS ---")
    required_vars = {
        "EIA_API_KEY": EIA_API_KEY,
        "SNOWFLAKE_USERNAME": SF_USER,
        "SNOWFLAKE_PAT": SF_TOKEN,
        "SNOWFLAKE_ACCOUNT": SF_ACCOUNT
    }
    missing = [var for var, val in required_vars.items() if not val]
    if missing:
        print(f"❌ CRITICAL ERROR: Missing required secrets: {', '.join(missing)}")
        sys.exit(1)
    
    for var in required_vars:
        print(f"  ✅ {var}: DETECTED")
    print("All required secrets successfully loaded into runner environment.\n")

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SF_USER,
        authenticator='programmatic_access_token',
        token=SF_TOKEN,
        account=SF_ACCOUNT,
        warehouse=SF_WAREHOUSE,
        database=SF_DATABASE,
        schema=SF_SCHEMA
    )

def enforce_rate_limit():
    global LAST_REQUEST_TIMESTAMP
    elapsed = time.time() - LAST_REQUEST_TIMESTAMP
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    LAST_REQUEST_TIMESTAMP = time.time()

def fetch_with_retries(url, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            enforce_rate_limit()
            response = requests.get(url, params=params, timeout=30)
            if response.status_code in [429, 500, 502, 503, 504]:
                wait_time = (2 ** attempt) + 1
                print(f"\nStatus {response.status_code}. Throttling and retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return {"error": str(e), "status_code": 0}
            time.sleep(2 ** attempt)

def build_api_params(target_hour, offset, endpoint_sorts):
    params = {
        "api_key": EIA_API_KEY,
        "frequency": FREQUENCY,
        "data[0]": "value",
        "start": target_hour,
        "end": target_hour,
        "offset": offset,
        "length": LENGTH
    }
    for idx, (col, direction) in enumerate(endpoint_sorts):
        params[f"sort[{idx}][column]"] = col
        params[f"sort[{idx}][direction]"] = direction
    return params

def process_api_response(response):
    status_code = getattr(response, 'status_code', 0)
    
    if status_code == 200:
        data = response.json()
        raw_json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        records = data.get("response", {}).get("data", [])
        record_count = len(records)
        error_msg = None
    else:
        error_msg = response.text if hasattr(response, 'text') else str(response.get("error"))
        raw_json_str = "{}"
        record_count = 0

    payload_hash = hashlib.md5(raw_json_str.encode('utf-8')).hexdigest()
    
    return {
        "status_code": status_code,
        "status_msg": error_msg if error_msg else "OK",
        "record_count": record_count,
        "raw_json_str": raw_json_str,
        "payload_hash": payload_hash
    }

def upsert_to_snowflake(cursor, target_table, record_data):
    upsert_query = f"""
        MERGE INTO {SF_DATABASE}.{SF_SCHEMA}.{target_table} T
        USING (
            SELECT 
                %s::VARCHAR AS run_id,
                %s::TIMESTAMP_NTZ AS loaded_at,
                %s::NUMBER AS status_code,
                %s::VARCHAR AS status_msg,
                %s::VARCHAR AS api_target_hour, 
                %s::NUMBER AS page,
                %s::NUMBER AS record_count,
                PARSE_JSON(%s) AS raw_json_str,
                %s::VARCHAR AS payload_hash
        ) S
        ON T.api_target_hour = S.api_target_hour AND T.page = S.page
        
        WHEN MATCHED AND (T.payload_hash IS NULL OR T.payload_hash != S.payload_hash) THEN
            UPDATE SET 
                T.run_id = S.run_id,
                T.status_code = S.status_code,
                T.status_msg = S.status_msg,
                T.record_count = S.record_count,
                T.raw_json_str = S.raw_json_str,
                T.payload_hash = S.payload_hash,
                T.updated_at = S.loaded_at
                
        WHEN NOT MATCHED THEN
            INSERT (run_id, loaded_at, status_code, status_msg, 
                    api_target_hour, page, record_count, raw_json_str, payload_hash, updated_at)
            VALUES (S.run_id, S.loaded_at, S.status_code, S.status_msg, 
                    S.api_target_hour, S.page, S.record_count, S.raw_json_str, S.payload_hash, S.loaded_at);
    """
    
    cursor.execute(upsert_query, (
        record_data["run_id"],
        record_data["loaded_at"],
        record_data["status_code"],
        record_data["status_msg"],
        record_data["api_target_hour"],
        record_data["page"],
        record_data["record_count"],
        record_data["raw_json_str"],
        record_data["payload_hash"]
    ))

def extract_eia_endpoint(endpoint_config, target_hours):
    run_id = str(uuid.uuid4())
    url = endpoint_config['url']
    target_table = endpoint_config['table']
    total_hours = len(target_hours)
    
    print(f"\n--- Processing Table: {target_table} ---")
    print(f"Run ID: {run_id} | Target Hour: {target_hours[0]}")
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    for idx, hour in enumerate(target_hours, start=1):
        offset = 0
        has_more_data = True
        
        while has_more_data:
            page_num = (offset // LENGTH) + 1
            
            params = build_api_params(hour, offset, endpoint_config['sorts'])
            request_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            response = fetch_with_retries(url, params)
            parsed = process_api_response(response)
            
            if parsed["status_code"] != 200:
                print(f"❌ Failed Page {page_num}. Status: {parsed['status_code']}. Error: {parsed['status_msg']}")
                has_more_data = False
            elif parsed["record_count"] < LENGTH:
                has_more_data = False
            else:
                offset += LENGTH

            record_data = {
                "run_id": run_id,
                "loaded_at": request_timestamp,
                "api_target_hour": hour,
                "page": page_num,
                **parsed
            }

            try:
                upsert_to_snowflake(cursor, target_table, record_data)
                print(f"  ✅ MERGE Successful for {target_table} | Hour: {hour} | Page: {page_num} | Records: {parsed['record_count']}")
            except Exception as e:
                print(f"\n❌ CRITICAL: Snowflake MERGE Failed for {target_table}!")
                print(f"Error: {e}\n")
                cursor.close()
                conn.close()
                sys.exit(1)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify_env_secrets()
    
    # HARDCODED TEST HOUR
    target_hours = ["2026-02-02T00"]
    print(f"--- 2. EXECUTING TEST FOR TARGET HOUR: {target_hours[0]} ---")

    ENDPOINTS = [
        {
            "url": "https://api.eia.gov/v2/electricity/rto/region-data/data/",
            "table": "RAW_REGIONAL_OPERATING_METRICS",
            "sorts": [("period", "asc"), ("respondent", "desc"), ("type", "desc")]
        },
        {
            "url": "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/",
            "table": "RAW_GENERATION_ENERGY_SOURCE",
            "sorts": [("period", "asc"), ("respondent", "desc"), ("fueltype", "desc")]
        },
        {
            "url": "https://api.eia.gov/v2/electricity/rto/region-sub-ba-data/data/",
            "table": "RAW_SUBREGIONAL_DEMAND",
            "sorts": [("period", "asc"), ("subba", "desc")]
        },
        {
            "url": "https://api.eia.gov/v2/electricity/rto/interchange-data/data/",
            "table": "RAW_BALANCING_AUTHORITY_INTERCHANGE",
            "sorts": [("period", "asc"), ("fromba", "desc"), ("toba", "desc")]
        }
    ]

    for endpoint in ENDPOINTS:
        extract_eia_endpoint(endpoint, target_hours)
        
    print("\n🎉 ALL 4 TABLES INGESTED AND MERGED SUCCESSFULLY TO RAW SCHEMA.")