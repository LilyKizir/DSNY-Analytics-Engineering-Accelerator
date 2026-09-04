from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import snowflake.connector
from datetime import datetime, timezone, timedelta

# --- API Call Configuration ---
load_dotenv()
EIA_API_KEY = os.getenv('API_KEY')
LENGTH = 5000
BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
START_DATE = END_DATE = "2026-01-01T00"
FREQUENCY = "hourly"

# --- Snowflake Configuration ---
SF_USER = os.getenv('SNOWFLAKE_USERNAME')
SF_TOKEN = os.getenv('SNOWFLAKE_PAT')
SF_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SF_WAREHOUSE = "DATASCHOOL_WH"
SF_DATABASE = "TIL_DATA_ENGINEERING"
SF_SCHEMA = "AEA_LK_RAW"
SF_TABLE = "eia_hourly_operations"

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SF_USER,
        authenticator = 'programmatic_access_token',
        token=SF_TOKEN,
        account=SF_ACCOUNT,
        warehouse=SF_WAREHOUSE,
        database=SF_DATABASE,
        schema=SF_SCHEMA
    )

def get_latest_api_date():
    """Probes the EIA API to find the most recent date of data available."""
    print("Probing API for the latest available date...")
    
    probe_params = {
        "api_key": EIA_API_KEY,
        "frequency": FREQUENCY,
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 1  # We only need 1 record!
    }
    
    response = fetch_with_retries(BASE_URL, probe_params)
    
    if getattr(response, 'status_code', 0) == 200:
        data = response.json()
        records = data.get("response", {}).get("data", [])
        if records:
            latest_date_str = records[0].get("period") # This is a string!
            latest_date_obj = datetime.strptime(latest_date_str, '%Y-%m-%dT%H')
            print(f"API's latest full available data is from: {latest_date_obj}")
            return latest_date_str
            
    print("Warning: Probe failed. Falling back to yesterday's date.")
    return (datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H')

def __get_date_range(cursor):
    # 1. Ask the API what it currently has FIRST
    end_date_str = get_latest_api_date() 

    # --- NEW DEBUG BLOCK ---
    print("\n--- SNOWFLAKE SESSION CONTEXT ---")
    cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
    session_info = cursor.fetchone()
    print(f"User:      {session_info[0]}")
    print(f"Role:      {session_info[1]}")
    print(f"Database:  {session_info[2]}")
    print(f"Schema:    {session_info[3]}")
    print(f"Warehouse: {session_info[4]}")
    print("---------------------------------\n")
    # -----------------------

    # 2. Ask Snowflake what we already have
    query = """
        SELECT MAX(target_end_date) 
        FROM eia_daily_region_data_raw 
        WHERE http_status_code = 200 
            AND record_count > 0
    """
    cursor.execute(query)
    last_fetched_date = cursor.fetchone()[0] # Snowflake returns a datetime.date object here!

    if last_fetched_date:
        # We have data! No need to parse it. Just add 1 day and format to string.
        start_date = (last_fetched_date + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        # First run ever - convert API string to object, subtract 31 days safely!
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d')
        start_date = (end_date_obj - timedelta(days=31)).strftime('%Y-%m-%d')
    
    return start_date, end_date_str

def fetch_with_retries(url, params, max_retries=3):
    """Fetches data from the API with exponential backoff for transient errors."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            # If rate limited or server error, wait and retry
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

def run_extraction():
    run_id = str(uuid.uuid4())
    print(f"Starting extraction run: {run_id}")
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    # Get dynamic dates
    # START_DATE, END_DATE = get_date_range(cursor)

    # Check if we even need to run
    # if START_DATE > END_DATE:
    #     print(f"Data is up to date (Latest full day of API data: {END_DATE}). Exiting.")
    #     cursor.close()
    #     conn.close()
    #     return

    print(f"Extracting data from {START_DATE} to {END_DATE}...")
    
    offset = 0
    has_more_data = True
    
    while has_more_data:
        print(f"Fetching offset: {offset}...")
        
        params = {
            "api_key": EIA_API_KEY,
            "frequency": FREQUENCY,
            "data[0]": "value",
            "start": START_DATE,
            "end": END_DATE,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "sort[1][column]": "respondent",
            "sort[1][direction]": "desc",
            "sort[2][column]": "type",
            "sort[2][direction]": "desc",
            "offset": offset,
            "length": LENGTH
        }
        
        request_timestamp = datetime.now(timezone.utc)
        response = fetch_with_retries(BASE_URL, params)
        
        # Initialize default values
        record_count = 0
        raw_json_str = None
        error_msg = None
        status_code = getattr(response, 'status_code', 0)
        
        if status_code == 200:
            data = response.json()
            raw_json_str = json.dumps(data)
            
            # EIA v2 API puts the actual array of records in response['response']['data']
            records = data.get("response", {}).get("data", [])
            record_count = len(records)
            
            if record_count < LENGTH:
                has_more_data = False # Reached the end of the dataset
            else:
                offset += LENGTH
        else:
            # Handle failure (store the error and stop the loop)
            error_msg = response.text if hasattr(response, 'text') else str(response.get("error"))
            raw_json_str = "{}" # Insert empty JSON for failures
            has_more_data = False # Stop loop to prevent infinite error cycling
            print(f"Failed at offset {offset}. Status: {status_code}. Error: {error_msg}")

        # Insert metadata and raw JSON into Snowflake
        insert_query = """
            INSERT INTO eia_daily_region_data_raw
            (request_timestamp, run_id, target_start_date, target_end_date, offset_value, 
             http_status_code, record_count, error_message, raw_data)
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)
        """
        
        try:
            cursor.execute(insert_query, (
                request_timestamp, 
                run_id, 
                START_DATE, 
                END_DATE, 
                offset if status_code == 200 else params['offset'], 
                status_code, 
                record_count, 
                error_msg, 
                raw_json_str
            ))
            print(f"Successfully loaded offset {params['offset']} to Snowflake. Records: {record_count}")
        except Exception as e:
            print(f"Snowflake insertion failed at offset {params['offset']}: {e}")
            break # Halt execution if DB fails

    cursor.close()
    conn.close()
    print("Extraction complete.")

if __name__ == "__main__":
    run_extraction()