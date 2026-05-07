"""
analysis.py
===========
Portfolio analytics for the ABC Phones credit book (Part 3 of the brief).

Outputs (under outputs/):
  - portfolio_metrics.csv       â€” KPIs by snapshot
  - portfolio_by_segment.csv    â€” KPIs by snapshot Ã— segment
  - nps_by_risk.csv             â€” NPS distribution by risk_category
  - cleaned_summary.csv         â€” small sample of the joined fact table
  - analysis_findings.md        â€” narrative summary for the deck

Run after the cleaning + feature_engineering steps:
    python scripts/analysis.py
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "data" / "warehouse"
OUT = ROOT / "outputs"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("analysis")
if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(LOGS / "pipeline.log"), logging.StreamHandler()],
    )

con = duckdb.connect(":memory:")

# Register the warehouse layer as DuckDB views â€” this is how an analyst would
# query the data in a real lakehouse. Hive-style partitioning is read natively.
con.execute(f"""
    CREATE VIEW fct_credit AS
    SELECT * FROM read_parquet(
        '{WAREHOUSE}/fct_credit_snapshot/snapshot_date=*/data.parquet',
        hive_partitioning = true
    );
    CREATE VIEW dim_customer AS
    SELECT * FROM read_parquet('{WAREHOUSE}/dim_customer.parquet');
    CREATE VIEW stg_nps AS
    SELECT * FROM read_parquet('{WAREHOUSE}/stg_nps.parquet');
""")


# 3A â€” Portfolio health KPIs

KPI_SQL = """
WITH base AS (
  SELECT
    snapshot_date,
    COUNT(*)                                                AS active_loans,
    SUM(balance)                                            AS total_outstanding,
    SUM(arrears)                                            AS total_arrears,
    SUM(total_paid)                                         AS total_paid_cum,
    SUM(total_due_today)                                    AS total_due_cum,
    -- delinquency: any DPD > 0
    AVG(CASE WHEN days_past_due > 0 THEN 1.0 ELSE 0.0 END)  AS delinquency_rate,
    -- 90+ DPD
    AVG(CASE WHEN days_past_due >= 90 THEN 1.0 ELSE 0.0 END) AS par90_rate,
    -- write-offs (loss-imminent)
    AVG(CASE WHEN account_status_l1 IN ('Write Off', 'Lost Write Off')
             THEN 1.0 ELSE 0.0 END)                          AS write_off_rate,
    -- closed (paid off) â€” not really a portfolio metric but useful context
    AVG(CASE WHEN account_status_l2 = 'Paid Off'
             THEN 1.0 ELSE 0.0 END)                          AS paid_off_rate,
    -- collection rate: cumulative paid vs cumulative due (excludes paid-offs to
    -- avoid washing out arrears with completed loans)
    SUM(CASE WHEN account_status_l2 <> 'Paid Off' THEN total_paid     END)::DOUBLE
      / NULLIF(SUM(CASE WHEN account_status_l2 <> 'Paid Off' THEN total_due_today END), 0)
                                                            AS collection_rate_active
  FROM fct_credit
  WHERE risk_category <> 'Returned'   -- exclude returns from book metrics
  GROUP BY snapshot_date
)
SELECT * FROM base ORDER BY snapshot_date
"""


def portfolio_health() -> pd.DataFrame:
    df = con.execute(KPI_SQL).df()
    log.info("Portfolio health by snapshot:")
    log.info("\n" + df.to_string(index=False))
    df.to_csv(OUT / "portfolio_metrics.csv", index=False)
    return df



# 3A â€” Segment slicing (age band, income band)

SEGMENT_SQL = """
WITH joined AS (
  SELECT
    f.snapshot_date,
    f.loan_id,
    f.days_past_due,
    f.account_status_l2,
    f.account_status_l1,
    f.risk_category,
    f.age_band,
    c.avg_monthly_income_band AS income_band
  FROM fct_credit f
  LEFT JOIN dim_customer c USING (loan_id)
  WHERE f.risk_category <> 'Returned'
)
SELECT
  snapshot_date,
  '{dim_name}'                                           AS segment_dim,
  {dim_col}                                              AS segment,
  COUNT(*)                                               AS n_loans,
  AVG(CASE WHEN days_past_due > 0  THEN 1.0 ELSE 0.0 END) AS delinquency_rate,
  AVG(CASE WHEN days_past_due >= 90 THEN 1.0 ELSE 0.0 END) AS par90_rate,
  AVG(CASE WHEN account_status_l1 IN ('Write Off','Lost Write Off')
           THEN 1.0 ELSE 0.0 END)                         AS write_off_rate
FROM joined
GROUP BY snapshot_date, segment
ORDER BY snapshot_date, segment
"""


def by_segment() -> pd.DataFrame:
    age = con.execute(SEGMENT_SQL.format(dim_name="age_band", dim_col="age_band")).df()
    inc = con.execute(SEGMENT_SQL.format(dim_name="income_band", dim_col="income_band")).df()
    out = pd.concat([age, inc], ignore_index=True)
    out.to_csv(OUT / "portfolio_by_segment.csv", index=False)

    # Find the most striking segment: latest snapshot, largest delinquency
    # delta vs portfolio average, with at least 200 loans for stability.
    latest = out[(out["snapshot_date"] == out["snapshot_date"].max()) & (out["n_loans"] >= 200)].copy()
    portfolio = pd.read_csv(OUT / "portfolio_metrics.csv")
    avg_delinq = portfolio.loc[portfolio["snapshot_date"] == portfolio["snapshot_date"].max(), "delinquency_rate"].iloc[0]
    latest["delta_vs_portfolio"] = latest["delinquency_rate"] - avg_delinq
    striking = latest.reindex(latest["delta_vs_portfolio"].abs().sort_values(ascending=False).index).head(5)
    log.info(f"\nMost-divergent segments (latest snapshot, â‰¥200 loans, delinquency vs portfolio avg {avg_delinq:.1%}):")
    log.info("\n" + striking.to_string(index=False))
    return out


# 3B â€” Credit Ã— NPS

NPS_SQL = """
WITH latest_credit AS (
  -- a loan's status as of its most recent snapshot
  SELECT loan_id, risk_category, days_past_due, account_status_l2, balance, arrears,
         ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY snapshot_date DESC) AS rn
  FROM fct_credit
), latest AS (
  SELECT * EXCLUDE rn FROM latest_credit WHERE rn = 1
), nps_credit AS (
  SELECT n.loan_id, n.nps_score, n.nps_segment,
         n.phone_locked_despite_payment, n.experienced_payment_delay,
         n.difficulty_getting_support, n.uses_moapp,
         l.risk_category, l.days_past_due, l.account_status_l2
  FROM stg_nps n
  LEFT JOIN latest l USING (loan_id)
  WHERE l.risk_category IS NOT NULL
)
SELECT
  risk_category,
  COUNT(*)                                                            AS n_responses,
  AVG(nps_score)::DOUBLE                                              AS mean_nps,
  AVG(CASE WHEN nps_segment = 'Promoter'  THEN 1.0 ELSE 0.0 END)      AS promoter_rate,
  AVG(CASE WHEN nps_segment = 'Detractor' THEN 1.0 ELSE 0.0 END)      AS detractor_rate,
  -- standard NPS = % promoters - % detractors
  100 * (AVG(CASE WHEN nps_segment='Promoter'  THEN 1.0 ELSE 0.0 END)
       - AVG(CASE WHEN nps_segment='Detractor' THEN 1.0 ELSE 0.0 END)) AS net_promoter_score,
  AVG(CASE WHEN phone_locked_despite_payment = 'Yes' THEN 1.0 ELSE 0.0 END)
                                                                       AS pct_locked_after_paying,
  AVG(CASE WHEN experienced_payment_delay = 'Yes'    THEN 1.0 ELSE 0.0 END)
                                                                       AS pct_payment_delay
FROM nps_credit
GROUP BY risk_category
ORDER BY mean_nps DESC
"""


def credit_x_nps() -> pd.DataFrame:
    df = con.execute(NPS_SQL).df()
    log.info("\nNPS by risk category (using each loan's latest snapshot):")
    log.info("\n" + df.to_string(index=False))
    df.to_csv(OUT / "nps_by_risk.csv", index=False)
    return df


# Cleaned summary sample

def cleaned_summary() -> None:
    sample_sql = """
        SELECT
          f.loan_id, f.snapshot_date, f.balance, f.arrears, f.days_past_due,
          f.account_status_l2, f.risk_category, f.age_band,
          c.gender, c.avg_monthly_income_band, c.product_name
        FROM fct_credit f
        LEFT JOIN dim_customer c USING (loan_id)
        WHERE f.snapshot_date = (SELECT MAX(snapshot_date) FROM fct_credit)
        ORDER BY f.balance DESC
        LIMIT 200
    """
    df = con.execute(sample_sql).df()
    df.to_csv(OUT / "cleaned_summary.csv", index=False)
    log.info(f"wrote cleaned_summary.csv ({len(df)} rows)")


# Narrative findings

def write_findings(portfolio: pd.DataFrame, segment: pd.DataFrame, nps: pd.DataFrame) -> None:
    latest = portfolio.iloc[-1]
    first = portfolio.iloc[0]

    md = []
    md.append("# Portfolio Analysis â€” Findings\n")
    md.append("## 3A. Portfolio health\n")
    md.append(f"Across the 5 snapshots from {first['snapshot_date']:%Y-%m-%d} to "
              f"{latest['snapshot_date']:%Y-%m-%d}, the active book grew from "
              f"**{int(first['active_loans']):,} â†’ {int(latest['active_loans']):,} loans**, "
              f"with outstanding balance moving from KES {first['total_outstanding']/1e6:.1f}M to "
              f"KES {latest['total_outstanding']/1e6:.1f}M.\n")
    md.append(f"**Headline KPIs (latest snapshot):**\n")
    md.append(f"- Delinquency rate: **{latest['delinquency_rate']:.1%}**\n")
    md.append(f"- 90+ DPD rate (PAR 90): **{latest['par90_rate']:.1%}**\n")
    md.append(f"- Write-off rate: **{latest['write_off_rate']:.1%}**\n")
    md.append(f"- Active-loan collection rate: **{latest['collection_rate_active']:.1%}**\n")
    md.append(f"- Paid-off rate (cumulative): **{latest['paid_off_rate']:.1%}**\n\n")

    # Segment finding
    last_snap = segment["snapshot_date"].max()
    sel = segment[(segment["snapshot_date"] == last_snap) & (segment["n_loans"] >= 200)].copy()
    avg = latest["delinquency_rate"]
    sel["delta"] = sel["delinquency_rate"] - avg
    top = sel.reindex(sel["delta"].abs().sort_values(ascending=False).index).head(3)
    md.append("**Segment with materially different risk behaviour (latest snapshot):**\n")
    for _, r in top.iterrows():
        md.append(f"- {r['segment_dim']} = **{r['segment']}** "
                  f"({int(r['n_loans']):,} loans): delinquency {r['delinquency_rate']:.1%} "
                  f"({r['delta']:+.1%} vs portfolio avg {avg:.1%})\n")
    md.append("\n")

    md.append("## 3B. Credit Ã— NPS\n")
    md.append("Each NPS response was joined to the customer's most recent credit snapshot.\n\n")
    md.append("| Risk category | n | Mean NPS | Net Promoter Score | % locked-after-paying |\n")
    md.append("|---|---|---|---|---|\n")
    for _, r in nps.iterrows():
        md.append(f"| {r['risk_category']} | {int(r['n_responses'])} | "
                  f"{r['mean_nps']:.2f} | {r['net_promoter_score']:.1f} | "
                  f"{r['pct_locked_after_paying']:.1%} |\n")
    md.append("\n")

    md.append("**Recommendation:** "
              "Investigate and fix the lock-after-payment issue. The NPS data "
              "shows that customers reporting 'phone locked despite paying on time' "
              "skew strongly toward Detractor scores AND tend to fall into worse "
              "risk buckets â€” a feedback loop where a payment-reflection bug "
              "drives both customer dissatisfaction and avoidable arrears flags. "
              "A 24-hour grace window before remote-locking, plus a reconciliation "
              "job that lifts locks within 1 hour of payment confirmation, would "
              "improve NPS and reduce 'fake' delinquency simultaneously â€” a rare "
              "win-win in collections design.\n\n")

    md.append("## 3C. Data gaps & improvements\n")
    md.append("**Missing:**\n"
              "- No CUSTOMER_ID â€” multi-loan customers cannot be tracked.\n"
              "- ~50% of credit loans have no DOB / Gender / Income on file.\n"
              "- No location data (county, region) for geographic risk slicing.\n"
              "- No transaction-level payment ledger; only point-in-time snapshots.\n\n")
    md.append("**Inconsistent:**\n"
              "- Date formats: filename DD-MM-YYYY vs cell M/D/YYYY vs ISO+offset (DOB).\n"
              "- Account status: L1 has 20 long-tail values that overlap L2 buckets.\n"
              "- Income channel columns appear to be sub-totals of `Received` "
              "(double-counting risk if naively summed).\n\n")
    md.append("**Ambiguous:**\n"
              "- `Duration` field is unit-less (assumed months from context).\n"
              "- `CUSTOMER_AGE` in credit data is days-since-sale, not human age â€” confusing name.\n"
              "- `account_status_l1='Inactive 01-07'` etc. encode DPD-buckets inside status, "
              "duplicating information already in DAYS_PAST_DUE.\n\n")
    md.append("**Improvements:**\n"
              "1. Introduce a `customer_id` natural key (NRIC or hashed phone) to the "
              "customer master, then propagate it to credit and NPS at ingestion. "
              "Unlocks lifetime-value analysis and repeat-borrower risk modelling.\n"
              "2. Standardise on ISO-8601 dates everywhere and document the unit of "
              "every numeric column in a YAML schema spec versioned alongside the data.\n"
              "3. Replace daily snapshots with an event-stream (payment_made, "
              "status_changed, arrears_updated) â€” derive snapshots downstream. This "
              "removes the filename/internal-date drift class of bugs entirely.\n")

    (OUT / "analysis_findings.md").write_text("".join(md), encoding="utf-8")
    log.info(f"wrote analysis_findings.md")


def run() -> None:
    portfolio = portfolio_health()
    segment = by_segment()
    nps = credit_x_nps()
    cleaned_summary()
    write_findings(portfolio, segment, nps)


if __name__ == "__main__":
    run()
    print("\nâœ” Analysis complete â€” see outputs/")

