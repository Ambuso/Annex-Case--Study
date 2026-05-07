Here's the cleaned-up README:
markdown# ABC Phones Credit Portfolio — Annex DE Case Study

A lightweight but production-shaped data pipeline for ABC Phones' credit
portfolio: ingestion → cleaning → feature engineering → quality checks →
analysis. Built with Python + Pandas + DuckDB + Parquet — a lakehouse
pattern that runs on a laptop today and lifts cleanly into S3+Athena,
GCS+BigQuery, or Snowflake tomorrow with no SQL rewrites.

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

Deactivate the environment when finished:

```bash
deactivate
```

### Run the pipeline

```bash
python run_pipeline.py
```

End-to-end runtime ≈ 2.5 minutes. All outputs land in `outputs/`,
all intermediate Parquet tables in `data/warehouse/`, all logs in
`logs/pipeline.log`.

## Architecture

![ETL Pipeline Architecture](pipeline_design/architecture.png)

## Directory layout
.
├── run_pipeline.py              # single-driver orchestrator
├── pipeline_design/
│   ├── architecture.png         # rendered diagram
│   └── architecture.svg
├── scripts/
│   ├── data_profiling.py        # row counts, nulls, anomalies, relationships
│   ├── data_cleaning.py         # source → stg_* Parquet (per snapshot)
│   ├── feature_engineering.py   # stg_* → dim_customer + fct_credit_snapshot
│   ├── quality_checks.py        # 5+1 DQ checks, alerting routes
│   ├── analysis.py              # portfolio metrics + segments + NPS join
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
│   ├── data_quality_report.md   # profiling findings
│   ├── profile_*.csv            # per-column profiles
│   ├── dq_results.csv           # rolling DQ check log
│   ├── portfolio_metrics.csv    # KPIs by snapshot
│   ├── portfolio_by_segment.csv
│   ├── nps_by_risk.csv
│   ├── cleaned_summary.csv
│   └── analysis_findings.md     # narrative for slides
├── slides/
│   └── Annex_DE_Presentation.pdf
└── logs/
└── pipeline.log

## Tech choices

| Concern | Choice | Why |
|---|---|---|
| Storage | Parquet, Hive-partitioned by `snapshot_date` | Columnar, compressed, native to every cloud warehouse |
| Compute | Pandas (cleaning/features) + DuckDB (SQL analytics) | Pandas for row-wise transforms; DuckDB for fast Parquet SQL with no warehouse |
| Orchestration | `run_pipeline.py` (this submission) | Production target: Airflow / Prefect / Dagster — one task per stage |
| Quality | Custom Python checks with severity + cadence | Production target: Great Expectations or dbt tests against the same Parquet |
| Alerting | Mocked log routes (PagerDuty / Slack / digest) | Drop-in replacement with real SDKs in prod |

## Key decisions & assumptions

These are the calls I made; each is also justified inline in the code.

1. **No customer_id exists in source.** Joins are loan-to-loan via `LOAN_ID` /
   `Loan Id`. Multi-loan customers are not identifiable. **Recommend** adding
   a stable customer key upstream.

2. **`Loan Id` vs `Loan Id ` (trailing space).** Cleaned on ingest by

```python
   df.columns = [c.strip() for c in df.columns]
```

3. **DOB conflicts (471 loans).** Resolved by provider priority
TRANSUNION > SMILEID > SPINMOBILE

   then most recent `createdAt UTC`. The credit bureau is treated as authoritative.

4. **Income `Received` field used as canonical total.** The other income
   columns (`Persons Received From Total`, `Banks Received`,
   `Paybills Received Others`) look like channel sub-totals — naive sum risks
   double-counting. Documented as a gap.

5. **`Duration` assumed to be months** (matches `LOAN_TERM='12M'` semantics).

6. **`days_past_due` derived independently** from
(reporting_date - next_invoice_date)

   per the brief, *and* the source value retained for reconciliation. They
   match within 7 days for ~55% of rows; the gap is a known modelling
   difference (next-invoice vs earliest-unpaid-invoice). Surfaced as a
   weekly DQ check.

7. **`risk_category`**: standard PAR-bucket framework adapted to ABC Phones'
   `ACCOUNT_STATUS_L2`:

   - **Critical** = Write Off / Lost Write Off OR DPD ≥ 90
   - **High**     = DPD 31-89 OR L2 ∈ {PAR 30, FMD}
   - **Medium**   = DPD 1-30 OR L2 ∈ {PAR 7, FPD, Inactive}
   - **Low**      = DPD 0 AND L2 = Active
   - **Closed**   = L2 = Paid Off       (out of active book)
   - **Returned** = L2 = Return         (out of active book)

8. **Demo rows excluded** (`ACCOUNT_STATUS_L1='Demo'`, 8 rows total). Test data.

9. **Missing customer-side data NOT dropped** from the credit fact. Carried
   as `age_band='Unknown'`, `income_band='Unknown'`. This preserves the
   credit book and surfaces coverage as a real metric — and turned up our
   biggest finding (see `analysis_findings.md`).

10. **Snapshot dates are quarterly** (1/1, 3/31, 6/30, 9/30, 12/30). One
    file (`30-03-2025`) has internal `DATE = 3/31/2025` — captured by the
    schema_and_freshness DQ check and flagged in slides as the worked
    real-world example.

## Reproducing this submission

Tested on Python 3.12. Dependencies:
pandas>=2.0
pyarrow>=15
duckdb>=1.0
openpyxl
matplotlib
cairosvg

Place the source files in `data/raw/`:
Credit_Data_-01-01-2025.csv
Credit_Data-30-03-2025.csv
Credit_Data-30-06-2025.csv
Credit_Data-30-09-2025.csv
Credit_Data-_30-12-2025.csv
Credit_Data_Definitions.xlsx
Sales_and_Customer_Data.xlsx
NPS_Data.xlsx

Then run:

```bash
python run_pipeline.py
```

Individual stages are runnable on their own:

```bash
python scripts/data_cleaning.py
```

Each stage is idempotent.

## Production-roadmap delta

What changes when this scales beyond the take-home?

- **Orchestration:** Airflow DAG with one task per stage, `snapshot_date`
  as the run_id, retries with exponential backoff, SLAs per task.
- **Storage:** S3 with Hive-style prefixes; same Parquet, same partitioning.
- **Compute:** DuckDB locally → Athena or BigQuery in cloud. The same SQL
  in `analysis.py` runs unchanged.
- **Transformation:** wrap the SQL in **dbt** so transformations get
  documentation, lineage, and tests for free.
- **Quality:** swap custom checks for **Great Expectations** suites or
  dbt tests; surface results in **Soda Cloud** or **Monte Carlo**.
- **Alerting:** real PagerDuty/Slack integrations; on-call rota.
- **Observability:** **OpenLineage** events emitted from each task.
