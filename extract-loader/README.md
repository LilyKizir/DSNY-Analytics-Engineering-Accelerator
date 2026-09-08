# EIA Ingestion Script Function Reference (`eia_hourly_ingest.py`)

This Python pipeline orchestrates extraction from the EIA v2 Open API, applies client-side rate limiting and retries, generates payload hashes for change detection, and executes idempotent loads into Snowflake landing tables.

## Database & API Connection Helpers

* **`get_snowflake_connection()`**
  Establishes a session with Snowflake using `snowflake.connector` authenticated via Programmatic Access Token (PAT) and environment variables.

* **`enforce_rate_limit()`**
  Measures time elapsed between outgoing API calls and pauses execution if calls occur faster than `MIN_REQUEST_INTERVAL` (0.45 seconds). Keeps throughput bounded under EIA limits (~2.22 req/sec).

* **`fetch_with_retries(url, params, max_retries=3)`**
  Wraps `requests.get` with exponential backoff retries. Intercepts HTTP throttling (`429`) and server errors (`500`, `502`, `503`, `504`), doubling wait times between retry attempts.

## Core Transformation & Load Functions

* **`build_api_params(target_hour, offset, endpoint_sorts)`**
  Formats the query parameters for EIA API endpoints, setting authentication keys, hourly frequency, date parameters, pagination offset, page size length, and dynamic sort directions.

* **`process_api_response(response)`**
  Parses raw HTTP response objects, extracts record counts, sorts JSON keys deterministically, and generates an MD5 string hash (`payload_hash`).

* **`upsert_to_snowflake(cursor, target_table, record_data)`**
  Executes a SQL `MERGE INTO` query against Snowflake raw tables. Uses `(api_target_hour, page)` as the composite key, updating existing rows only when `payload_hash` differs, or inserting new rows if unmatched.

* **`calculate_target_hours(mode="auto", custom_start=None, custom_end=None)`**
  Generates an array of UTC hourly strings (`YYYY-MM-DDTHH`) to fetch based on execution context:
  * **`daily`**: Pulls the previous 2 operating days.
  * **`weekly`**: Pulls the prior 2 full calendar weeks (runs on Mondays).
  * **`monthly`**: Pulls the prior 2 full calendar months (runs on the 1st of the month).
  * **`auto`**: Evaluates system date to dynamically select `monthly`, `weekly`, or `daily` windows.
  * **`custom`**: Generates hours bounded by user-supplied `--start` and `--end` CLI arguments.

* **`extract_eia_endpoint(endpoint_config, target_hours)`**
  Orchestrates the lifecycle for a given EIA endpoint table: iterates over target hours, handles multi-page pagination offset loops, calls retries/parsing/upserts, and streams real-time CLI terminal progress.
