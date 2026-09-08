<h1>DSNY Analytics Engineering Accelerator</h1>
<a id="readme-top"></a>

Produced by Lily Kiziriya

The Analytics Engineering Project is an end-to-end, automated data pipeline that:  
- ingests U.S. Energy Information Administration (EIA) hourly electricity grid data into Snowflake
- transforms the raw data into a clean, flattened bronze layer using dbt
- models it into a silver layer dimensional star schema using dbt
- produces BI ready tables that incorporate some basic business metrics in the gold layer
- automates continuous execution via GitHub Actions + Cron-Job.org.

<h2>Architecture & Pipeline Overview</h2>  

```Plaintext
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│  This project covers:                                                                      │
│                                                                                            │
│  ┌──────────────────┐      ┌─────────────────────────┐      ┌───────────────────────────┐  │      ┌─────────────────┐
│  │  EIA Open API    │ ───> │ Python Ingestion Script │ ───> │ dbt Transformation        │  │ ───> │  BI Dashboard / │
│  │  (Hourly Data)   │      │ Snowflake (Raw Storage) │      │ [Staging -> Int -> Marts] │  │      │    Analytics    │
│  └──────────────────┘      └─────────────────────────┘      └───────────────────────────┘  │      └─────────────────┘
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

The pipeline operates in three distinct phases:  

<b>Extraction & Raw Load:</b>  
A Python script extracts hourly grid metrics across 4 EIA API endpoints.

<b>Transformation & Modeling:</b>  
dbt models the raw JSON payloads into a dimensional star schema using the medallion architecture for separation.

Bronze --> Staging
Silver --> Intermediate
Gold   --> Mart

<b>Orchestration & CI/CD:</b>  
Manual workflow triggers run inside GitHub Actions, with scheduled automation triggered via Cron-Job.org.

<h2>Directory Map</h2>

```Plaintext
DSNY-Analytics-Engineering-Accelerator/
├── .github/
│   └── workflows/
│       └── daily_snowflake_ingestion.yml  # GitHub Actions pipeline workflow
│
├── extract-loader/                        # Python EL Pipeline
│   ├── README.md                          # API & ingestion script docs
│   └── eia_hourly_ingest.py               # Main modular production script
│
├── transformer/                           # dbt Transformation Project
│   ├── README.md                          # dbt project & model docs
│   ├── dbt_project.yml                    # dbt project configurations
│   ├── profiles.yml                       # Snowflake connection profile (env_var mapped)
│   └── models/
│       ├── staging/                       # Raw JSON extraction & initial cleaning
│       ├── intermediate/                  # Fact & dimension entities (Star Schema, Kimball methodology)
│       └── marts/                         # Dashboard-ready gold tables
│
├── .env.example                           # Template for local environment variables
├── requirements.txt                       # Python dependencies
└── README.md                              # Repository overview (You are here)
```

<h2>Data Lineage & Modeling Strategy</h2>

The target database is **`TIL_DATA_ENGINEERING`**, segmented logically across four core schema layers:

| Layer | Snowflake Schema | Grain / Description | dbt Materialization |
| :--- | :--- | :--- | :--- |
| **Raw** | `AEA_LK_RAW` | 1 row per API response page per target hour (`api_target_hour` + `page`) | Table (Python Load) |
| **Staging** | `AEA_LK_STAGE` | 1 row per record parsed from raw JSON payloads (`stg_*`) | View |
| **Intermediate** | `AEA_LK_INTERMEDIATE` | Conformed Fact and Dimension entities (`dim_*`, `fact_*`) | View |
| **Marts** | `AEA_LK_MART` | Aggregated, dashboard-ready analytical summaries (`mart_*`) | Table |

**Data Grain Justification**
* **Raw Layer (`AEA_LK_RAW`):** Captures complete API payload responses (`VARIANT`) to preserve source auditability without losing raw metadata.
* **Dimensions (`dim_*`):** Isolates distinct entities for Balancing Authorities (`dim_balancing_authority`), sub-regions(`dim_sub_balancing_authority`), energy source types (`dim_energy_source`), and metric types (`dim_type_code`).
* **Facts (`fact_*`):** Standardizes time series data to **1 row per operating hour per entity** (e.g., fuel type, region, interchange pair).
* **Marts (`mart_*`):** Roll up hourly generation, regional metrics, and interchange flows into daily and zonal summaries for BI reporting performance.

<h2>Engineering Judgments & Design Decisions</h2>

- Idempotency & Re-run Safety: Raw loads use a Snowflake MERGE statement comparing an MD5 payload_hash generated from the API json output. Re-running the pipeline for existing time windows updates modified records or skips duplicate payloads without creating duplicate rows.

- Rate Limit Management: EIA caps API requests at 5 req/sec and 9,000 req/hr. The ingestion script enforces a minimum 0.45-second sleep interval between calls and handles HTTP 429/50x codes with exponential backoff retries.

- Secret Handling: Credentials are never committed. Secrets are injected via environment variables at runtime using python-dotenv locally and GitHub Secrets in CI/CD.

<h2>Setup & Local Execution Guide</h2>

This project is optimized for quick deployment using repository cloning, GitHub Actions, and GitHub Codespaces.

<h3>1. Fork the repository</h3>

<h3>2. Configure GitHub Secrets</h3>

Navigate to Settings > Secrets and variables > Actions in your GitHub repository and add the following repository secrets:

- EIA_API_KEY

- SNOWFLAKE_USERNAME

- SNOWFLAKE_PAT

- SNOWFLAKE_PRIVATE_KEY (You will have to generate this rsa key pair. Private key for github, public key for snowflake)

- SNOWFLAKE_ACCOUNT


<h3>3. Launch in GitHub Codespaces</h3>

- Click Code > Codespaces > Create codespace on main.

- The container automatically configures Python 3.12, dbt, and project dependencies defined in .devcontainer/devcontainer.json.

- You can run the project in terminal using the following commands

```Bash
# Run raw EIA data extraction and Snowflake load
python extract-loader/eia_hourly_ingest.py --mode auto

# Run dbt transformations and tests
cd transformer
dbt deps 
dbt build 
```

<h3>4. Trigger the GitHub Actions Workflow</h3>  

- Go to the Actions tab in your GitHub repository.

- Select Daily Snowflake Ingestion.

- Click Run workflow to execute the Python ingestion script and dbt build sequence end-to-end.

FUTURE IMPLEMENTATION - Local Project Execution


<hr>

<h2>Contact</h2>

Lily Kiziriya  
Email: lily.kiziriya@theinformationlab.com  
[GitHub]() | [LinkedIn]() | [Twitter]() | [Alteryx Community]()  
