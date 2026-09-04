from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import snowflake.connector
from datetime import datetime, timezone

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

def extract_eia_endpoint(endpoint_config, target_hour):
    """Extracts and loads data for a specific EIA API endpoint."""
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
        print(f"Fetching offset: {offset}...")
        
        # Base parameters
        params = {
            "api_key": EIA_API_KEY,
            "frequency": FREQUENCY,
            "data[0]": "value",
            "start": target_hour,
            "end": target_hour,
            "offset": offset,
            "length": LENGTH
        }
        
        # Dynamically add the sorting parameters specific to this endpoint
        for idx, (col, direction) in enumerate(endpoint_config['sorts']):
            params[f"sort[{idx}][column]"] = col
            params[f"sort[{idx}][direction]"] = direction
            
        request_timestamp = datetime.now(timezone.utc)
        response = fetch_with_retries(url, params)
        
        current_offset = params['offset']
        page_num = (current_offset // LENGTH) + 1
        
        record_count = 0
        raw_json_str = None
        error_msg = None
        status_code = getattr(response, 'status_code', 0)
        
        if status_code == 200:
            data = response.json()
            raw_json_str = json.dumps(data)
            records = data.get("response", {}).get("data", [])
            record_count = len(records)
            
            if record_count < LENGTH:
                has_more_data = False 
            else:
                offset += LENGTH
        else:
            error_msg = response.text if hasattr(response, 'text') else str(response.get("error"))
            raw_json_str = "{}" 
            has_more_data = False 
            print(f"Failed at page {page_num}. Status: {status_code}. Error: {error_msg}")

        response_time_str = request_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        status_message = error_msg if error_msg else "OK"

        upsert_query = f"""
            MERGE INTO {SF_DATABASE}.{SF_SCHEMA}.{target_table} T
            USING (
                SELECT 
                    %s AS run_id,
                    %s AS utc_response_timestamp,
                    %s AS status_code,
                    %s AS status_msg,
                    %s AS utc_timestamp,
                    %s AS page,
                    %s AS record_count,
                    PARSE_JSON(%s) AS raw_json_str
            ) S
            ON T.utc_timestamp = S.utc_timestamp AND T.page = S.page
            WHEN MATCHED THEN
                UPDATE SET 
                    T.run_id = S.run_id,
                    T.utc_response_timestamp = S.utc_response_timestamp,
                    T.status_code = S.status_code,
                    T.status_msg = S.status_msg,
                    T.record_count = S.record_count,
                    T.raw_json_str = S.raw_json_str
            WHEN NOT MATCHED THEN
                INSERT (run_id, utc_response_timestamp, status_code, status_msg, 
                        utc_timestamp, page, record_count, raw_json_str)
                VALUES (S.run_id, S.utc_response_timestamp, S.status_code, S.status_msg, 
                        S.utc_timestamp, S.page, S.record_count, S.raw_json_str);
        """
        
        try:
            cursor.execute(upsert_query, (
                  run_id
                , response_time_str
                , status_code
                , status_message
                , target_hour
                , page_num
                , record_count
                , raw_json_str
            ))
            print(f"Successfully loaded Page {page_num} to {target_table}. Records: {record_count}")
        except Exception as e:
            print(f"Snowflake insertion failed at Page {page_num}: {e}")
            break 

    cursor.close()
    conn.close()

if __name__ == "__main__":
    
    TARGET_HOUR_OVERRIDE = "2026-01-01T00"
    
    # Configuration list defining the unique traits of each endpoint
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

    # Execute extraction for all 4 endpoints
    for endpoint in ENDPOINTS:
        extract_eia_endpoint(endpoint, TARGET_HOUR_OVERRIDE)
        
    print("\nAll extractions completed successfully.")