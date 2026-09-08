<h1>Tranformer</h1>
<a id="readme-top"></a>

This directory contains the dbt project responsible for transforming raw U.S. Energy Information Administration (EIA) grid data into a BI-ready analytics layer. 

The modeling strategy of this project separates structural data transformations from business logic.

## Architecture & Layering Philosophy

### 1. Raw Layer (Context)
Data is ingested from the EIA API and loaded into Snowflake with the entire JSON payload stored as a single `VARIANT` column.  
**Why?** This ELT approach protects our pipeline from failing if the upstream API schema changes or drifts. We capture the exact state of the source data here. We also collect some metadata about the circumstances around the API call itself.

### 2. Staging Layer (`models/staging/`)
The first step in dbt. We use Snowflake's `LATERAL FLATTEN` to unpack the raw JSON `VARIANT` payloads into tabular rows and columns. In this layer, we:
* Extract nested fields.
* Cast and standardize data types (e.g., strings to dates/times/numerics).
* Generate surrogate keys for downstream joins.

### 3. Intermediate Layer (`models/intermediate/`)
Here, we reshape the staging data into a **Star Schema** following Kimball methodology. 
* **Dimensions (`dim_*`)**: Conformed entities (e.g., Balancing Authorities, Fuel Types, Metric Types).
* **Facts (`fact_*`)**: Clean event logs (e.g., hourly generation, sub-regional demand) stripped of descriptive text.

### 4. Marts Layer / Gold (`models/marts/`)
This is the presentation layer where data is modeled for end-users and BI dashboards. 
* **Separation of Concerns:** By isolating business logic in the Marts layer, the core pipeline (Staging/Intermediate) remains purely focused on data structure and integrity.
* **Calculations:** This is where we apply complex business rules, calculate KPIs (e.g., forecast accuracy, renewable penetration), pivot rows to columns, and aggregate time series data to the daily grain.

## Run Project

You can run the project in terminal using the following commands:

```Bash
# Run dbt transformations and tests
cd transformer
dbt deps 
dbt build 
```
