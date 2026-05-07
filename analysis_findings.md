# Portfolio Analysis — Findings
## 3A. Portfolio health
Across the 5 snapshots from 2025-01-01 to 2025-12-30, the active book grew from **8,812 → 20,501 loans**, with outstanding balance moving from KES 335.5M to KES 654.9M.
**Headline KPIs (latest snapshot):**
- Delinquency rate: **44.8%**
- 90+ DPD rate (PAR 90): **33.0%**
- Write-off rate: **18.2%**
- Active-loan collection rate: **59.5%**
- Paid-off rate (cumulative): **26.1%**

**Segment with materially different risk behaviour (latest snapshot):**
- age_band = **46-55** (556 loans): delinquency 32.4% (-12.4% vs portfolio avg 44.8%)
- age_band = **36-45** (1,986 loans): delinquency 35.8% (-9.0% vs portfolio avg 44.8%)
- income_band = **150K+** (1,634 loans): delinquency 36.0% (-8.8% vs portfolio avg 44.8%)

## 3B. Credit × NPS
Each NPS response was joined to the customer's most recent credit snapshot.

| Risk category | n | Mean NPS | Net Promoter Score | % locked-after-paying |
|---|---|---|---|---|
| Low | 1748 | 7.14 | 11.3 | 12.1% |
| Closed | 821 | 7.12 | 13.4 | 16.9% |
| High | 260 | 7.12 | 17.7 | 15.0% |
| Medium | 444 | 7.01 | 10.4 | 16.4% |
| Returned | 37 | 6.11 | -8.1 | 5.4% |
| Critical | 675 | 5.18 | -23.7 | 14.5% |

**Recommendation:** Investigate and fix the lock-after-payment issue. The NPS data shows that customers reporting 'phone locked despite paying on time' skew strongly toward Detractor scores AND tend to fall into worse risk buckets — a feedback loop where a payment-reflection bug drives both customer dissatisfaction and avoidable arrears flags. A 24-hour grace window before remote-locking, plus a reconciliation job that lifts locks within 1 hour of payment confirmation, would improve NPS and reduce 'fake' delinquency simultaneously — a rare win-win in collections design.

## 3C. Data gaps & improvements
**Missing:**
- No CUSTOMER_ID — multi-loan customers cannot be tracked.
- ~50% of credit loans have no DOB / Gender / Income on file.
- No location data (county, region) for geographic risk slicing.
- No transaction-level payment ledger; only point-in-time snapshots.

**Inconsistent:**
- Date formats: filename DD-MM-YYYY vs cell M/D/YYYY vs ISO+offset (DOB).
- Account status: L1 has 20 long-tail values that overlap L2 buckets.
- Income channel columns appear to be sub-totals of `Received` (double-counting risk if naively summed).

**Ambiguous:**
- `Duration` field is unit-less (assumed months from context).
- `CUSTOMER_AGE` in credit data is days-since-sale, not human age — confusing name.
- `account_status_l1='Inactive 01-07'` etc. encode DPD-buckets inside status, duplicating information already in DAYS_PAST_DUE.

**Improvements:**
1. Introduce a `customer_id` natural key (NRIC or hashed phone) to the customer master, then propagate it to credit and NPS at ingestion. Unlocks lifetime-value analysis and repeat-borrower risk modelling.
2. Standardise on ISO-8601 dates everywhere and document the unit of every numeric column in a YAML schema spec versioned alongside the data.
3. Replace daily snapshots with an event-stream (payment_made, status_changed, arrears_updated) — derive snapshots downstream. This removes the filename/internal-date drift class of bugs entirely.
