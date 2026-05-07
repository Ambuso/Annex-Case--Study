/**
 * build_deck.js
 * =============
 * Builds the 10-slide submission deck for the Annex DE case study.
 *
 *   node build_deck.js
 *
 * Output: slides/Annex_DE_Presentation.pptx
 *
 * Palette (fintech / credit-risk credible):
 *   navy     #1B2845   primary dark, titles, key numbers
 *   navy_lt  #2D4D72   subordinate dark
 *   terra    #C8553D   accent, risk indicators
 *   teal     #0F766E   positive signals
 *   slate    #64748B   muted body text
 *   stone    #E5E7EB   dividers
 *   cream    #FFFFFF   default bg (white per skill guidance)
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const OUT = path.join(ROOT, "slides", "Annex_DE_Presentation.pptx");
const ARCH_PNG = path.join(ROOT, "pipeline_design", "architecture.png");

const C = {
  navy: "1B2845",
  navyLt: "2D4D72",
  terra: "C8553D",
  teal: "0F766E",
  slate: "64748B",
  stone: "E5E7EB",
  white: "FFFFFF",
  paper: "F8FAFC",
};

const FONT_HEAD = "Calibri";
const FONT_BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";   // 13.3 × 7.5 in
pres.author = "Annex DE Case Study";
pres.title = "ABC Phones Credit Portfolio";

// -------- helpers --------
function addPageHeader(slide, title, subtitle) {
  slide.background = { color: C.white };
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 12.3, h: 0.55,
    fontFace: FONT_HEAD, fontSize: 26, bold: true, color: C.navy, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.5, y: 0.85, w: 12.3, h: 0.3,
      fontFace: FONT_BODY, fontSize: 12, color: C.slate, margin: 0,
    });
  }
  slide.addText("Annex DE Case Study  ·  ABC Phones Credit Portfolio", {
    x: 0.5, y: 7.05, w: 12.3, h: 0.3,
    fontFace: FONT_BODY, fontSize: 9, color: C.slate, italic: true, align: "left", margin: 0,
  });
}

function statCallout(slide, x, y, w, h, value, label, color = C.navy) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: C.paper }, line: { color: C.stone, width: 0.75 },
  });
  slide.addText(value, {
    x: x + 0.15, y: y + 0.15, w: w - 0.3, h: h * 0.55,
    fontFace: FONT_HEAD, fontSize: 32, bold: true, color, valign: "middle", margin: 0,
  });
  slide.addText(label, {
    x: x + 0.15, y: y + h * 0.62, w: w - 0.3, h: h * 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.slate, valign: "top", margin: 0,
  });
}

// =================================================================
// SLIDE 1 — Title + executive summary
// =================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addText("ABC Phones", {
    x: 0.7, y: 1.2, w: 12, h: 0.7,
    fontFace: FONT_HEAD, fontSize: 22, color: C.terra, bold: true, charSpacing: 4, margin: 0,
  });
  s.addText("Credit Portfolio:\nFrom Raw Snapshots to Reliable Insights", {
    x: 0.7, y: 1.95, w: 12, h: 1.7,
    fontFace: FONT_HEAD, fontSize: 40, color: C.white, bold: true, margin: 0,
  });

  // three executive findings
  const findings = [
    { k: "133%", v: "Loan-book growth across 2025 (8.8K → 20.5K loans)\nbut credit quality deteriorating" },
    { k: "44.8%", v: "Latest delinquency rate — collection rate fell\n10pp from Q1 to Q4 (69 → 60%)" },
    { k: "+5pp", v: "Default-rate gap for loans without complete\ncustomer profiles vs the rest of the book" },
  ];
  findings.forEach((f, i) => {
    const x = 0.7 + i * 4.1;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.3, w: 3.9, h: 1.9, fill: { color: C.navyLt }, line: { type: "none" },
    });
    s.addText(f.k, {
      x: x + 0.2, y: 4.4, w: 3.5, h: 0.7,
      fontFace: FONT_HEAD, fontSize: 30, bold: true, color: C.terra, margin: 0,
    });
    s.addText(f.v, {
      x: x + 0.2, y: 5.15, w: 3.5, h: 1.0,
      fontFace: FONT_BODY, fontSize: 11, color: C.white, margin: 0,
    });
  });

  s.addText("Annex DE Case Study  ·  Slide 1 of 10", {
    x: 0.7, y: 6.85, w: 12, h: 0.3,
    fontFace: FONT_BODY, fontSize: 9, color: C.stone, italic: true, margin: 0,
  });
}

// =================================================================
// SLIDE 2 — Data overview & quality findings
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "What we found in the data",
                "Three sources, real-world inconsistencies, ~50% customer-side coverage gap");

  // stats row
  statCallout(s, 0.5, 1.4, 2.9, 1.3, "71,448", "credit rows across 5 quarterly snapshots");
  statCallout(s, 3.55, 1.4, 2.9, 1.3, "20,742", "unique loans (1 row per loan per snapshot)");
  statCallout(s, 6.6, 1.4, 2.9, 1.3, "3,985", "NPS responses, 100% match credit");
  statCallout(s, 9.65, 1.4, 3.15, 1.3, "~50%", "credit loans w/ no DOB/income/gender", C.terra);

  // issues table
  s.addText("Top quality issues identified", {
    x: 0.5, y: 2.95, w: 12.3, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });

  const issues = [
    [
      { text: "Issue", options: { bold: true, color: C.white, fill: { color: C.navy } } },
      { text: "Detail", options: { bold: true, color: C.white, fill: { color: C.navy } } },
      { text: "Resolution", options: { bold: true, color: C.white, fill: { color: C.navy } } },
    ],
    ["Filename ↔ data drift", "Credit_Data_-_30-03-2025.csv contains DATE = 3/31/2025", "Caught by schema_and_freshness check (CRITICAL)"],
    ["No CUSTOMER_ID anywhere", "Joins are loan-to-loan only via LOAN_ID / Loan Id", "Documented gap; multi-loan customers not trackable"],
    ["Column-name typo", "DOB sheet uses 'Loan Id ' (trailing space)", "Stripped on ingest"],
    ["DOB conflicts", "471 loans have multiple DOBs across 3 providers", "Resolution rule: TransUnion → SmileID → SpinMobile, then most recent createdAt"],
    ["Income column ambiguity", "4 income fields likely overlap — naive sum double-counts", "Use 'Received' as canonical total; documented"],
    ["Excel padding", "All customer sheets padded to 1,048,575 rows (Excel cap)", "dropna(how='all') on ingest"],
    ["Inconsistent enum casing", "BALANCE_DUE_STATUS: 'Arrears' vs 'up to date' vs 'advance'", "Lowercased on ingest"],
  ];

  s.addTable(issues, {
    x: 0.5, y: 3.45, w: 12.3, h: 3.3,
    colW: [3.0, 5.5, 3.8],
    fontSize: 11, fontFace: FONT_BODY, color: C.navy,
    border: { type: "solid", pt: 0.5, color: C.stone },
    rowH: [0.35, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42],
  });
}

// =================================================================
// SLIDE 3 — Architecture diagram
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "ETL architecture",
                "Lakehouse pattern on a laptop today, lifts to S3+Athena / GCS+BigQuery / Snowflake tomorrow with no SQL rewrites");

  // The diagram is 1280×720 (16:9). Fit to ~12.3" wide max.
  const w = 12.3;
  const h = w * (720/1280);   // 6.92"
  s.addImage({
    path: ARCH_PNG, x: 0.5, y: 1.25, w, h,
  });
}

// =================================================================
// SLIDE 4 — Key engineering decisions
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Key engineering decisions",
                "Each call is small but compounds into a robust pipeline");

  const decisions = [
    {
      title: "Hive partitioning by snapshot_date",
      body: "Each snapshot is its own Parquet partition. Reruns drop & replace one folder; the rest stays untouched. Idempotent without locking.",
    },
    {
      title: "DuckDB over Pandas-only",
      body: "Cleaning stays in Pandas (row-wise logic). Analytics moves to SQL via DuckDB on the Parquet files. Same SQL ports to BigQuery/Snowflake.",
    },
    {
      title: "Pure-function stages",
      body: "Every clean_* and check_* function returns (df, report). No globals, no in-place mutation. Trivially unit-testable.",
    },
    {
      title: "Source values preserved alongside derived",
      body: "We keep both days_past_due (source) and days_past_due_derived (ours). The reconciliation gap itself is a quality check — not a bug to hide.",
    },
    {
      title: "Schema contract on ingest",
      body: "Expected columns are codified in EXPECTED_CREDIT_COLS. Missing or extra cols halt the pipeline before bad data reaches analysts.",
    },
    {
      title: "Late-arriving / reprocessing strategy",
      body: "Replay any snapshot independently — `python run_pipeline.py --only cleaning` rebuilds one partition. Nothing else recomputes.",
    },
  ];

  decisions.forEach((d, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 6.2;
    const y = 1.4 + row * 1.85;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 5.9, h: 1.65, fill: { color: C.paper }, line: { color: C.stone, width: 0.75 },
    });
    // Accent stripe (left edge, RECTANGLE not ROUNDED_RECTANGLE per skill guidance)
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.08, h: 1.65, fill: { color: C.terra }, line: { type: "none" },
    });
    s.addText(d.title, {
      x: x + 0.25, y: y + 0.15, w: 5.5, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.navy, margin: 0,
    });
    s.addText(d.body, {
      x: x + 0.25, y: y + 0.55, w: 5.5, h: 1.05,
      fontFace: FONT_BODY, fontSize: 11, color: C.slate, margin: 0,
    });
  });
}

// =================================================================
// SLIDE 5 — Data quality framework
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Data quality framework",
                "Five checks + one bonus, each with severity, cadence, and a real alerting route");

  const headerRow = [
    { text: "Check", options: { bold: true, color: C.white, fill: { color: C.navy } } },
    { text: "Severity", options: { bold: true, color: C.white, fill: { color: C.navy } } },
    { text: "Cadence", options: { bold: true, color: C.white, fill: { color: C.navy } } },
    { text: "Alert route", options: { bold: true, color: C.white, fill: { color: C.navy } } },
  ];
  const rows = [
    ["1. Schema & freshness — files arrive, columns match contract, internal DATE = filename", "CRITICAL", "real-time", "PagerDuty + halt DAG"],
    ["2. Uniqueness of (loan_id, snapshot_date)", "CRITICAL", "daily", "PagerDuty + halt DAG"],
    ["3. Referential integrity — every credit/NPS loan_id exists in dim_customer", "WARNING", "daily", "Slack #data-alerts"],
    ["4. Range checks — age 18-100, income > 0, NPS 0-10, DPD ≥ 0", "WARNING", "daily", "Slack #data-alerts"],
    ["5. Null thresholds — critical fields < 1%, soft fields < 60%", "WARNING", "daily", "Slack #data-alerts"],
    ["+ DPD reconciliation — derived vs source within 7-day tolerance", "INFO", "weekly", "Daily digest email"],
  ];
  s.addTable([headerRow, ...rows], {
    x: 0.5, y: 1.35, w: 12.3,
    colW: [6.7, 1.5, 1.4, 2.7],
    fontSize: 11, fontFace: FONT_BODY, color: C.navy,
    border: { type: "solid", pt: 0.5, color: C.stone },
    rowH: [0.34, 0.5, 0.4, 0.5, 0.45, 0.45, 0.5],
  });

  // worked example
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.85, w: 12.3, h: 1.95, fill: { color: C.paper },
    line: { color: C.terra, width: 1.5 },
  });
  s.addText("REAL EXAMPLE FROM THE DATA", {
    x: 0.7, y: 4.95, w: 12, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, charSpacing: 3, margin: 0,
  });
  s.addText("Filename ↔ internal date mismatch", {
    x: 0.7, y: 5.25, w: 12, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });
  s.addText([
    { text: "Credit_Data_-_30-03-2025.csv ", options: { fontFace: "Consolas", color: C.terra, bold: true } },
    { text: "contains an internal ", options: { } },
    { text: "DATE ", options: { fontFace: "Consolas" } },
    { text: "column with value ", options: { } },
    { text: "3/31/2025", options: { fontFace: "Consolas", color: C.terra, bold: true } },
    { text: " — silent date drift that would land in PAR-30 quarter-end metrics.", options: { } },
  ], {
    x: 0.7, y: 5.6, w: 12, h: 0.45,
    fontFace: FONT_BODY, fontSize: 12, color: C.navy, margin: 0,
  });
  s.addText([
    { text: "→ ", options: { color: C.teal, bold: true } },
    { text: "Caught automatically by check #1 with severity=CRITICAL on first run. Alert routed to PagerDuty; DAG halted before downstream tasks ran.", options: { } },
  ], {
    x: 0.7, y: 6.1, w: 12, h: 0.6,
    fontFace: FONT_BODY, fontSize: 12, color: C.navy, margin: 0,
  });
}

// =================================================================
// SLIDE 6 — Feature engineering (focus risk_category)
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Feature engineering",
                "Four derived fields per the brief; risk_category is where the judgement shows");

  // Left: feature list
  s.addText("Four required features", {
    x: 0.5, y: 1.4, w: 5.5, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.navy, margin: 0,
  });
  const features = [
    { name: "age_band", desc: "from DOB at each reporting date — 18-25, 26-35, 36-45, 46-55, 55+, plus explicit 'Unknown' bucket so coverage stays visible" },
    { name: "avg_monthly_income_band", desc: "received_total ÷ duration_months → 8 bands per brief. 'Received' used as canonical total to avoid sub-channel double-counting" },
    { name: "days_past_due", desc: "(reporting_date − next_invoice_date), clamped to 0 when no arrears. Source value retained for reconciliation" },
    { name: "risk_category", desc: "the credit-risk judgement call → see right" },
  ];
  features.forEach((f, i) => {
    const y = 1.85 + i * 0.85;
    s.addText(f.name, {
      x: 0.5, y, w: 5.5, h: 0.3,
      fontFace: "Consolas", fontSize: 12, bold: true, color: C.terra, margin: 0,
    });
    s.addText(f.desc, {
      x: 0.5, y: y + 0.3, w: 5.5, h: 0.55,
      fontFace: FONT_BODY, fontSize: 11, color: C.slate, margin: 0,
    });
  });

  // Right: risk_category logic
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: 1.35, w: 6.4, h: 5.4,
    fill: { color: C.navy }, line: { type: "none" },
  });
  s.addText("risk_category logic", {
    x: 6.6, y: 1.5, w: 6, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.white, margin: 0,
  });
  s.addText("Standard PAR-bucket framework adapted to ABC Phones' status taxonomy", {
    x: 6.6, y: 1.9, w: 6, h: 0.3,
    fontFace: FONT_BODY, fontSize: 10, color: C.stone, italic: true, margin: 0,
  });

  const rules = [
    { tag: "CRITICAL", rule: "Write Off / Lost Write Off  OR  DPD ≥ 90", color: C.terra },
    { tag: "HIGH",     rule: "DPD 31-89  OR  L2 ∈ {PAR 30, FMD}",         color: "F59E0B" },
    { tag: "MEDIUM",   rule: "DPD 1-30  OR  L2 ∈ {PAR 7, FPD, Inactive}", color: "EAB308" },
    { tag: "LOW",      rule: "DPD = 0  AND  L2 = Active",                  color: C.teal },
    { tag: "CLOSED",   rule: "L2 = Paid Off  (out of active book)",        color: "6B7280" },
    { tag: "RETURNED", rule: "L2 = Return  (out of active book)",          color: "6B7280" },
  ];
  rules.forEach((r, i) => {
    const y = 2.3 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 6.6, y, w: 1.4, h: 0.5, fill: { color: r.color }, line: { type: "none" },
    });
    s.addText(r.tag, {
      x: 6.6, y, w: 1.4, h: 0.5,
      fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(r.rule, {
      x: 8.1, y, w: 4.6, h: 0.5,
      fontFace: "Consolas", fontSize: 10, color: C.white, valign: "middle", margin: 0,
    });
  });

  s.addText("Mirrors IFRS-9 staging logic and standard microfinance PAR-bucketing.", {
    x: 6.6, y: 6.4, w: 6, h: 0.3,
    fontFace: FONT_BODY, fontSize: 9, italic: true, color: C.stone, margin: 0,
  });
}

// =================================================================
// SLIDE 7 — Portfolio health (chart)
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Portfolio health: book grew fast, quality slipped",
                "Five quarterly snapshots, 2025-01-01 through 2025-12-30");

  // Left: KPI bar chart — delinquency, PAR 90, write-off rates
  const labels = ["Q1 '25", "Q1 end", "Q2 end", "Q3 end", "Q4 end"];
  s.addChart(pres.charts.LINE, [
    { name: "Delinquency rate", labels, values: [41.4, 43.5, 42.8, 43.5, 44.8] },
    { name: "PAR 90+",           labels, values: [28.5, 31.8, 32.9, 33.8, 33.0] },
    { name: "Write-off rate",    labels, values: [13.8, 16.4, 17.5, 18.5, 18.2] },
  ], {
    x: 0.5, y: 1.4, w: 7.5, h: 5.4,
    chartColors: [C.terra, C.navyLt, C.slate],
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: C.slate,
    showTitle: true, title: "Risk metrics by snapshot (%)", titleFontSize: 13, titleColor: C.navy,
    valAxisLabelColor: C.slate, catAxisLabelColor: C.slate,
    valAxisLabelFontSize: 10, catAxisLabelFontSize: 10,
    valGridLine: { color: C.stone, size: 0.5 }, catGridLine: { style: "none" },
    lineSize: 3, lineSmooth: false, showValue: false,
    chartArea: { fill: { color: C.white }, roundedCorners: false },
  });

  // Right: collection-rate stat + take-aways
  statCallout(s, 8.3, 1.4, 4.5, 1.4, "59.5%", "Active-loan collection rate (latest) — down from 69.4% Q1", C.terra);
  s.addText("Take-aways", {
    x: 8.3, y: 2.95, w: 4.5, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.navy, margin: 0,
  });
  const takeaways = [
    { text: "Book size more than doubled in 2025 (133% growth in active loans).", options: { bullet: true, breakLine: true } },
    { text: "Delinquency, PAR 90, and write-off rates all climbed in parallel — not a one-off.", options: { bullet: true, breakLine: true } },
    { text: "Collection rate fell 10 percentage points — the leading indicator.", options: { bullet: true, breakLine: true } },
    { text: "Pattern is consistent with rapid origination outpacing underwriting controls.", options: { bullet: true } },
  ];
  s.addText(takeaways, {
    x: 8.3, y: 3.4, w: 4.5, h: 3.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, valign: "top", margin: 0, paraSpaceAfter: 6,
  });
}

// =================================================================
// SLIDE 8 — Segment finding: the "Unknown" age band
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Where the risk really lives",
                "Loans without complete customer profiles default ~5pp more than the rest of the book");

  // Left: segment delinquency bar chart (latest snapshot)
  const segLabels = ["46-55", "36-45", "150K+\nincome", "100K-150K\nincome", "26-35", "Portfolio\navg", "Unknown\nage band"];
  const segValues = [32.4,    35.8,    36.0,            36.7,             45.2,    44.8,            49.6];
  s.addChart(pres.charts.BAR, [
    { name: "Delinquency rate (%)", labels: segLabels, values: segValues },
  ], {
    x: 0.5, y: 1.35, w: 7.8, h: 5.4,
    barDir: "col",
    chartColors: [C.navyLt],
    showLegend: false,
    showTitle: true, title: "Delinquency rate by segment, latest snapshot (≥200 loans)",
    titleFontSize: 13, titleColor: C.navy,
    valAxisLabelColor: C.slate, catAxisLabelColor: C.slate,
    valAxisLabelFontSize: 10, catAxisLabelFontSize: 10,
    valAxisMinVal: 0, valAxisMaxVal: 55,
    valGridLine: { color: C.stone, size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.navy, dataLabelFontSize: 10,
    chartArea: { fill: { color: C.white }, roundedCorners: false },
  });

  // Right: insight panel
  s.addShape(pres.shapes.RECTANGLE, {
    x: 8.5, y: 1.35, w: 4.3, h: 5.4,
    fill: { color: C.navy }, line: { type: "none" },
  });
  s.addText("THE FINDING", {
    x: 8.7, y: 1.5, w: 4, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, charSpacing: 3, margin: 0,
  });
  s.addText("Loans with no DOB on file (46% of latest book) default at 49.6% — almost 5pp above portfolio average.", {
    x: 8.7, y: 1.85, w: 4, h: 1.6,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.white, margin: 0,
  });
  s.addText("Loans WITH complete profiles (older borrowers, higher income) consistently perform 8-12pp better.", {
    x: 8.7, y: 3.5, w: 4, h: 1.4,
    fontFace: FONT_BODY, fontSize: 12, color: C.white, margin: 0,
  });
  s.addShape(pres.shapes.LINE, {
    x: 8.7, y: 4.95, w: 3.9, h: 0, line: { color: C.terra, width: 1.5 },
  });
  s.addText("This isn't only a data gap — it's a credit-decisioning gap. The pipeline approves loans without complete profiles, and those loans default more.", {
    x: 8.7, y: 5.1, w: 4, h: 1.55,
    fontFace: FONT_BODY, fontSize: 11, color: C.stone, italic: true, margin: 0,
  });
}

// =================================================================
// SLIDE 9 — Credit × NPS + recommendation
// =================================================================
{
  const s = pres.addSlide();
  addPageHeader(s, "Credit × NPS — and one fix that helps both",
                "Each NPS response joined to the customer's most recent credit snapshot");

  // Left: NPS by risk_category bar chart
  const npsLabels = ["Closed", "High", "Low", "Medium", "Returned", "Critical"];
  const npsValues = [13.4,     17.7,   11.3,  10.4,     -8.1,       -23.7];
  s.addChart(pres.charts.BAR, [
    { name: "Net Promoter Score", labels: npsLabels, values: npsValues },
  ], {
    x: 0.5, y: 1.35, w: 6.8, h: 5.4,
    barDir: "col",
    chartColors: [C.teal],
    showLegend: false,
    showTitle: true, title: "Net Promoter Score by risk category",
    titleFontSize: 13, titleColor: C.navy,
    valAxisLabelColor: C.slate, catAxisLabelColor: C.slate,
    valAxisLabelFontSize: 10, catAxisLabelFontSize: 10,
    valGridLine: { color: C.stone, size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.navy, dataLabelFontSize: 10,
    chartArea: { fill: { color: C.white }, roundedCorners: false },
  });

  // Right: recommendation block
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.5, y: 1.35, w: 5.3, h: 5.4,
    fill: { color: C.paper }, line: { color: C.stone, width: 0.75 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.5, y: 1.35, w: 0.08, h: 5.4, fill: { color: C.terra }, line: { type: "none" },
  });
  s.addText("RECOMMENDATION", {
    x: 7.7, y: 1.5, w: 5, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, charSpacing: 3, margin: 0,
  });
  s.addText("Fix the lock-after-payment issue", {
    x: 7.7, y: 1.85, w: 5, h: 0.5,
    fontFace: FONT_HEAD, fontSize: 18, bold: true, color: C.navy, margin: 0,
  });

  const recBullets = [
    { text: "12-17% of NPS respondents across every risk segment report ", options: { breakLine: false } },
    { text: "'phone locked despite paying on time'", options: { italic: true, color: C.terra, breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "This drives ", options: { breakLine: false } },
    { text: "both ", options: { bold: true, breakLine: false } },
    { text: "outcomes the business cares about: customer dissatisfaction (Critical-risk NPS = -23.7) AND avoidable arrears flags when the locking system runs ahead of payment reflection.", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "Fix:", options: { bold: true, color: C.teal, breakLine: false } },
    { text: " a 24-hour grace window before remote-locking, plus a reconciliation job that lifts locks within 1 hour of payment confirmation.", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "→ improves NPS and reduces 'fake' delinquency simultaneously — a rare win-win in collections design.", options: { italic: true, color: C.slate } },
  ];
  s.addText(recBullets, {
    x: 7.7, y: 2.4, w: 5, h: 4.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, valign: "top", margin: 0,
  });
}

// =================================================================
// SLIDE 10 — Data gaps + production roadmap
// =================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addText("Where this goes next", {
    x: 0.5, y: 0.4, w: 12.3, h: 0.6,
    fontFace: FONT_HEAD, fontSize: 26, bold: true, color: C.white, margin: 0,
  });
  s.addText("Three data improvements ABC Phones should make + the production-roadmap delta", {
    x: 0.5, y: 1.0, w: 12.3, h: 0.4,
    fontFace: FONT_BODY, fontSize: 12, color: C.stone, margin: 0,
  });

  // Left column — data improvements
  s.addText("DATA IMPROVEMENTS", {
    x: 0.5, y: 1.7, w: 6, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, charSpacing: 3, margin: 0,
  });
  const improvements = [
    {
      n: "1",
      title: "Introduce a stable customer_id",
      body: "Hash of national ID or phone, propagated from KYC into credit and NPS. Unlocks lifetime-value, repeat-borrower risk, and household-level analysis.",
    },
    {
      n: "2",
      title: "Standardise on ISO-8601 + a YAML schema spec",
      body: "Versioned alongside the data; documents the unit of every numeric column (Duration in months, balance in KES, etc.). Eliminates ambiguity discussed in Slide 2.",
    },
    {
      n: "3",
      title: "Replace daily snapshots with an event stream",
      body: "Emit payment_made, status_changed, arrears_updated events; derive snapshots downstream. Removes the filename-vs-internal-date drift class of bugs entirely.",
    },
  ];
  improvements.forEach((imp, i) => {
    const y = 2.1 + i * 1.45;
    s.addShape(pres.shapes.OVAL, {
      x: 0.5, y, w: 0.55, h: 0.55, fill: { color: C.terra }, line: { type: "none" },
    });
    s.addText(imp.n, {
      x: 0.5, y, w: 0.55, h: 0.55,
      fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(imp.title, {
      x: 1.2, y: y + 0.0, w: 5.0, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 13, bold: true, color: C.white, margin: 0,
    });
    s.addText(imp.body, {
      x: 1.2, y: y + 0.4, w: 5.0, h: 1.0,
      fontFace: FONT_BODY, fontSize: 10.5, color: C.stone, margin: 0,
    });
  });

  // Right column — production roadmap
  s.addText("PRODUCTION ROADMAP DELTA", {
    x: 6.9, y: 1.7, w: 6, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, charSpacing: 3, margin: 0,
  });
  const roadmap = [
    ["Orchestration", "run_pipeline.py  →  Airflow / Prefect / Dagster DAG; one task per stage; SLAs"],
    ["Storage",       "Local Parquet  →  S3 / GCS, same Hive partitioning"],
    ["Compute",       "DuckDB  →  Athena or BigQuery — same SQL, no rewrite"],
    ["Transforms",    "Python + SQL  →  dbt (lineage, docs, tests for free)"],
    ["Quality",       "Custom Python checks  →  Great Expectations / dbt tests / Soda"],
    ["Alerting",      "Mocked log routes  →  PagerDuty + Slack SDKs, on-call rota"],
    ["Lineage",       "Add  →  OpenLineage events from each task"],
  ];
  roadmap.forEach((r, i) => {
    const y = 2.1 + i * 0.55;
    s.addText(r[0], {
      x: 6.9, y, w: 1.7, h: 0.45,
      fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.terra, valign: "middle", margin: 0,
    });
    s.addText(r[1], {
      x: 8.7, y, w: 4.5, h: 0.45,
      fontFace: FONT_BODY, fontSize: 10.5, color: C.white, valign: "middle", margin: 0,
    });
  });

  // Footer
  s.addShape(pres.shapes.LINE, {
    x: 0.5, y: 6.6, w: 12.3, h: 0, line: { color: C.terra, width: 1 },
  });
  s.addText("Thank you  ·  Annex Technologies — Data Engineer Case Study", {
    x: 0.5, y: 6.75, w: 12.3, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 11, bold: true, color: C.white, align: "center", margin: 0,
  });
}

// -------- write --------
pres.writeFile({ fileName: OUT }).then((f) => {
  console.log("✔ wrote", f);
});
