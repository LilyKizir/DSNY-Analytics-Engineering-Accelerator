import os
import sys
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

def verify_environment():
    print("==========================================")
    print("1. CHECKING ENVIRONMENT & SECRETS INJECTION")
    print("==========================================")
    
    secrets_to_check = {
        "EIA_API_KEY": os.getenv("EIA_API_KEY"),
        "SNOWFLAKE_USERNAME": os.getenv("SNOWFLAKE_USERNAME"),
        "SNOWFLAKE_PAT": os.getenv("SNOWFLAKE_PAT"),
        "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
    }
    
    missing = []
    for var_name, value in secrets_to_check.items():
        if value:
            # Mask value length for security confirmation
            masked = f"{value[:3]}...{value[-3:]}" if len(value) > 6 else "***"
            print(f"  ✅ {var_name}: DETECTED ({masked})")
        else:
            print(f"  ❌ {var_name}: MISSING or EMPTY!")
            missing.append(var_name)
            
    if missing:
        print(f"\n❌ Error: Missing secrets: {', '.join(missing)}")
        sys.exit(1)
    else:
        print("\nAll required secrets are successfully injected into the environment.\n")

def test_snowflake_connection():
    print("==========================================")
    print("2. TESTING SNOWFLAKE CONNECTION")
    print("==========================================")
    
    user = os.getenv("SNOWFLAKE_USERNAME")
    pat = os.getenv("SNOWFLAKE_PAT")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "DATASCHOOL_WH")
    database = os.getenv("SNOWFLAKE_DATABASE", "TIL_DATA_ENGINEERING")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "AEA_LK_RAW")
    
    try:
        conn = snowflake.connector.connect(
            user=user,
            authenticator='programmatic_access_token',
            token=pat,
            account=account,
            warehouse=warehouse,
            database=database,
            schema=schema
        )
        cursor = conn.cursor()
        
        # Query basic metadata to confirm permission and connectivity
        cursor.execute("""
            SELECT 
                CURRENT_VERSION(), 
                CURRENT_USER(), 
                CURRENT_ROLE(), 
                CURRENT_WAREHOUSE(), 
                CURRENT_DATABASE(), 
                CURRENT_SCHEMA()
        """)
        row = cursor.fetchone()
        
        print("  ✅ Snowflake Connection: SUCCESSFUL!")
        print(f"  • Snowflake Version : {row[0]}")
        print(f"  • Authenticated User: {row[1]}")
        print(f"  • Active Role       : {row[2]}")
        print(f"  • Active Warehouse  : {row[3]}")
        print(f"  • Target Database   : {row[4]}")
        print(f"  • Target Schema     : {row[5]}\n")
        
        cursor.close()
        conn.close()
        print("==========================================")
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("==========================================")
        
    except Exception as e:
        print(f"  ❌ Snowflake Connection FAILED!")
        print(f"  Error [{type(e).__name__}]: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    verify_environment()
    test_snowflake_connection()
