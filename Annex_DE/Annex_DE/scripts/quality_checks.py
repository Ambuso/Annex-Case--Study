"""
quality_checks.py
=================
Data quality framework for the ABC Phones credit pipeline.

Design
------
* Every check is a function returning a `CheckResult`.
* Every check has a `severity` (info / warning / critical) and a `cadence`
  (real_time / daily / weekly).
* Results write to `outputs/dq_results.csv` and to the rolling pipeline log.
* `run_all()` returns nonzero exit code if any CRITICAL check fails — this
  is what an Airflow / Prefect task wraps to fail the DAG.

In production, the alerting layer is a thin shim: failures push to
PagerDuty (critical), Slack #data-alerts (warning), and a daily digest
email (info). Mocked here as log lines + the dq_results.csv artifact.

Five concrete checks implemented (matches the brief):
  1. Schema & freshness     — every expected snapshot file exists, has
                               the expected columns, and the internal DATE
                               matches the filename.
  2. Uniqueness             — no duplicate (loan_id, snapshot_date) keys.
  3. Referential integrity  — every loan_id in credit/NPS exists in
                               dim_customer; every NPS loan_id exists in
                               credit.
  4. Range / domain checks  — DOBs imply age 18-100; income > 0; nps_score
                               in [0,10]; dpd >= 0.
  5. Null thresholds        — critical fields below 1% null tolerance;
                               soft fields below 60%.

  + bonus business-logic check: derived dpd ≈ source dpd within tolerance.

Run:
    python scripts/quality_checks.py
"""
from __future__ import annotations

import glob
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "data" / "warehouse"
OUT = ROOT / "outputs"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("dq")
if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(LOGS / "pipeline.log"), logging.StreamHandler()],
    )

# Result type

@dataclass
class CheckResult:
    name: str
    severity: str        # 'info' | 'warning' | 'critical'
    cadence: str         # 'real_time' | 'daily' | 'weekly'
    passed: bool
    n_failed: int = 0
    detail: str = ""
    failures: list[dict] = field(default_factory=list)

    def emoji(self) -> str:
        if self.passed:
            return "✓"
        return {"info": "ℹ", "warning": "⚠", "critical": "✗"}[self.severity]



# CHECK 1 — Schema & freshness

EXPECTED_CREDIT_COLS = {
    "loan_id", "reporting_date", "snapshot_date", "customer_age", "total_paid",
    "total_due_today", "balance", "days_past_due", "closing_balance", "advance",
    "balance_due_to_date", "arrears", "balance_due_status", "payment",
    "expected_payment", "first_payment", "first_expected_payment",
    "account_status_l1", "account_status_l2", "return_date", "sale_date",
    "credit_check_done", "payment_amount", "adjustment_amount",
    "prepayment_amount", "deposit", "weekly_rate", "credit_expiry",
    "next_invoice_date", "discount", "overpayment_amount", "max_payment_date",
    "initial_pay", "total_paid_with_adjustments_15d",
}


def check_schema_and_freshness() -> CheckResult:
    files = sorted(glob.glob(str(WAREHOUSE / "stg_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    failures = []
    if not files:
        return CheckResult("schema_and_freshness", "critical", "real_time",
                           passed=False, n_failed=1,
                           detail="no credit snapshot partitions found")

    for f in files:
        df = pd.read_parquet(f, columns=None)
        missing = EXPECTED_CREDIT_COLS - set(df.columns)
        extra = set(df.columns) - EXPECTED_CREDIT_COLS
        # snapshot_date in path vs reporting_date in data
        path_date = Path(f).parent.name.split("=")[1]
        actual_dates = df["reporting_date"].dropna().dt.strftime("%Y-%m-%d").unique()

        if missing:
            failures.append({"file": f, "issue": "missing_cols", "detail": str(missing)})
        if len(actual_dates) != 1 or actual_dates[0] != path_date:
            failures.append({"file": f, "issue": "date_mismatch",
                             "detail": f"path={path_date}  data={list(actual_dates)}"})
    return CheckResult(
        name="schema_and_freshness",
        severity="critical",
        cadence="real_time",
        passed=len(failures) == 0,
        n_failed=len(failures),
        detail=f"checked {len(files)} snapshots",
        failures=failures,
    )



# CHECK 2 — Uniqueness of (loan_id, snapshot_date)

def check_uniqueness() -> CheckResult:
    files = sorted(glob.glob(str(WAREHOUSE / "fct_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    failures = []
    total_dups = 0
    for f in files:
        df = pd.read_parquet(f, columns=["loan_id", "snapshot_date"])
        dup_mask = df.duplicated(["loan_id", "snapshot_date"], keep=False)
        if dup_mask.any():
            n = int(dup_mask.sum())
            total_dups += n
            failures.append({"file": Path(f).parent.name, "n_dupes": n})
    return CheckResult(
        name="uniqueness_loan_snapshot",
        severity="critical",
        cadence="daily",
        passed=total_dups == 0,
        n_failed=total_dups,
        detail=f"{total_dups} duplicate (loan_id, snapshot_date) rows",
        failures=failures,
    )


# CHECK 3 — Referential integrity

def check_referential_integrity() -> CheckResult:
    cust = pd.read_parquet(WAREHOUSE / "dim_customer.parquet", columns=["loan_id"])
    cust_ids = set(cust["loan_id"])

    fct_files = sorted(glob.glob(str(WAREHOUSE / "fct_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    fct_ids: set[str] = set()
    for f in fct_files:
        fct_ids.update(pd.read_parquet(f, columns=["loan_id"])["loan_id"].unique())

    nps_ids = set(pd.read_parquet(WAREHOUSE / "stg_nps.parquet", columns=["loan_id"])["loan_id"])

    fct_orphans = fct_ids - cust_ids
    nps_orphans_vs_cust = nps_ids - cust_ids
    nps_orphans_vs_fct = nps_ids - fct_ids

    n_failed = len(fct_orphans) + len(nps_orphans_vs_cust)
    return CheckResult(
        name="referential_integrity",
        severity="warning",   # we accept partial coverage; alert but don't block
        cadence="daily",
        passed=n_failed == 0,
        n_failed=n_failed,
        detail=(
            f"credit→customer orphans: {len(fct_orphans)} | "
            f"nps→customer orphans: {len(nps_orphans_vs_cust)} | "
            f"nps→credit orphans: {len(nps_orphans_vs_fct)}"
        ),
        failures=[
            {"loan_id": x, "missing_in": "dim_customer"} for x in list(fct_orphans)[:50]
        ],
    )


# CHECK 4 — Range / domain checks

def check_ranges() -> CheckResult:
    cust = pd.read_parquet(WAREHOUSE / "dim_customer.parquet")
    nps = pd.read_parquet(WAREHOUSE / "stg_nps.parquet")

    failures = []

    # implied age 18..100 at the latest reporting date
    ref = pd.Timestamp("2025-12-30")
    age = ((ref - cust["dob"]).dt.days / 365.25).where(cust["dob"].notna())
    bad_age = cust.loc[age.notna() & ((age < 18) | (age > 100)), ["loan_id", "dob"]]
    if len(bad_age):
        failures.append({"check": "age_bounds", "n": int(len(bad_age))})

    # income > 0 (filter NaNs)
    bad_income = cust.loc[(cust["received_total"].notna()) & (cust["received_total"] <= 0), ["loan_id", "received_total"]]
    if len(bad_income):
        failures.append({"check": "income_positive", "n": int(len(bad_income))})

    # NPS score in [0,10]
    bad_nps = nps.loc[(nps["nps_score"] < 0) | (nps["nps_score"] > 10), ["loan_id", "nps_score"]]
    if len(bad_nps):
        failures.append({"check": "nps_score_range", "n": int(len(bad_nps))})

    # DPD >= 0
    fct_files = sorted(glob.glob(str(WAREHOUSE / "fct_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    n_neg_dpd = 0
    for f in fct_files:
        d = pd.read_parquet(f, columns=["days_past_due"])
        n_neg_dpd += int((d["days_past_due"] < 0).sum())
    if n_neg_dpd:
        failures.append({"check": "dpd_non_negative", "n": n_neg_dpd})

    n_failed = sum(x["n"] for x in failures)
    return CheckResult(
        name="range_checks",
        severity="warning",
        cadence="daily",
        passed=n_failed == 0,
        n_failed=n_failed,
        detail="; ".join(f"{x['check']}={x['n']}" for x in failures) or "all in range",
        failures=failures,
    )


# CHECK 5 — Null thresholds

NULL_TOLERANCES = {
    # critical fields — pipeline-breaking if null
    "loan_id":          0.00,
    "reporting_date":   0.00,
    "balance":          0.01,
    "account_status_l2":0.01,
    # soft fields — flag but tolerate higher null rate
    "next_invoice_date":0.20,
    "sale_date":        0.05,
}


def check_nulls() -> CheckResult:
    files = sorted(glob.glob(str(WAREHOUSE / "fct_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    breaches = []
    for f in files:
        df = pd.read_parquet(f)
        snap = Path(f).parent.name
        for col, tol in NULL_TOLERANCES.items():
            if col not in df.columns:
                breaches.append({"snapshot": snap, "col": col, "issue": "missing_column"})
                continue
            pct_null = df[col].isna().mean()
            if pct_null > tol:
                breaches.append({"snapshot": snap, "col": col,
                                 "pct_null": round(100*pct_null, 2), "tolerance": round(100*tol, 2)})
    return CheckResult(
        name="null_thresholds",
        severity="warning",
        cadence="daily",
        passed=len(breaches) == 0,
        n_failed=len(breaches),
        detail=f"{len(breaches)} breaches across {len(files)} snapshots",
        failures=breaches,
    )


# BONUS — DPD reconciliation (derived vs source)

def check_dpd_reconciliation() -> CheckResult:
    files = sorted(glob.glob(str(WAREHOUSE / "fct_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    rows = []
    for f in files:
        df = pd.read_parquet(f, columns=["loan_id", "days_past_due", "days_past_due_derived"])
        diff = (df["days_past_due_derived"].astype("Int64") - df["days_past_due"].astype("Int64")).abs()
        rows.append({
            "snapshot": Path(f).parent.name,
            "rows": len(df),
            "exact_match_pct": round(100*(diff == 0).mean(), 2),
            "within_7d_pct":   round(100*(diff <= 7).mean(), 2),
        })
    rep = pd.DataFrame(rows)
    # Drift threshold: at least 50% should match within 7 days; flag if not.
    breached = rep.loc[rep["within_7d_pct"] < 50]
    return CheckResult(
        name="dpd_reconciliation",
        severity="info",
        cadence="weekly",
        passed=len(breached) == 0,
        n_failed=len(breached),
        detail=rep.to_dict(orient="records"),
    )

# Runner

ALL_CHECKS = [
    check_schema_and_freshness,
    check_uniqueness,
    check_referential_integrity,
    check_ranges,
    check_nulls,
    check_dpd_reconciliation,
]


def run_all() -> int:
    results: list[CheckResult] = []
    for fn in ALL_CHECKS:
        r = fn()
        results.append(r)
        log.info(f"{r.emoji()} {r.name:30s} [{r.severity:8s}|{r.cadence:9s}] "
                 f"{'PASS' if r.passed else f'FAIL ({r.n_failed})'}  {r.detail if isinstance(r.detail, str) else ''}")

    # Persist results
    df_out = pd.DataFrame([
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "name": r.name, "severity": r.severity, "cadence": r.cadence,
            "passed": r.passed, "n_failed": r.n_failed,
            "detail": r.detail if isinstance(r.detail, str) else str(r.detail)[:500],
        } for r in results
    ])
    out_path = OUT / "dq_results.csv"
    if out_path.exists():
        old = pd.read_csv(out_path)
        df_out = pd.concat([old, df_out], ignore_index=True)
    df_out.to_csv(out_path, index=False)
    log.info(f"DQ results appended to {out_path}")

    # Mock alerting routes
    for r in results:
        if r.passed:
            continue
        if r.severity == "critical":
            log.error(f"[ALERT→PagerDuty]   {r.name}: {r.detail}")
        elif r.severity == "warning":
            log.warning(f"[ALERT→Slack #data-alerts]  {r.name}: {r.detail}")
        else:
            log.info(f"[DIGEST]  {r.name}: {r.detail}")

    # Exit nonzero on any critical failure (so the orchestrator fails the DAG)
    n_critical = sum(1 for r in results if not r.passed and r.severity == "critical")
    return 0 if n_critical == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())
