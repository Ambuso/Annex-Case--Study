"""
generate_architecture_diagram.py
--------------

Renders the ETL pipeline architecture as architecture.svg and architecture.png
for inclusion in the slide deck and submission.

Approach: hand-written SVG (full control over typography and layout),
converted to PNG via cairosvg.

Run:
    python scripts/generate_architecture_diagram.py
"""

from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline_design"
OUT.mkdir(parents=True, exist_ok=True)


SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" font-family="Inter, -apple-system, system-ui, sans-serif">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#374151"/>
    </marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#dc2626"/>
    </marker>
    <linearGradient id="srcGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fef3c7"/>
      <stop offset="100%" stop-color="#fde68a"/>
    </linearGradient>
    <linearGradient id="stgGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#dbeafe"/>
      <stop offset="100%" stop-color="#bfdbfe"/>
    </linearGradient>
    <linearGradient id="martGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#dcfce7"/>
      <stop offset="100%" stop-color="#bbf7d0"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Title -->
  <text x="640" y="36" text-anchor="middle" font-size="22" font-weight="700" fill="#111827">
    ABC Phones — Credit Portfolio ETL Pipeline
  </text>
  <text x="640" y="58" text-anchor="middle" font-size="13" fill="#6b7280">
    Python · Pandas · DuckDB · Parquet  |  Lakehouse pattern, cloud-portable
  </text>

  <!-- Lane labels -->
  <text x="120" y="105" text-anchor="middle" font-size="12" font-weight="600" fill="#92400e" letter-spacing="1">SOURCES</text>
  <text x="380" y="105" text-anchor="middle" font-size="12" font-weight="600" fill="#1e40af" letter-spacing="1">INGEST · CLEAN</text>
  <text x="640" y="105" text-anchor="middle" font-size="12" font-weight="600" fill="#1e40af" letter-spacing="1">TRANSFORM · FEATURE</text>
  <text x="900" y="105" text-anchor="middle" font-size="12" font-weight="600" fill="#166534" letter-spacing="1">SERVE</text>
  <text x="1140" y="105" text-anchor="middle" font-size="12" font-weight="600" fill="#166534" letter-spacing="1">CONSUMERS</text>

  <!-- ============== SOURCES ============== -->
  <g filter="url(#shadow)">
    <rect x="40" y="130" width="160" height="60" rx="8" fill="url(#srcGrad)" stroke="#d97706" stroke-width="1"/>
    <text x="120" y="155" text-anchor="middle" font-size="13" font-weight="600" fill="#78350f">Credit CSVs</text>
    <text x="120" y="174" text-anchor="middle" font-size="11" fill="#78350f">5 quarterly snapshots</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="40" y="210" width="160" height="60" rx="8" fill="url(#srcGrad)" stroke="#d97706" stroke-width="1"/>
    <text x="120" y="235" text-anchor="middle" font-size="13" font-weight="600" fill="#78350f">Sales · Customer XLSX</text>
    <text x="120" y="254" text-anchor="middle" font-size="11" fill="#78350f">4 sheets (sales/dob/etc.)</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="40" y="290" width="160" height="60" rx="8" fill="url(#srcGrad)" stroke="#d97706" stroke-width="1"/>
    <text x="120" y="315" text-anchor="middle" font-size="13" font-weight="600" fill="#78350f">NPS XLSX</text>
    <text x="120" y="334" text-anchor="middle" font-size="11" fill="#78350f">survey responses</text>
  </g>

  <!-- ============== INGEST · CLEAN ============== -->
  <g filter="url(#shadow)">
    <rect x="290" y="130" width="180" height="220" rx="10" fill="white" stroke="#3b82f6" stroke-width="1.5"/>
    <text x="380" y="153" text-anchor="middle" font-size="13" font-weight="700" fill="#1e40af">data_cleaning.py</text>
    <line x1="305" y1="163" x2="455" y2="163" stroke="#dbeafe"/>
    <text x="305" y="183" font-size="11" fill="#374151">• schema validation</text>
    <text x="305" y="203" font-size="11" fill="#374151">• date standardisation</text>
    <text x="305" y="223" font-size="11" fill="#374151">• enum normalisation</text>
    <text x="305" y="243" font-size="11" fill="#374151">• demo-row removal</text>
    <text x="305" y="263" font-size="11" fill="#374151">• DOB / income dedupe</text>
    <text x="305" y="283" font-size="11" fill="#374151">  with priority rules</text>
    <text x="305" y="307" font-size="10" fill="#6b7280">↓ writes Parquet:</text>
    <text x="305" y="322" font-size="10" font-style="italic" fill="#6b7280">  stg_credit_snapshot/</text>
    <text x="305" y="335" font-size="10" font-style="italic" fill="#6b7280">  stg_customer · stg_nps</text>
  </g>

  <!-- ============== TRANSFORM ============== -->
  <g filter="url(#shadow)">
    <rect x="550" y="130" width="180" height="220" rx="10" fill="white" stroke="#3b82f6" stroke-width="1.5"/>
    <text x="640" y="153" text-anchor="middle" font-size="13" font-weight="700" fill="#1e40af">feature_engineering.py</text>
    <line x1="565" y1="163" x2="715" y2="163" stroke="#dbeafe"/>
    <text x="565" y="183" font-size="11" fill="#374151">• age_band (per snapshot)</text>
    <text x="565" y="203" font-size="11" fill="#374151">• avg_monthly_income_band</text>
    <text x="565" y="223" font-size="11" fill="#374151">• days_past_due (derived)</text>
    <text x="565" y="243" font-size="11" fill="#374151">• risk_category (Low/Med/</text>
    <text x="565" y="259" font-size="11" fill="#374151">  High/Critical/Closed)</text>
    <text x="565" y="307" font-size="10" fill="#6b7280">↓ writes Parquet:</text>
    <text x="565" y="322" font-size="10" font-style="italic" fill="#6b7280">  fct_credit_snapshot/</text>
    <text x="565" y="335" font-size="10" font-style="italic" fill="#6b7280">  dim_customer</text>
  </g>

  <!-- ============== SERVE ============== -->
  <g filter="url(#shadow)">
    <rect x="810" y="130" width="180" height="60" rx="8" fill="url(#martGrad)" stroke="#16a34a" stroke-width="1"/>
    <text x="900" y="155" text-anchor="middle" font-size="13" font-weight="600" fill="#14532d">fct_credit_snapshot</text>
    <text x="900" y="174" text-anchor="middle" font-size="11" fill="#14532d">partitioned by date · Parquet</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="810" y="210" width="180" height="60" rx="8" fill="url(#martGrad)" stroke="#16a34a" stroke-width="1"/>
    <text x="900" y="235" text-anchor="middle" font-size="13" font-weight="600" fill="#14532d">dim_customer</text>
    <text x="900" y="254" text-anchor="middle" font-size="11" fill="#14532d">one row per loan · Parquet</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="810" y="290" width="180" height="60" rx="8" fill="url(#martGrad)" stroke="#16a34a" stroke-width="1"/>
    <text x="900" y="315" text-anchor="middle" font-size="13" font-weight="600" fill="#14532d">stg_nps</text>
    <text x="900" y="334" text-anchor="middle" font-size="11" fill="#14532d">survey · Parquet</text>
  </g>

  <!-- ============== CONSUMERS ============== -->
  <g filter="url(#shadow)">
    <rect x="1060" y="130" width="160" height="60" rx="8" fill="white" stroke="#16a34a" stroke-width="1.5"/>
    <text x="1140" y="155" text-anchor="middle" font-size="12" font-weight="600" fill="#14532d">DuckDB ad-hoc</text>
    <text x="1140" y="174" text-anchor="middle" font-size="11" fill="#14532d">analyst SQL</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="1060" y="210" width="160" height="60" rx="8" fill="white" stroke="#16a34a" stroke-width="1.5"/>
    <text x="1140" y="235" text-anchor="middle" font-size="12" font-weight="600" fill="#14532d">analysis.py</text>
    <text x="1140" y="254" text-anchor="middle" font-size="11" fill="#14532d">portfolio_metrics.csv</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="1060" y="290" width="160" height="60" rx="8" fill="white" stroke="#16a34a" stroke-width="1.5"/>
    <text x="1140" y="315" text-anchor="middle" font-size="12" font-weight="600" fill="#14532d">BI / dashboards</text>
    <text x="1140" y="334" text-anchor="middle" font-size="11" fill="#14532d">Looker · Metabase</text>
  </g>

  <!-- Arrows: sources → cleaning -->
  <line x1="200" y1="160" x2="285" y2="200" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="200" y1="240" x2="285" y2="240" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="200" y1="320" x2="285" y2="280" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>

  <!-- cleaning → transform -->
  <line x1="470" y1="240" x2="545" y2="240" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>

  <!-- transform → marts -->
  <line x1="730" y1="180" x2="805" y2="160" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="730" y1="240" x2="805" y2="240" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="470" y1="320" x2="805" y2="320" stroke="#374151" stroke-width="1.4" stroke-dasharray="3,3" marker-end="url(#arrow)"/>

  <!-- marts → consumers -->
  <line x1="990" y1="160" x2="1055" y2="160" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="990" y1="240" x2="1055" y2="240" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>
  <line x1="990" y1="320" x2="1055" y2="320" stroke="#374151" stroke-width="1.4" marker-end="url(#arrow)"/>

  <!-- ============== QUALITY + ORCHESTRATION (cross-cutting band below) ============== -->
  <g filter="url(#shadow)">
    <rect x="40" y="410" width="950" height="80" rx="10" fill="#fef2f2" stroke="#dc2626" stroke-width="1.5"/>
    <text x="60" y="436" font-size="13" font-weight="700" fill="#991b1b">quality_checks.py — runs after every transform</text>
    <text x="60" y="458" font-size="11" fill="#7f1d1d">5 checks: schema/freshness · uniqueness · referential integrity · range · null thresholds  +  bonus DPD reconciliation</text>
    <text x="60" y="476" font-size="11" fill="#7f1d1d">CRITICAL fail → PagerDuty + DAG halt    |    WARNING → Slack #data-alerts    |    INFO → daily digest email</text>
  </g>
  <!-- arrow showing checks tap the warehouse -->
  <line x1="900" y1="350" x2="900" y2="408" stroke="#dc2626" stroke-width="1.4" stroke-dasharray="3,3" marker-end="url(#arrow-red)"/>

  <g filter="url(#shadow)">
    <rect x="40" y="510" width="950" height="80" rx="10" fill="#f3f4f6" stroke="#6b7280" stroke-width="1.5"/>
    <text x="60" y="536" font-size="13" font-weight="700" fill="#1f2937">run_pipeline.py — orchestration driver</text>
    <text x="60" y="558" font-size="11" fill="#374151">This submission: single Python driver runs cleaning → features → quality → analysis with structured logging to logs/pipeline.log</text>
    <text x="60" y="576" font-size="11" fill="#374151">Production: Airflow / Prefect / Dagster DAG with one task per script, idempotent rerun by snapshot_date partition, retries + SLA monitoring</text>
  </g>

  <!-- Storage layer band -->
  <g filter="url(#shadow)">
    <rect x="1060" y="410" width="160" height="180" rx="10" fill="white" stroke="#6b7280" stroke-width="1.5" stroke-dasharray="3,3"/>
    <text x="1140" y="436" text-anchor="middle" font-size="13" font-weight="700" fill="#1f2937">Cloud-portable</text>
    <text x="1140" y="458" text-anchor="middle" font-size="11" fill="#374151">Parquet + DuckDB</text>
    <text x="1140" y="475" text-anchor="middle" font-size="11" fill="#374151">→ S3 + Athena</text>
    <text x="1140" y="492" text-anchor="middle" font-size="11" fill="#374151">→ GCS + BigQuery</text>
    <text x="1140" y="509" text-anchor="middle" font-size="11" fill="#374151">→ Snowflake</text>
    <text x="1140" y="544" text-anchor="middle" font-size="11" fill="#374151" font-style="italic">Same SQL,</text>
    <text x="1140" y="560" text-anchor="middle" font-size="11" fill="#374151" font-style="italic">no rewrite</text>
  </g>

  <!-- Footer note -->
  <text x="640" y="660" text-anchor="middle" font-size="11" fill="#6b7280">
    Hive-partitioning by snapshot_date enables idempotent reruns and incremental loads — drop a partition, replace it, leave the rest untouched.
  </text>
  <text x="640" y="680" text-anchor="middle" font-size="11" fill="#6b7280">
    Every step is a pure function with a CleaningReport / CheckResult — easy to unit-test and trace.
  </text>
</svg>
"""

(OUT / "architecture.svg").write_text(SVG)
cairosvg.svg2png(bytestring=SVG.encode("utf-8"), write_to=str(OUT / "architecture.png"), output_width=1920)
print(f"✔ wrote {OUT / 'architecture.svg'}")
print(f"✔ wrote {OUT / 'architecture.png'}")
