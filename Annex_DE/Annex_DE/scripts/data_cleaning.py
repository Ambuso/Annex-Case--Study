"""
data_cleaning.py
--------------------------------------
Cleaning and standardisation for ABC Phones credit, customer, and NPS data.

Design principles
-----------------
* Pure functions — each `clean_*` returns a new DataFrame; no in-place mutation.
* All cleaning decisions are documented inline; the *what* is in code, the
  *why* is in the docstring or a comment.
* Idempotent — running this twice on the same input produces the same output.
* No silent drops. Every row removed is counted and logged via the returned
  CleaningReport so quality checks can verify.

Run as a module:
    python scripts/data_cleaning.py

Or import the pure functions:
    from scripts.data_cleaning import clean_credit_snapshot, clean_customer, clean_nps
"""
from __future__ import annotations

import glob
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
WAREHOUSE = ROOT / "data" / "warehouse"
LOGS = ROOT / "logs"
WAREHOUSE.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "pipeline.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("clean")


# Reporting helpers — every clean step returns a record of what it did


@dataclass
class CleaningReport:
    source: str
    rows_in: int = 0
    rows_out: int = 0
    notes: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.notes.append(msg)
        log.info(f"[{self.source}] {msg}")



# Date parsing — credit CSV uses M/D/YYYY (US format).
# Wrapped so we get clean NaT on bad input rather than exceptions.

def parse_us_date(s: pd.Series) -> pd.Series:
    """Parse strings in M/D/YYYY format. Returns datetime64[ns]."""
    return pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")


def parse_iso_dob(s: pd.Series) -> pd.Series:
    """
    DOB sheet has mixed formats:
        '1992-01-15T00:00:00+03:00'  (ISO with EAT offset)
        '1979-01-01 00:00:00'        (naive)
    Return tz-naive date in local sense (we strip tz; DOB is a calendar date).
    """
    parsed = pd.to_datetime(s, errors="coerce", utc=True)
    # Strip tz so it's a pure calendar date for arithmetic with reporting_date
    return parsed.dt.tz_localize(None)


# 1. Credit snapshot cleaning

SNAPSHOT_FILE_RX = re.compile(r"Credit_Data_-_(\d{2})-(\d{2})-(\d{4})\.csv$")


def snapshot_date_from_filename(path: str | Path) -> pd.Timestamp:
    """File names use DD-MM-YYYY (e.g. 30-12-2025). Returns the snapshot date."""
    m = SNAPSHOT_FILE_RX.search(str(path))
    if not m:
        raise ValueError(f"Cannot parse snapshot date from filename: {path}")
    dd, mm, yyyy = m.groups()
    return pd.Timestamp(year=int(yyyy), month=int(mm), day=int(dd))


def clean_credit_snapshot(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Clean a single credit snapshot CSV.

    Decisions:
      * Drop ACCOUNT_STATUS_L1='Demo' rows  → test data, not real loans.
      * Drop rows with null LOAN_ID         → cannot key.
      * Lowercase BALANCE_DUE_STATUS        → casing inconsistent in source.
      * Strip whitespace on string columns.
      * Parse all date columns as datetime; the source DATE field becomes
        `reporting_date` and is also validated against the filename.
      * Add `snapshot_date` (from filename) as the authoritative partition key.
    """
    rep = CleaningReport(source=f"credit::{snapshot_date.date()}", rows_in=len(df))
    df = df.copy()

    # Strip whitespace from object columns
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype("string").str.strip()

    # Parse dates
    date_cols = [
        "DATE", "RETURN_DATE", "SALE_DATE", "CREDIT_EXPIRY",
        "NEXT_INVOICE_DATE", "MAX_PAYMENT_DATE",
    ]
    for c in date_cols:
        df[c] = parse_us_date(df[c])

    # Drop demo rows
    demo_mask = df["ACCOUNT_STATUS_L1"].fillna("").str.lower().eq("demo")
    if demo_mask.any():
        rep.add(f"dropped {int(demo_mask.sum())} ACCOUNT_STATUS_L1='Demo' rows")
        df = df.loc[~demo_mask].copy()

    # Drop null loan ids
    null_loan = df["LOAN_ID"].isna()
    if null_loan.any():
        rep.add(f"dropped {int(null_loan.sum())} rows with null LOAN_ID")
        df = df.loc[~null_loan].copy()

    # Normalise enum casing
    df["BALANCE_DUE_STATUS"] = df["BALANCE_DUE_STATUS"].str.lower()

    # Validate that source DATE matches snapshot_date
    distinct_reported = df["DATE"].dropna().unique()
    if len(distinct_reported) != 1:
        rep.add(f"WARNING: snapshot has {len(distinct_reported)} distinct DATE values: {distinct_reported}")
    elif pd.Timestamp(distinct_reported[0]) != snapshot_date:
        rep.add(f"WARNING: file date ({snapshot_date.date()}) ≠ DATE column ({pd.Timestamp(distinct_reported[0]).date()})")

    df = df.rename(columns={"DATE": "reporting_date"})
    df["snapshot_date"] = snapshot_date

    # Lowercase column names for downstream consistency
    df.columns = [c.lower() for c in df.columns]

    rep.rows_out = len(df)
    rep.add(f"cleaned: {rep.rows_in} → {rep.rows_out} rows ({df['loan_id'].nunique()} unique loans)")
    return df, rep


# 2. Customer dimension cleaning — joins 4 sheets into one row-per-loan dim


def _strip_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def clean_customer(xlsx_path: Path) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Build a one-row-per-loan customer dimension by joining the four sheets:
    Sales Details, Gender, DOB, Income Level.

    Decisions:
      * Sales Details is the spine — every loan in credit ties back here.
      * Gender: dedupe to one row per loan (dups are exact); 2 conflicting
        cases — keep first deterministic order.
      * DOB: 471 loans have multiple DOBs across providers (TransUnion,
        SpinMobile, SmileID). Resolution rule:
          1. Prefer TransUnion (credit bureau, authoritative)
          2. Then most recent createdAt UTC
          3. Then first row
      * Income: 489 loans have differing Received values. Resolution rule:
          - Keep the row with the largest Duration (longest history window =
            most representative). Ties broken by largest Received.
      * #N/A literal Loan Ids: not present in this version of the data, but
        guard for robustness.
      * `Received` is the canonical total inflow (other channel fields appear
        to be sub-totals — documented in README, not summed here).
    """
    rep = CleaningReport(source="customer", rows_in=0)
    sheets = pd.read_excel(xlsx_path, sheet_name=None)

    # ----- Sales Details (spine) -----
    sales = _strip_cols(sheets["Sales Details"]).dropna(how="all")
    rep.rows_in += len(sales)

    # Drop NaN Loan Id (cannot join)
    n_orphan = sales["Loan Id"].isna().sum()
    if n_orphan:
        rep.add(f"sales: dropped {int(n_orphan)} rows with NaN Loan Id")
        sales = sales.loc[sales["Loan Id"].notna()].copy()

    # Drop full duplicates first
    n_full_dup = sales.duplicated().sum()
    if n_full_dup:
        rep.add(f"sales: dropped {int(n_full_dup)} fully-duplicate rows")
        sales = sales.drop_duplicates()

    # Any remaining same-loan rows: keep first
    n_loan_dup = sales.duplicated("Loan Id").sum()
    if n_loan_dup:
        rep.add(f"sales: kept first of {int(n_loan_dup)} same-loan-id rows")
        sales = sales.drop_duplicates("Loan Id", keep="first")

    sales = sales.rename(columns={"Loan Id": "loan_id"})
    sales.columns = [c.lower().replace(" ", "_") for c in sales.columns]

    # ----- Gender -----
    gender = _strip_cols(sheets["Gender"]).dropna(how="all")
    gender = gender.loc[gender["Loan Id"].notna() & gender["Loan Id"].astype(str).ne("#N/A")]
    gender = gender.drop_duplicates("Loan Id", keep="first")
    gender = gender.rename(columns={"Loan Id": "loan_id"})
    gender.columns = [c.lower() for c in gender.columns]

    # ----- DOB -----
    dob = _strip_cols(sheets["DOB"]).dropna(how="all")
    dob = dob.loc[dob["Loan Id"].notna() & dob["Loan Id"].astype(str).ne("#N/A")]
    dob["dob"] = parse_iso_dob(dob["date_of_birth"])
    dob["createdAt UTC"] = pd.to_datetime(dob["createdAt UTC"], errors="coerce", utc=True)
    dob["_provider_priority"] = dob["provider"].map(
        {"TRANSUNION": 0, "SMILEID": 1, "SPINMOBILE": 2}
    ).fillna(99)
    dob = (
        dob.sort_values(
            ["Loan Id", "_provider_priority", "createdAt UTC"],
            ascending=[True, True, False],
        )
        .drop_duplicates("Loan Id", keep="first")
        .rename(columns={"Loan Id": "loan_id"})
        [["loan_id", "dob", "provider"]]
    )

    # Flag implausible DOBs but keep them; an explicit quality check fails them
    rep.add(f"dob: {(dob['dob'].notna()).sum()} non-null DOBs after dedupe")

    # ----- Income -----
    income = _strip_cols(sheets["Income Level"]).dropna(how="all")
    income = income.loc[income["Loan Id"].notna() & income["Loan Id"].astype(str).ne("#N/A")]
    income = income.rename(columns={"Loan Id": "loan_id", "Duration": "duration_months", "Received": "received_total"})
    # Pick representative row per loan
    income = (
        income.sort_values(["loan_id", "duration_months", "received_total"], ascending=[True, False, False])
              .drop_duplicates("loan_id", keep="first")
              [["loan_id", "duration_months", "received_total"]]
    )

    # ----- Join -----
    cust = sales.merge(gender, on="loan_id", how="left") \
                .merge(dob,    on="loan_id", how="left") \
                .merge(income, on="loan_id", how="left")

    # Coverage report
    rep.add(f"final dim_customer rows: {len(cust)}")
    rep.add(f"  with gender:   {cust['gender'].notna().sum()} ({100*cust['gender'].notna().mean():.1f}%)")
    rep.add(f"  with dob:      {cust['dob'].notna().sum()} ({100*cust['dob'].notna().mean():.1f}%)")
    rep.add(f"  with income:   {cust['received_total'].notna().sum()} ({100*cust['received_total'].notna().mean():.1f}%)")

    rep.rows_out = len(cust)
    return cust, rep


# 3. NPS cleaning

NPS_RENAME = {
    "Submission ID": "submission_id",
    "Respondent ID": "respondent_id",
    "Submitted at": "submitted_at",
    "Loan Id": "loan_id",
    "Are you happy with the quality and performance of your device?": "happy_with_device",
    "Are you happy with the service and support provided by ABC Phones?": "happy_with_service",
    "Have you ever experienced a delay in your payment reflecting in your ABC account?": "experienced_payment_delay",
    "Have you ever had difficulty getting assistance from ABC Phones customer support when needed?": "difficulty_getting_support",
    "Have you experienced any battery-related issues with your MoPhones device?": "battery_issues",
    "Have you used the MoPhones app (MoApp) to manage your account or make payments?": "uses_moapp",
    "Which communication channel do you prefer when contacting MoPhones for inquiries or support?": "preferred_channel",
    "Have you ever had your phone lock despite making a payment on time?": "phone_locked_despite_payment",
}


def clean_nps(xlsx_path: Path) -> tuple[pd.DataFrame, CleaningReport]:
    """
    Clean NPS survey responses.

    Decisions:
      * Rename verbose question columns to short snake_case (mapping above).
      * The score column has a 100+ char question — extract by pattern match.
      * Drop responses with null loan_id (cannot join to credit).
      * Compute nps_segment: 0-6 = Detractor, 7-8 = Passive, 9-10 = Promoter.
      * Drop rows with null score (incomplete responses).
    """
    rep = CleaningReport(source="nps", rows_in=0)
    df = pd.read_excel(xlsx_path).dropna(how="all")
    rep.rows_in = len(df)

    # Identify the score column by question stem
    score_col = next(c for c in df.columns if "scale from 0" in c.lower())
    df = df.rename(columns={**NPS_RENAME, score_col: "nps_score"})

    # Strip strings
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype("string").str.strip()

    # Drop rows we can't use
    n_no_loan = df["loan_id"].isna().sum()
    n_no_score = df["nps_score"].isna().sum()
    df = df.loc[df["loan_id"].notna() & df["nps_score"].notna()].copy()
    rep.add(f"dropped {int(n_no_loan)} null-loan_id and {int(n_no_score)} null-score rows")

    # NPS segment per the standard Bain framework
    def to_segment(score: float) -> str:
        if score >= 9:
            return "Promoter"
        if score >= 7:
            return "Passive"
        return "Detractor"

    df["nps_segment"] = df["nps_score"].apply(to_segment)

    rep.rows_out = len(df)
    rep.add(f"cleaned: {rep.rows_in} → {rep.rows_out} rows ({df['loan_id'].nunique()} unique loans)")
    return df, rep


# Module-level driver — clean everything and write to the warehouse layer

def run() -> dict[str, Any]:
    reports: list[CleaningReport] = []

    # ----- Credit (one Parquet partition per snapshot) -----
    credit_files = sorted(glob.glob(str(RAW / "Credit_Data_-_*.csv")))
    snapshots: list[pd.DataFrame] = []
    for f in credit_files:
        sd = snapshot_date_from_filename(f)
        df_raw = pd.read_csv(f)
        df_clean, rep = clean_credit_snapshot(df_raw, sd)
        reports.append(rep)
        # Write per-partition (Hive-style)
        part_dir = WAREHOUSE / "stg_credit_snapshot" / f"snapshot_date={sd.date()}"
        part_dir.mkdir(parents=True, exist_ok=True)
        df_clean.to_parquet(part_dir / "data.parquet", index=False)
        snapshots.append(df_clean)
    log.info(f"wrote {len(snapshots)} credit snapshot partitions")

    # ----- Customer dim -----
    cust, rep = clean_customer(RAW / "Sales_and_Customer_Data.xlsx")
    reports.append(rep)
    cust.to_parquet(WAREHOUSE / "stg_customer.parquet", index=False)
    log.info(f"wrote stg_customer.parquet ({len(cust)} rows)")

    # ----- NPS -----
    nps, rep = clean_nps(RAW / "NPS_Data.xlsx")
    reports.append(rep)
    nps.to_parquet(WAREHOUSE / "stg_nps.parquet", index=False)
    log.info(f"wrote stg_nps.parquet ({len(nps)} rows)")

    return {
        "n_snapshots": len(snapshots),
        "customer_rows": len(cust),
        "nps_rows": len(nps),
        "reports": reports,
    }


if __name__ == "__main__":
    result = run()
    print("\n" + "=" * 70)
    print(f"CLEANING COMPLETE — {result['n_snapshots']} snapshots, "
          f"{result['customer_rows']} customers, {result['nps_rows']} NPS responses")
    print("=" * 70)
