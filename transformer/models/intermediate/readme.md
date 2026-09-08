# Intermediate Layer (`models/intermediate/`)

This directory represents the **Silver / Intermediate Layer** of the dbt project. It reshapes cleaned data from the staging layer into a **Kimball Star Schema** consisting of normalized Fact (`fact_*`) and Dimension (`dim_*`) tables.

By decoupling pure structural transformations (star schema modeling) from business logic calculations (reserved for the Gold/Marts layer), this layer guarantees structural data integrity and referential consistency across the pipeline.

---

## Dimension Models (`dim_*`)

Dimension tables isolate descriptive entities, eliminating redundant text across fact tables and serving as conformed lookup tables for downstream reporting.

* **`dim_balancing_authority.sql`**
  Extracts and deduplicates all unique Balancing Authorities (electric grid operators) from regional metrics and interchange data to create a master reference table of grid operators (`ba_code`, `ba_name`).

* **`dim_energy_source.sql`**
  Deduplicates fuel codes to create a master reference list of energy generation sources (`fuel_code`, `fuel_name`), such as Solar, Wind, Coal, Natural Gas, and Nuclear.

* **`dim_sub_balancing_authority.sql`**
  Extracts distinct sub-balancing authority zones (`sub_ba_code`, `sub_ba_name`), representing smaller utility sub-regions within major grid operator territories.

* **`dim_type_codes.sql`**
  Creates a master reference dimension of regional operating metric types (`type_code`, `type_name`), standardizing codes for Demand (`D`), Day-Ahead Demand Forecast (`DF`), Net Generation (`NG`), and Total Interchange (`TI`).

---

## Fact Models (`fact_*`)

Fact tables capture transactional, time-series grid events at an hourly grain. Descriptive text attributes are stripped out, leaving only numeric metrics, timestamps, and foreign keys referencing dimension tables.

* **`fact_balancing_authority_interchange.sql`**
  Records hourly directional physical electricity flows (transfers in MWh) between interconnected grid regions. Contains foreign keys referencing the exporting region (`fromba_code`) and importing region (`toba_code`).

* **`fact_generation_energy_source.sql`**
  Tracks hourly net electricity generation (in MWh) broken down by fuel source (`fuel_code`) for each Balancing Authority (`ba_code`).

* **`fact_regional_operating_metrics.sql`**
  Stores hourly high-level operational readings (demand, generation, total interchange, demand forecasts in MWh) for each Balancing Authority, referenced by metric type (`type_code`).

* **`fact_subregional_demand.sql`**
  Captures hourly electricity demand (in MWh) at the utility sub-zone level (`sub_ba_code`) linked back to its parent Balancing Authority (`ba_code`).

---

## Documentation & Testing Files

* **`_dim.yml`**
  Contains column descriptions and tests primary key constraints (`unique` and `not_null`) for all dimension tables.

* **`_fact.yml`**
  Contains column descriptions, primary key tests (`unique`, `not_null`), and referential integrity tests (`relationships`) enforcing that every foreign key in a fact table correctly resolves to a primary key in its corresponding dimension table.
