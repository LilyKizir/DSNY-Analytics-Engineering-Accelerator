from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import snowflake.connector
from datetime import datetime, timezone

# --- API Call Configuration ---
load_dotenv()
EIA_API_KEY = os.getenv('EIA_API_KEY')
LENGTH = 5000
BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
TARGET_HOUR = "2026-01-01T00"
FREQUENCY = "hourly"

# --- Snowflake Configuration ---
SF_USER = os.getenv('SNOWFLAKE_USERNAME')
SF_TOKEN = os.getenv('SNOWFLAKE_PAT')
SF_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SF_WAREHOUSE = "DATASCHOOL_WH"
SF_DATABASE = "TIL_DATA_ENGINEERING"
SF_SCHEMA = "AEA_LK_RAW"
SF_LANDING = "RAW_ELECTRICITY_OPERATIONS"

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

def run_sample_extraction():
    run_id = str(uuid.uuid4())
    print(f"Starting sample extraction run: {run_id}")
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    print(f"Extracting sample data for {TARGET_HOUR}...")
    
    offset = 0
    has_more_data = True
    
    while has_more_data:
        print(f"Fetching offset: {offset}...")
        
        params = {
            "api_key": EIA_API_KEY,
            "frequency": FREQUENCY,
            "data[0]": "value",
            "start": TARGET_HOUR,
            "end": TARGET_HOUR,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "sort[1][column]": "respondent",
            "sort[1][direction]": "desc",
            "sort[2][column]": "type",
            "sort[2][direction]": "desc",
            "offset": offset,
            "length": LENGTH
        }
        
        request_timestamp = datetime.now(timezone.utc)
        response = fetch_with_retries(BASE_URL, params)
        
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
            MERGE INTO {SF_DATABASE}.{SF_SCHEMA}.{SF_LANDING} T
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
                run_id, 
                response_time_str, 
                status_code, 
                status_message, 
                TARGET_HOUR,   
                page_num,      
                record_count, 
                raw_json_str
            ))
            print(f"Successfully loaded Page {page_num} to Snowflake. Records: {record_count}")
        except Exception as e:
            print(f"Snowflake insertion failed at Page {page_num}: {e}")
            break 

    cursor.close()
    conn.close()
    print("Sample extraction complete.")

if __name__ == "__main__":
    run_sample_extraction()