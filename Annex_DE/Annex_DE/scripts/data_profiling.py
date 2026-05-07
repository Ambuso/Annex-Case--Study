"""
data_profiling.py
------------------------------------
Comprehensive profiling of all three source datasets for the ABC Phones
credit portfolio case study.

Outputs:
  - outputs/data_quality_report.md   (human-readable findings)
  - outputs/profile_credit.csv        (per-column stats per snapshot)
  - outputs/profile_customer.csv      (per-sheet per-column stats)
  - outputs/profile_nps.csv

Run:
    python scripts/data_profiling.py
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

# helpers

def column_profile(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Return a per-column profile: dtype, null %, n_unique, sample value."""
    rows: list[dict[str, Any]] = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        nulls = s.isna().sum()
        rows.append(
            {
                "source": source,
                "column": col,
                "dtype": str(s.dtype),
                "rows": n,
                "n_null": int(nulls),
                "pct_null": round(100 * nulls / n, 2) if n else 0.0,
                "n_unique": int(s.nunique(dropna=True)),
                "sample": str(s.dropna().iloc[0]) if s.notna().any() else None,
            }
        )
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame) -> str:
    """Tiny markdown-table renderer that doesn't need tabulate."""
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join(
        "| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |"
        for row in df.itertuples(index=False, name=None)
    )
    return "\n".join([head, sep, body])


# 1. Credit data — multiple CSV snapshots

print("=" * 70)
print("CREDIT DATA")
print("=" * 70)

credit_files = sorted(glob.glob(str(RAW / "Credit_Data_-_*.csv")))
credit_profiles = []
credit_snapshots: dict[str, pd.DataFrame] = {}
for f in credit_files:
    snap = os.path.basename(f).replace("Credit_Data_-_", "").replace(".csv", "")
    df = pd.read_csv(f)
    credit_snapshots[snap] = df
    print(f"\n[{snap}]  rows={len(df):,}  cols={df.shape[1]}")
    credit_profiles.append(column_profile(df, source=f"credit::{snap}"))

credit_profile = pd.concat(credit_profiles, ignore_index=True)
credit_profile.to_csv(OUT / "profile_credit.csv", index=False)

# 2. Customer/Sales — xlsx, multiple sheets

print("\n" + "=" * 70)
print("CUSTOMER DATA")
print("=" * 70)

cust_xlsx = RAW / "Sales_and_Customer_Data.xlsx"
cust_sheets = pd.read_excel(cust_xlsx, sheet_name=None)
customer_profiles = []
for name, df in cust_sheets.items():
    print(f"\n[Sheet: {name}]  rows={len(df):,}  cols={df.shape[1]}")
    customer_profiles.append(column_profile(df, source=f"customer::{name}"))
customer_profile = pd.concat(customer_profiles, ignore_index=True)
customer_profile.to_csv(OUT / "profile_customer.csv", index=False)


# 3. NPS

print("\n" + "=" * 70)
print("NPS DATA")
print("=" * 70)

nps_xlsx = RAW / "NPS_Data.xlsx"
nps_df = pd.read_excel(nps_xlsx)
print(f"rows={len(nps_df):,}  cols={nps_df.shape[1]}")
nps_profile = column_profile(nps_df, source="nps")
nps_profile.to_csv(OUT / "profile_nps.csv", index=False)


# 4. Cross-dataset relationship analysis

print("\n" + "=" * 70)
print("RELATIONSHIPS")
print("=" * 70)

sales = cust_sheets["Sales Details"].copy()
sales.columns = [c.strip() for c in sales.columns]
gender = cust_sheets["Gender"].copy()
gender.columns = [c.strip() for c in gender.columns]
dob = cust_sheets["DOB"].copy()
dob.columns = [c.strip() for c in dob.columns]
income = cust_sheets["Income Level"].copy()
income.columns = [c.strip() for c in income.columns]

# All credit snapshots together for join analysis
all_credit = pd.concat(credit_snapshots.values(), ignore_index=True)

credit_loans = set(all_credit["LOAN_ID"].dropna().unique())
sales_loans = set(sales["Loan Id"].dropna().astype(str).unique())
gender_loans = set(gender["Loan Id"].dropna().astype(str).unique())
dob_loans = set(dob["Loan Id"].dropna().astype(str).unique())
income_loans = set(income["Loan Id"].dropna().astype(str).unique())
nps_loans = set(nps_df["Loan Id"].dropna().astype(str).unique())

rel = {
    "credit_unique_loans": len(credit_loans),
    "sales_unique_loans": len(sales_loans),
    "gender_unique_loans": len(gender_loans),
    "dob_unique_loans": len(dob_loans),
    "income_unique_loans": len(income_loans),
    "nps_unique_loans": len(nps_loans),
    # orphans
    "gender_NA_count": int((gender["Loan Id"].astype(str) == "#N/A").sum()),
    "income_NA_count": int((income["Loan Id"].astype(str) == "#N/A").sum()),
    "dob_NA_count": int((dob["Loan Id"].astype(str) == "#N/A").sum()),
    # coverage of credit loans
    "credit_in_sales_pct": round(100 * len(credit_loans & sales_loans) / max(len(credit_loans), 1), 2),
    "credit_in_gender_pct": round(100 * len(credit_loans & gender_loans) / max(len(credit_loans), 1), 2),
    "credit_in_dob_pct": round(100 * len(credit_loans & dob_loans) / max(len(credit_loans), 1), 2),
    "credit_in_income_pct": round(100 * len(credit_loans & income_loans) / max(len(credit_loans), 1), 2),
    "nps_in_credit_pct": round(100 * len(nps_loans & credit_loans) / max(len(nps_loans), 1), 2),
    # duplicates
    "sales_duplicate_loan_ids": int(sales["Loan Id"].duplicated().sum()),
    "gender_duplicate_loan_ids": int(gender["Loan Id"].duplicated().sum()),
    "dob_duplicate_loan_ids": int(dob["Loan Id"].duplicated().sum()),
    "income_duplicate_loan_ids": int(income["Loan Id"].duplicated().sum()),
}
print(json.dumps(rel, indent=2))

# 5. Data quality findings — concrete anomalies

print("\n" + "=" * 70)
print("ANOMALIES")
print("=" * 70)

# Account status vocabulary
all_l1 = sorted(all_credit["ACCOUNT_STATUS_L1"].dropna().unique().tolist())
all_l2 = sorted(all_credit["ACCOUNT_STATUS_L2"].dropna().unique().tolist())
all_bds = sorted(all_credit["BALANCE_DUE_STATUS"].dropna().unique().tolist())
print(f"ACCOUNT_STATUS_L1 vocab ({len(all_l1)}): {all_l1}")
print(f"ACCOUNT_STATUS_L2 vocab ({len(all_l2)}): {all_l2}")
print(f"BALANCE_DUE_STATUS vocab ({len(all_bds)}): {all_bds}")

# Date format check on the credit DATE col
credit_dates = all_credit["DATE"].dropna().unique()
print(f"\nDistinct DATE values across snapshots: {sorted(credit_dates.tolist())}")

# DPD outliers
print(f"\nDAYS_PAST_DUE summary across all snapshots:")
print(all_credit["DAYS_PAST_DUE"].describe().to_string())

# DOB outliers — implausible birth years
dob_clean = pd.to_datetime(dob["date_of_birth"], errors="coerce", utc=True)
print(f"\nDOB year range: {dob_clean.dt.year.min()}..{dob_clean.dt.year.max()}")
print("DOB year distribution (suspect bins):")
print(dob_clean.dt.year.value_counts(dropna=False).sort_index().head(10).to_string())
print("...")
print(dob_clean.dt.year.value_counts(dropna=False).sort_index().tail(10).to_string())

# Implied ages (assume ref date = max credit DATE)
ref = pd.to_datetime("2025-12-30")
implied_age = ((ref - dob_clean.dt.tz_localize(None)).dt.days / 365.25).dropna()
print(f"\nImplied ages at 2025-12-30: min={implied_age.min():.1f}  max={implied_age.max():.1f}")
print(f"  <18: {(implied_age < 18).sum()}    >=100: {(implied_age >= 100).sum()}")

# Income oddities
print("\nIncome 'Received' summary:")
print(income["Received"].describe().to_string())
print(f"  negative or zero: {(income['Received'] <= 0).sum()}")
print(f"  duration distinct values: {sorted(income['Duration'].dropna().unique().tolist())[:20]}")

# NPS oddities
score_col = [c for c in nps_df.columns if "scale" in c.lower() and "0" in c][0]
print(f"\nNPS score column: '{score_col[:60]}...'")
print(nps_df[score_col].describe().to_string())
print(f"  out-of-range (<0 or >10): {((nps_df[score_col] < 0) | (nps_df[score_col] > 10)).sum()}")

# Inconsistent BALANCE_DUE_STATUS casing
bds_case = all_credit["BALANCE_DUE_STATUS"].value_counts(dropna=False)
print(f"\nBALANCE_DUE_STATUS counts (raw):")
print(bds_case.to_string())


# 6. Write the data_quality_report.md


report_lines: list[str] = []
report_lines.append("# Data Quality Report — ABC Phones Credit Portfolio\n")
report_lines.append("_Generated by `scripts/data_profiling.py`_\n")

report_lines.append("## 1. Dataset summary\n")
summary = pd.DataFrame(
    [
        {"dataset": "credit (5 snapshots)", "rows": sum(len(d) for d in credit_snapshots.values()), "cols": 33},
        {"dataset": "customer · Sales Details", "rows": len(sales), "cols": sales.shape[1]},
        {"dataset": "customer · Gender", "rows": len(gender), "cols": gender.shape[1]},
        {"dataset": "customer · DOB", "rows": len(dob), "cols": dob.shape[1]},
        {"dataset": "customer · Income Level", "rows": len(income), "cols": income.shape[1]},
        {"dataset": "nps", "rows": len(nps_df), "cols": nps_df.shape[1]},
    ]
)
report_lines.append(md_table(summary))
report_lines.append("\n\n## 2. Snapshot row counts (credit)\n")
snap_summary = pd.DataFrame(
    [{"snapshot": k, "rows": len(v), "unique_loans": v["LOAN_ID"].nunique()} for k, v in credit_snapshots.items()]
)
report_lines.append(md_table(snap_summary))

report_lines.append("\n\n## 3. Cross-dataset relationships\n")
rel_df = pd.DataFrame([{"metric": k, "value": v} for k, v in rel.items()])
report_lines.append(md_table(rel_df))

report_lines.append("\n\n## 4. Vocabulary checks\n")
report_lines.append(f"- **ACCOUNT_STATUS_L1** ({len(all_l1)} distinct): {', '.join(all_l1)}\n")
report_lines.append(f"- **ACCOUNT_STATUS_L2** ({len(all_l2)} distinct): {', '.join(all_l2)}\n")
report_lines.append(f"- **BALANCE_DUE_STATUS** ({len(all_bds)} distinct, note casing): {', '.join(all_bds)}\n")

report_lines.append("\n## 5. Key issues detected\n")
issues = [
    "**No CUSTOMER_ID exists** — joins are loan-to-loan via `LOAN_ID` / `Loan Id`. Multi-loan customers are not identifiable in source.",
    "**Column name inconsistency** — `Loan Id` (Sales Details, Gender, Income Level) vs `Loan Id ` (DOB sheet, trailing space). Strip whitespace on ingest.",
    "**Literal `#N/A` strings as Loan Id** — Gender, Income Level, DOB sheets contain orphan rows that cannot be joined. Quarantine and exclude from joins.",
    "**Date formats vary** — credit `DATE` is `M/D/YYYY` text; DOB is ISO with `+03:00` offset; NPS `Submitted at` is true datetime. Standardise to `DATE` (date) on ingest.",
    "**Inconsistent enum casing** — `BALANCE_DUE_STATUS` has `'Arrears'`, `'up to date'`, `'advance'`. Normalise to lowercase.",
    "**Income columns are ambiguous** — `Received`, `Persons Received From Total`, `Banks Received`, `Paybills Received Others` likely overlap (sub-channel breakdowns of total inflow). Naive sum will double-count. Pick `Received` as the canonical total OR sum the channel breakdown excluding `Received`. Document which.",
    "**`Duration` field unit not explicit** — values like `12` could be months or weeks. We assume **months** based on context (matches LOAN_TERM '12M').",
    "**ACCOUNT_STATUS_L1 has long-tail values** — e.g. `Inactive 01-07`, `Inactive 08-30`, `Inactive 31+` — appear to encode DPD-buckets within Inactive. Decide whether to roll up to L2.",
    "**Snapshot dates are quarter-ends except 2025-01-01** — first snapshot is start-of-year, others are 30/03, 30/06, 30/09, 30/12. Cadence is quarterly with one origin point.",
    "**LOAN_IDs are Airtable record IDs** (`rec...` prefix). Treat as opaque strings, no semantic meaning, but stable as PKs.",
]
for i, item in enumerate(issues, 1):
    report_lines.append(f"{i}. {item}")

(OUT / "data_quality_report.md").write_text("\n".join(report_lines) + "\n")
print(f"\n✔ Wrote {OUT / 'data_quality_report.md'}")
print(f"✔ Wrote {OUT / 'profile_credit.csv'}")
print(f"✔ Wrote {OUT / 'profile_customer.csv'}")
print(f"✔ Wrote {OUT / 'profile_nps.csv'}")
