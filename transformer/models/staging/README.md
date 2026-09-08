# Staging Layer (`models/staging/`)

This directory represents the **Bronze / Staging Layer** of the pipeline. It reads raw JSON payloads stored in Snowflake variant columns, parses nested arrays, standardizes column names, generates deterministic surrogate primary keys, and casts temporal data types.

---

## Common Pipeline Architecture (The 3-CTE Pattern)

Every staging model in this layer strictly adheres to an identical three-stage Common Table Expression (CTE) pattern:

### 1. `source` CTE
* Establishes dbt lineage using the `{{ source('eia_energy', 'raw_*') }}` macro.
* Isolates the raw ingestion table from downstream logic.

### 2. `renamed` CTE
* **JSON Parsing & Unnesting**: Uses `parse_json(RAW_JSON_STR):response:data` passed into Snowflake's `LATERAL FLATTEN` function to explode nested hourly record arrays into individual rows.
* **Surrogate Key Generation**: Utilizes `dbt_utils.generate_surrogate_key()` to hash natural composite keys into a single unique primary key (`MD5`).
* **Field Extraction & Normalization**: Casts raw variant attributes (`d.value:...`) into explicit data types (`numeric`, `string`) and renames hyphens to snake_case (`respondent-name` $\rightarrow$ `ba_name`).

### 3. `typecast` CTE
* **Temporal Splitting**: Converts the ISO timestamp string (`period`, formatted as `YYYY-MM-DDTHH`) into distinct `post_date` (`TO_DATE`) and `post_time` (`TO_TIME`) columns.
* **Column Cleanup**: Uses Snowflake's `* EXCLUDE period` syntax to pass all formatted columns forward while dropping the redundant raw string period.

---

## Model Specifics & Key Differences

While the transformation pipeline is identical, each model handles a distinct grid entity, source table, and natural key combination for surrogate primary key generation:

### 1. `stg_balancing_authority_interchange.sql`
* **Source Table:** `raw_balancing_authority_interchange`
* **Primary Key:** `bai_id`
* **Natural Key Composite:** `['period', 'fromba', 'toba']`
* **Distinct Fields:** Extracts interchange directional attributes (`fromba_code`, `fromba_name`, `toba_code`, `toba_name`) representing physical power transfers across region borders.

### 2. `stg_generation_energy_source.sql`
* **Source Table:** `raw_generation_energy_source`
* **Primary Key:** `ges_id`
* **Natural Key Composite:** `['period', 'respondent', 'fueltype']`
* **Distinct Fields:** Extracts grid operator identifiers (`ba_code`, `ba_name`) and energy fuel details (`fuel_code`, `fuel_name`).

### 3. `stg_regional_operating_metrics.sql`
* **Source Table:** `raw_regional_operating_metrics`
* **Primary Key:** `rom_id`
* **Natural Key Composite:** `['period', 'respondent', 'type']`
* **Distinct Fields:** Extracts grid operator identifiers (`ba_code`, `ba_name`) and metric classification attributes (`type_code`, `type_name`) such as Demand (`D`), Day-Ahead Forecast (`DF`), Net Generation (`NG`), and Total Interchange (`TI`).

### 4. `stg_subregional_demand.sql`
* **Source Table:** `raw_subregional_demand`
* **Primary Key:** `srd_id`
* **Natural Key Composite:** `['period', 'subba', 'parent']`
* **Distinct Fields:** Extracts sub-utility zone details (`sub_ba_code`, `sub_ba_name`) and maps them back to their parent balancing authority (`ba_code`, `ba_name`).
