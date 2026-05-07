"""
feature_engineering.py
-------------------------------
Derived features for the ABC Phones credit portfolio.

Features produced (per the brief, Part 1B):
  - age_band                   : Calculated from DOB at each reporting date.
  - avg_monthly_income_band    : Income / employment duration (months).
  - days_past_due              : Independently derived; validated vs source.
  - risk_category              : Low / Medium / High / Critical, from
                                  account status + DPD + arrears.

Inputs
------
  data/warehouse/stg_credit_snapshot/snapshot_date=YYYY-MM-DD/data.parquet
  data/warehouse/stg_customer.parquet

Outputs
-------
  data/warehouse/dim_customer.parquet                   — one row per loan_id
  data/warehouse/fct_credit_snapshot/                    — partitioned facts
      snapshot_date=YYYY-MM-DD/data.parquet
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "data" / "warehouse"
LOGS = ROOT / "logs"

log = logging.getLogger("features")
if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(LOGS / "pipeline.log"), logging.StreamHandler()],
    )

# 1. Age band — computed at a given reference date


AGE_BANDS = [
    (18, 25, "18-25"),
    (26, 35, "26-35"),
    (36, 45, "36-45"),
    (46, 55, "46-55"),
    (56, 120, "55+"),
]


def compute_age(dob: pd.Series, ref_date: pd.Timestamp | pd.Series) -> pd.Series:
    """Age in completed years at ref_date. NaT-safe."""
    if isinstance(ref_date, pd.Timestamp):
        ref = pd.Series([ref_date] * len(dob), index=dob.index)
    else:
        ref = ref_date
    delta_years = (ref - dob).dt.days / 365.25
    return np.floor(delta_years).astype("Float64")


def age_band(age: pd.Series) -> pd.Series:
    """Bucket age into the bands defined in the brief.

    Out-of-range ages get explicit labels so QA can spot them:
      - <18  → 'Under 18'   (data error or business policy violation)
      - >100 → 'Over 100'   (likely DOB error)
      - NaN  → 'Unknown'    (no DOB on file)
    """
    out = pd.Series(["Unknown"] * len(age), index=age.index, dtype="string")
    for lo, hi, label in AGE_BANDS:
        mask = age.between(lo, hi, inclusive="both")
        out.loc[mask] = label
    out.loc[age < 18] = "Under 18"
    out.loc[age > 100] = "Over 100"
    return out


# 2. Income band — applied to dim_customer

INCOME_BANDS = [
    (0,            4_999.99,  "Below 5K"),
    (5_000,        9_999.99,  "5K-10K"),
    (10_000,       19_999.99, "10K-20K"),
    (20_000,       29_999.99, "20K-30K"),
    (30_000,       49_999.99, "30K-50K"),
    (50_000,       99_999.99, "50K-100K"),
    (100_000,      149_999.99,"100K-150K"),
    (150_000, float("inf"),   "150K+"),
]


def compute_avg_monthly_income(received_total: pd.Series, duration_months: pd.Series) -> pd.Series:
    """
    Avg monthly income = received_total / duration_months.

    Source columns 'Persons Received From Total', 'Banks Received', and
    'Paybills Received Others' appear to be channel sub-totals of `Received`,
    so summing them double-counts. We use `Received` as the canonical total.
    Documented as a data-gap risk in the report.
    """
    duration = duration_months.where(duration_months > 0)
    return (received_total / duration).astype("Float64")


def income_band(monthly: pd.Series) -> pd.Series:
    out = pd.Series(["Unknown"] * len(monthly), index=monthly.index, dtype="string")
    for lo, hi, label in INCOME_BANDS:
        mask = monthly.between(lo, hi, inclusive="both")
        out.loc[mask] = label
    out.loc[monthly < 0] = "Invalid"
    return out


# 3. Days past due — derived independently and validated vs source


def derive_days_past_due(reporting_date: pd.Series, next_invoice_date: pd.Series, arrears: pd.Series) -> pd.Series:
    """
    Per the brief: days between payment due date and reporting date,
    0 if no arrears.

    Logic: if arrears > 0 AND reporting_date > next_invoice_date,
           dpd = (reporting_date - next_invoice_date).days
           else 0.

    Note: the source already provides DAYS_PAST_DUE; we keep both as
    `days_past_due_derived` and `days_past_due_source` and surface the gap as
    a quality check. They will not match exactly because the source likely
    measures from the earliest unpaid invoice rather than the next one.
    """
    delta = (reporting_date - next_invoice_date).dt.days
    derived = np.where((arrears > 0) & (delta > 0), delta, 0)
    return pd.Series(derived, index=reporting_date.index).astype("Int64")


# 4. Risk category — Low / Medium / High / Critical (+ Returned, Closed)

"""
Risk category logic
-------------------
Combines ACCOUNT_STATUS_L2 (the bank's own bucket), days_past_due, and arrears.

  Closed      → ACCOUNT_STATUS_L2 in {Paid Off}
                or ACCOUNT_STATUS_L1 in {Cancelled..., Return}
                — out of active book
  Returned    → ACCOUNT_STATUS_L2 = 'Return'
  Critical    → write-off OR DPD ≥ 90    (irrecoverable / loss-imminent)
  High        → DPD 31-89  OR L2 in {PAR 30, FMD}
  Medium      → DPD  1-30  OR L2 in {PAR 7, FPD, Inactive}
  Low         → DPD = 0 AND L2 in {Active}

This mirrors standard credit risk practice (PAR-buckets / IFRS 9 staging).
"""
WRITE_OFF_L1 = {"Write Off", "Lost Write Off"}
RETURN_L1_TOKENS = ("Cancelled Returned", "First 2 days Return", "Return")


def derive_risk_category(l1: pd.Series, l2: pd.Series, dpd: pd.Series, arrears: pd.Series) -> pd.Series:
    """Vectorised risk classifier."""
    out = pd.Series(["Unclassified"] * len(l1), index=l1.index, dtype="string")

    is_write_off = l1.isin(WRITE_OFF_L1)
    is_return = l2.eq("Return") | l1.fillna("").apply(
        lambda s: any(s.startswith(t) for t in RETURN_L1_TOKENS)
    )
    is_paid_off = l2.eq("Paid Off")
    dpd_int = pd.to_numeric(dpd, errors="coerce").fillna(0)

    out.loc[is_paid_off] = "Closed"
    out.loc[is_return]   = "Returned"
    out.loc[is_write_off | (dpd_int >= 90)] = "Critical"
    out.loc[(out == "Unclassified") & ((dpd_int.between(31, 89)) | l2.isin(["PAR 30", "FMD"]))] = "High"
    out.loc[(out == "Unclassified") & ((dpd_int.between(1, 30)) | l2.isin(["PAR 7", "FPD", "Inactive"]))] = "Medium"
    out.loc[(out == "Unclassified") & (dpd_int == 0) & (l2 == "Active")] = "Low"
    return out


# Driver

def build_dim_customer() -> pd.DataFrame:
    cust = pd.read_parquet(WAREHOUSE / "stg_customer.parquet")

    # Income bands (constant per loan — independent of reporting date)
    cust["avg_monthly_income"] = compute_avg_monthly_income(
        cust["received_total"], cust["duration_months"]
    )
    cust["avg_monthly_income_band"] = income_band(cust["avg_monthly_income"])

    log.info(f"dim_customer built: {len(cust)} rows")
    log.info(f"  income band counts:\n{cust['avg_monthly_income_band'].value_counts(dropna=False).to_string()}")
    return cust


def build_fct_credit() -> pd.DataFrame:
    files = sorted(glob.glob(str(WAREHOUSE / "stg_credit_snapshot" / "snapshot_date=*" / "data.parquet")))
    parts = [pd.read_parquet(f) for f in files]
    fct = pd.concat(parts, ignore_index=True)

    # Bring DOB into the fact for age_band (which depends on reporting_date)
    cust = pd.read_parquet(WAREHOUSE / "stg_customer.parquet")[["loan_id", "dob"]]
    fct = fct.merge(cust, on="loan_id", how="left")

    # Derived features
    fct["age_at_report"] = compute_age(fct["dob"], fct["reporting_date"])
    fct["age_band"] = age_band(fct["age_at_report"])

    fct["days_past_due_derived"] = derive_days_past_due(
        fct["reporting_date"], fct["next_invoice_date"], fct["arrears"]
    )

    fct["risk_category"] = derive_risk_category(
        fct["account_status_l1"], fct["account_status_l2"],
        fct["days_past_due"], fct["arrears"],
    )

    log.info(f"fct_credit_snapshot built: {len(fct)} rows across {fct['snapshot_date'].nunique()} snapshots")
    log.info(f"  age band counts:\n{fct['age_band'].value_counts(dropna=False).to_string()}")
    log.info(f"  risk category counts:\n{fct['risk_category'].value_counts(dropna=False).to_string()}")
    return fct


def run() -> None:
    dim = build_dim_customer()
    dim.to_parquet(WAREHOUSE / "dim_customer.parquet", index=False)
    log.info(f"wrote dim_customer.parquet")

    fct = build_fct_credit()
    out_dir = WAREHOUSE / "fct_credit_snapshot"
    for sd, part in fct.groupby("snapshot_date", sort=False):
        d = out_dir / f"snapshot_date={sd.date()}"
        d.mkdir(parents=True, exist_ok=True)
        part.to_parquet(d / "data.parquet", index=False)
    log.info(f"wrote {fct['snapshot_date'].nunique()} fct_credit_snapshot partitions")


if __name__ == "__main__":
    run()
    print("\n✔ Feature engineering complete")
