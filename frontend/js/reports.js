// Reports page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js


// This object holds the data for each report section.
var REPORT_DATA = {
  executive: {
    title: "Executive Summary - NYC Yellow Taxi January 2019",
    sections: [
      { heading: "Dataset Overview", body: "7,682,940 clean trip records loaded from a raw Parquet source. 13,677 records (0.18%) were removed during ETL validation. The dataset covers January 1–31, 2019 across 265 NYC taxi zones in 5 boroughs + EWR." },
      { heading: "Revenue", body: "Total revenue (from sampled trips) extrapolated from a 500-trip sample. Average fare per trip is approximately $16–18. Manhattan generates the highest revenue share (&gt;55% of total), followed by Brooklyn and Queens." },
      { heading: "Top Zones", body: "JFK Airport, LaGuardia Airport, and Midtown Manhattan consistently dominate pickup volume. The top 10 zones (ranked by custom Merge Sort algorithm) account for roughly 30% of all trips." },
      { heading: "Data Quality", body: "Primary rejection reasons: missing required values (NaN in datetime/location/distance), invalid timestamps (dropoff &le; pickup), negative monetary values. No data was altered — only removed or flagged." },
    ],
  },
  revenue: {
    title: "Revenue Analysis - Borough & Payment Breakdown",
    sections: [
      { heading: "Revenue by Borough", body: "Manhattan leads with the highest total revenue from taxi trips. Brooklyn and Queens follow significantly behind due to lower average fares and trip counts from outer boroughs." },
      { heading: "Payment Methods", body: "Credit card payments (type 1) account for the majority of transactions and carry a slightly higher average fare. Cash payments (type 2) are the second most common." },
      { heading: "Fare Distribution", body: "The $0–10 and $10–20 ranges contain the most trips (short city rides). Fares above $50 represent a small but significant revenue segment (airport transfers, long-distance rides)." },
      { heading: "Daily Trend", body: "Revenue shows a consistent weekday pattern with a slight dip on weekends. No major anomalies were detected in the January 2019 daily revenue series." },
    ],
  },
  zones: {
    title: "Zone Coverage Report - 265 NYC Taxi Zones",
    sections: [
      { heading: "Coverage", body: "265 zones loaded from taxi_zone_lookup.csv. 260 zones have corresponding GeoJSON polygon boundaries loaded from the taxi_zones shapefile. 5 zones (likely water/unknown) have no geometry." },
      { heading: "High-Demand Hotspots", body: "Airport zones (JFK, LaGuardia), Midtown, Upper East Side, and Times Square/Theater District are the top pickup zones. These zones generate disproportionately high revenue per trip due to longer distances or flat-rate airport fares." },
      { heading: "Underserved Zones", body: "Staten Island, parts of the Bronx, and outer Queens zones have minimal trip volume, reflecting lower taxi demand in those areas relative to population." },
      { heading: "Borough Summary", body: "Manhattan: 70 zones. Brooklyn: 61 zones. Queens: 69 zones. Bronx: 43 zones. Staten Island: 20 zones. EWR (Newark): 1 zone." },
    ],
  },
  quality: {
    title: "Data Quality Report - ETL Validation Results",
    sections: [
      { heading: "Total Removed", body: "13,677 records (0.18% of raw data) were removed during the cleaning stage. All removed records are stored in the suspicious_records table for audit purposes." },
      { heading: "Removal Reasons", body: "missing_required_value: NaN in datetime, location_id, trip_distance, or amount fields. invalid_timestamp: dropoff_datetime &le; pickup_datetime. negative_distance: trip_distance &lt; 0. negative_money_value: fare_amount or total_amount &lt; 0. duplicate_trip: exact row duplicate." },
      { heading: "Outlier Detection", body: "Additional records are flagged as outliers (is_outlier=1) but kept in the dataset: distance &gt;100mi, amount &gt;$500, speed &gt;120mph, duration &gt;8h. These 'suspicious but plausible' trips are labeled for downstream analysis." },
      { heading: "Pipeline Integrity", body: "Foreign key constraints are enforced (PRAGMA foreign_keys = ON). Load scripts use UPSERT semantics — safe to re-run without destroying existing data. Audit logs are written to etl/data/logs/ after each run." },
    ],
  },
  mobility: {
    title: "Mobility Patterns - Trip Flow Analysis",
    sections: [
      { heading: "Pickup vs. Dropoff Demand", body: "Top pickup zones and top dropoff zones show strong overlap for airport and Midtown zones. Residential zones tend to have more pickups in the morning and more dropoffs in the evening." },
      { heading: "Borough Flow", body: "The majority of trips are intra-Manhattan (pickup and dropoff both in Manhattan). Cross-borough trips typically involve airport connections or commuter routes." },
      { heading: "Fare by Route Type", body: "Airport routes (flat-rate zones) have significantly higher fares than standard metered rides. Short city hops (&lt;2 miles) dominate by volume but contribute less to total revenue." },
      { heading: "Pending Data", body: "Top dropoff zone analytics and average-distance-by-hour require backend endpoints that are not yet implemented (GET /api/analytics/top-dropoff-zones and GET /api/analytics/average-distance)." },
    ],
  },
};

var SUMMARY_ROWS = [
  { metric: "Total Trip Records",       value: "7,682,940",  notes: "After ETL cleaning" },
  { metric: "Suspicious Records",       value: "13,677",     notes: "Removed during validation" },
  { metric: "Rejection Rate",           value: "0.18%",      notes: "Very low — good data quality" },
  { metric: "Date Range",               value: "Jan 1–31, 2019", notes: "NYC Yellow Taxi" },
  { metric: "Taxi Zones",               value: "265",        notes: "Unique location IDs" },
  { metric: "Zone Boundaries",          value: "260",        notes: "GeoJSON polygons" },
  { metric: "Boroughs",                 value: "5 + EWR",    notes: "Manhattan, Brooklyn, Queens, Bronx, Staten Island" },
  { metric: "Database Size",            value: "~2.1 GB",    notes: "SQLite file" },
  { metric: "API Endpoints",            value: "11",         notes: "9 implemented, 2 pending" },
  { metric: "ETL Chunk Size",           value: "50,000 rows", notes: "Per batch" },
];

async function initReportsPage() {
  injectSidebar("reports");
  injectNavbar();
  setNavbarTitle("Reports");

  _renderSummaryTable();
  await _populateSummaryBadge();
}

function _renderSummaryTable() {
  var badge = document.getElementById("reports-summary-badge");
  if (badge) { badge.textContent = "Static Data"; badge.className = "badge badge-cyan"; }

  var tbody = document.getElementById("reports-data-tbody");
  if (!tbody) return;

  tbody.innerHTML = SUMMARY_ROWS.map(function(r) {
    return (
      "<tr>" +
        "<td style='font-weight:600;color:var(--text-primary)'>" + r.metric + "</td>" +
        "<td style='font-family:var(--font-mono);color:var(--accent-cyan)'>" + r.value + "</td>" +
        "<td style='color:var(--text-secondary)'>" + r.notes + "</td>" +
      "</tr>"
    );
  }).join("");
}

async function _populateSummaryBadge() {
  try {
    var data = await fetchRevenueTrends();
    if (data && data.trend && data.trend.length > 0) {
      var badge = document.getElementById("reports-summary-badge");
      if (badge) { badge.textContent = "Live Data"; badge.className = "badge badge-green"; }
    }
  } catch (_) {}
}

function viewReport(type) {
  var def = REPORT_DATA[type];
  if (!def) return;

  var viewer = document.getElementById("report-viewer");
  var title  = document.getElementById("report-viewer-title");
  var body   = document.getElementById("report-viewer-body");

  if (!viewer || !title || !body) return;

  title.textContent = def.title;
  body.innerHTML = def.sections.map(function(s) {
    return (
      '<div style="margin-bottom:1.25rem">' +
        '<h3 style="font-size:0.9rem;font-weight:700;color:var(--accent-cyan);margin-bottom:0.35rem">' + s.heading + '</h3>' +
        '<p style="font-size:0.82rem;color:var(--text-secondary);line-height:1.7">' + s.body + '</p>' +
      '</div>'
    );
  }).join("");

  viewer.style.display = "block";
  viewer.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeReport() {
  var viewer = document.getElementById("report-viewer");
  if (viewer) viewer.style.display = "none";
}

document.addEventListener("DOMContentLoaded", initReportsPage);
