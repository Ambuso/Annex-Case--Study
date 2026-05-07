# ABC Phones Credit Portfolio — Annex DE Case Study

A lightweight but production-shaped data pipeline for ABC Phones' credit
portfolio: ingestion → cleaning → feature engineering → quality checks →
analysis. Built with Python + Pandas + DuckDB + Parquet — a lakehouse
pattern that runs on a laptop today and lifts cleanly into S3+Athena,
GCS+BigQuery, or Snowflake tomorrow with no SQL rewrites.

---

## TL;DR

### Create and activate a virtual environment

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Windows (Git Bash)
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Deactivate the environment when finished:

deactivate
Run the pipeline
pip install -r requirements.txt
python run_pipeline.py

End-to-end runtime ≈ 2.5 minutes. All outputs land in outputs/,
all intermediate Parquet tables in data/warehouse/, all logs in
logs/pipeline.log.

Pipeline Architecture

Directory layout
.
├── run_pipeline.py              # single-driver orchestrator
├── pipeline_design/
│   ├── architecture.png
│   └── architecture.svg
├── scripts/
│   ├── data_profiling.py
│   ├── data_cleaning.py
│   ├── feature_engineering.py
│   ├── quality_checks.py
│   ├── analysis.py
│   └── generate_architecture_diagram.py
├── data/
│   ├── raw/                     # source files (gitignored)
│   └── warehouse/               # Parquet tables, Hive-partitioned
│       ├── stg_credit_snapshot/snapshot_date=YYYY-MM-DD/data.parquet
│       ├── stg_customer.parquet
│       ├── stg_nps.parquet
│       ├── dim_customer.parquet
│       └── fct_credit_snapshot/snapshot_date=YYYY-MM-DD/data.parquet
├── outputs/
│   ├── data_quality_report.md
│   ├── profile_*.csv
│   ├── dq_results.csv
│   ├── portfolio_metrics.csv
│   ├── portfolio_by_segment.csv
│   ├── nps_by_risk.csv
│   ├── cleaned_summary.csv
│   └── analysis_findings.md
├── slides/
│   └── Annex_DE_Presentation.pdf
└── logs/
    └── pipeline.log
Tech choices
Concern	Choice	Why
Storage	Parquet, Hive-partitioned by snapshot_date	Columnar, compressed, cloud-ready
Compute	Pandas + DuckDB	Fast local analytics + SQL on Parquet
Orchestration	Python script driver	Easy to migrate to Airflow/Prefect
Quality	Custom Python DQ checks	Replaceable with Great Expectations/dbt
Alerting	Logging hooks	Plug into Slack/PagerDuty in prod
Key decisions & assumptions
No customer_id exists → analysis is loan-level
Column inconsistencies cleaned at ingest
DOB conflicts resolved via bureau priority: TRANSUNION > SMILEID > SPINMOBILE
Income fields carefully handled to avoid double counting
days_past_due independently recalculated for validation
Risk categories mapped from ACCOUNT_STATUS_L2
Demo rows excluded
Missing demographics retained as Unknown
Quarterly snapshot structure enforced
One dataset contains date mismatch → flagged in DQ checks
Reproducing this submission
Install dependencies
pip install -r requirements.txt
Required data files
data/raw/
Credit_Data_-_01-01-2025.csv
Credit_Data_-_30-03-2025.csv
Credit_Data_-_30-06-2025.csv
Credit_Data_-_30-09-2025.csv
Credit_Data_-_30-12-2025.csv
Credit_Data_Definitions.xlsx
Sales_and_Customer_Data.xlsx
NPS_Data.xlsx
Run pipeline
python run_pipeline.py

All stages are modular and idempotent.

Production roadmap
Airflow DAG orchestration (task-per-stage)
S3 + Athena / BigQuery migration (no logic change)
dbt transformation layer for lineage + testing
Great Expectations / Soda for data quality framework
Slack + PagerDuty alerting integration
OpenLineage for observability tracking
Summary

This project demonstrates a production-style data engineering pipeline
built with lightweight tools, designed to scale from local execution to
cloud warehouse systems without rewriting core logic.

It emphasizes:

Data quality discipline
Reproducible pipelines
Warehouse-ready architecture
Analytical clarity over tooling complexity
