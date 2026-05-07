# ABC Phones Credit Portfolio — Annex DE Case Study

A lightweight but production-shaped data pipeline for ABC Phones' credit
portfolio: ingestion → cleaning → feature engineering → quality checks →
analysis. Built with Python + Pandas + DuckDB + Parquet — a lakehouse
pattern that runs on a laptop today and lifts cleanly into S3+Athena,
GCS+BigQuery, or Snowflake tomorrow with no SQL rewrites.

---

## Pipeline Architecture

![Pipeline Architecture](pipeline_design/architecture.png)

This diagram shows the full end-to-end flow:
raw ingestion → staging → feature engineering → quality checks → analytics layer.

---

## TL;DR

### Create and activate a virtual environment

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Windows (Git Bash)

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Deactivate:

```bash
deactivate
```

---

### Run the pipeline

```bash
pip install -r requirements.txt
python run_pipeline.py
```

End-to-end runtime ≈ 2.5 minutes.

Outputs:
- `outputs/` → reports & analytics
- `data/warehouse/` → Parquet lakehouse tables
- `logs/` → pipeline logs

---

## Directory layout

```
.
├── run_pipeline.py
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
│   ├── raw/
│   └── warehouse/
├── outputs/
├── slides/
└── logs/
```

---

## Tech choices

| Layer | Tooling | Reason |
|------|--------|--------|
| Storage | Parquet (Hive-partitioned) | Fast, compressed, cloud-native |
| Transform | Pandas + DuckDB | Simple local + scalable SQL |
| Orchestration | Python driver script | Easy upgrade to Airflow/Prefect |
| Quality | Custom DQ checks | Replaceable with Great Expectations |
| Analytics | DuckDB SQL | Zero warehouse dependency |

---

## Key decisions & assumptions

- No `customer_id` → loan-level joins only
- Column cleanup handled via `.strip()`
- DOB conflicts resolved via bureau priority:
  `TRANSUNION > SMILEID > SPINMOBILE`
- Income fields treated carefully to avoid double counting
- `risk_category` derived using PAR-style buckets
- Missing customer attributes retained as `"Unknown"` (important signal)
- One dataset contains intentional date mismatch → flagged in DQ checks

---

## Reproducing

```bash
python -m venv .venv
source .venv/bin/activate   # or Activate.ps1 on Windows
pip install -r requirements.txt
python run_pipeline.py
```

---

## Production roadmap

- Airflow orchestration per stage
- S3 + Athena / BigQuery migration
- dbt transformations for SQL layer
- Great Expectations for data quality
- OpenLineage for observability
- Slack / PagerDuty alerting

---
