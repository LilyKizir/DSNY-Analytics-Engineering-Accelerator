from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import snowflake.connector
from datetime import datetime, timezone
import hashlib

# --- Core Configuration ---
load_dotenv()
EIA_API_KEY = os.getenv('EIA_API_KEY')
LENGTH = 5000
FREQUENCY = "hourly"

# --- Snowflake Configuration ---
SF_USER = os.getenv('SNOWFLAKE_USERNAME')
SF_TOKEN = os.getenv('SNOWFLAKE_PAT')
SF_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SF_WAREHOUSE = "DATASCHOOL_WH"
SF_DATABASE = "TIL_DATA_ENGINEERING"
SF_SCHEMA = "AEA_LK_RAW"

# --- Database & API Helpers ---

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

def fetch_with_retries(url, params, max_retries=3):
    """Fetches data from the API with exponential backoff for transient errors."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code in [429, 500, 502, 503, 504]:
                wait_time = 2 ** attempt
                print(f"Status {response.status_code}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return response
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return {"error": str(e), "status_code": 0}
            time.sleep(2 ** attempt)

# --- Modular Pipeline Functions ---

def build_api_params(target_hour, offset, endpoint_sorts):
    """Constructs sorted EIA API request parameters."""
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
    """Parses JSON response, extracts metadata, and generates deterministic hash."""
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
    """Executes the MERGE upsert into Snowflake raw table."""
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

# --- Main Orchestration ---

def extract_eia_endpoint(endpoint_config, target_hour):
    """Orchestrates pagination, API fetching, and loading for a single endpoint."""
    run_id = str(uuid.uuid4())
    url = endpoint_config['url']
    target_table = endpoint_config['table']
    
    print(f"\n--- Starting extraction for: {target_table} ---")
    print(f"Run ID: {run_id} | Target Hour: {target_hour}")
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    offset = 0
    has_more_data = True
    
    while has_more_data:
        page_num = (offset // LENGTH) + 1
        print(f"Fetching Page {page_num} (Offset: {offset})...")
        
        # 1. Prepare Request
        params = build_api_params(target_hour, offset, endpoint_config['sorts'])
        request_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        # 2. Fetch API Data
        response = fetch_with_retries(url, params)
        
        # 3. Process Payload & Metadata
        parsed = process_api_response(response)
        
        if parsed["status_code"] != 200:
            print(f"Failed at Page {page_num}. Status: {parsed['status_code']}. Error: {parsed['status_msg']}")
            has_more_data = False
        elif parsed["record_count"] < LENGTH:
            has_more_data = False
        else:
            offset += LENGTH

        # 4. Consolidate Record Context for Database
        record_data = {
            "run_id": run_id,
            "loaded_at": request_timestamp,
            "api_target_hour": target_hour,
            "page": page_num,
            **parsed
        }

        # 5. Execute Database Upsert
        try:
            upsert_to_snowflake(cursor, target_table, record_data)
            print(f"Successfully loaded Page {page_num} to {target_table}. Records: {parsed['record_count']}")
        except Exception as e:
            # 1. Capture comprehensive operational context
            error_context = {
                "target_table": target_table,
                "run_id": record_data.get("run_id"),
                "page": page_num,
                "api_target_hour": record_data.get("api_target_hour"),
                "record_count": record_data.get("record_count"),
                "payload_hash": record_data.get("payload_hash"),
                "error_type": type(e).__name__,
                "error_details": str(e)
            }
            
            # 2. Print structured output (or send to Python logging)
            print(f"\n❌ CRITICAL: Snowflake MERGE Failed!")
            print(f"Table: {target_table} | Run ID: {error_context['run_id']}")
            print(f"Context: Page {page_num} | Target Hour: {error_context['api_target_hour']} | Records: {error_context['record_count']}")
            print(f"Error [{error_context['error_type']}]: {error_context['error_details']}\n")
            
            # 3. Raise or break depending on workflow strategy
            raise

    cursor.close()
    conn.close()

if __name__ == "__main__":
    
    TARGET_HOUR_OVERRIDE = "2026-01-01T00"
    
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
        extract_eia_endpoint(endpoint, TARGET_HOUR_OVERRIDE)
        
    print("\nAll extractions completed successfully.")