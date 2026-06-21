// Reports page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js

var _reportContext = {
  summary: null,
  topPickupZones: [],
  topDropoffZones: [],
  revenueByBorough: [],
  revenueTrend: [],
};

var _rawParquetRows = 7696617;

async function initReportsPage() {
  injectSidebar("reports");
  injectNavbar();
  setNavbarTitle("Reports");

  _renderSummaryTable(null);  // Show loading state immediately
  _loadReportContext();       // Fire all independent loaders — don't await
}

function _loadReportContext() {
  var badge = document.getElementById("reports-summary-badge");
  if (badge) {
    badge.textContent = "Loading...";
    badge.className = "badge badge-cyan";
  }

  var pending = 5;
  function _onDone() {
    pending--;
    if (pending <= 0 && badge) {
      badge.textContent = "Live Data";
      badge.className = "badge badge-green";
    }
  }
  function _onError() {
    pending--;
    if (badge && pending <= 0) {
      badge.textContent = "Partial Data";
      badge.className = "badge badge-yellow";
    }
  }

  // Summary renders as soon as it arrives — usually fast due to backend cache.
  fetchSummary().then(function(summary) {
    _reportContext.summary = summary;
    _renderSummaryTable(summary);
    _onDone();
  }).catch(function(err) {
    console.error("Reports summary:", err);
    if (badge) { badge.textContent = "API Offline"; badge.className = "badge badge-yellow"; }
    _onError();
  });

  fetchTopPickupZones(10).then(function(data) {
    _reportContext.topPickupZones = data && data.zones ? data.zones : [];
    _onDone();
  }).catch(function() { _onError(); });

  fetchTopDropoffZones(10).then(function(data) {
    _reportContext.topDropoffZones = data && data.zones ? data.zones : [];
    _onDone();
  }).catch(function() { _onError(); });

  fetchRevenueByBorough().then(function(data) {
    _reportContext.revenueByBorough = data && data.boroughs ? data.boroughs : [];
    _onDone();
  }).catch(function() { _onError(); });

  fetchRevenueTrends().then(function(data) {
    _reportContext.revenueTrend = data && data.trend ? data.trend : [];
    _onDone();
  }).catch(function() { _onError(); });
}

function _renderSummaryTable(summary) {
  var tbody = document.getElementById("reports-data-tbody");
  if (!tbody) return;

  var rows = summary ? _buildLiveSummaryRows(summary) : [
    { metric: "Dataset Status", value: "Loading", notes: "Reading current database summary from the API." },
  ];

  tbody.innerHTML = rows.map(function(r) {
    return (
      "<tr>" +
        "<td style='font-weight:600;color:var(--text-primary)'>" + r.metric + "</td>" +
        "<td style='font-family:var(--font-mono);color:var(--accent-cyan)'>" + r.value + "</td>" +
        "<td style='color:var(--text-secondary)'>" + r.notes + "</td>" +
      "</tr>"
    );
  }).join("");
}

function _buildLiveSummaryRows(summary) {
  var loadedTrips = Number(summary.totalTrips || 0);
  var loadedPercent = _rawParquetRows ? ((loadedTrips / _rawParquetRows) * 100).toFixed(1) + "%" : "n/a";
  var rejectionRate = loadedTrips
    ? ((Number(summary.suspiciousRecords || 0) / (loadedTrips + Number(summary.suspiciousRecords || 0))) * 100).toFixed(2) + "%"
    : "0%";

  return [
    { metric: "Loaded Trip Records", value: formatNumber(loadedTrips), notes: "Rows currently present in data/mobility.db." },
    { metric: "Raw Parquet Rows", value: formatNumber(_rawParquetRows), notes: "Rows reported by yellow_tripdata_2019-01.parquet." },
    { metric: "Load Coverage", value: loadedPercent, notes: "The database appears partially loaded if this is below 100%." },
    { metric: "Total Revenue", value: formatCurrency(summary.totalRevenue), notes: "Computed from loaded trips." },
    { metric: "Average Fare", value: formatCurrency(summary.avgFare), notes: "Average fare_amount across loaded trips." },
    { metric: "Average Distance", value: formatDecimal(summary.avgDistance, 2) + " mi", notes: "Average trip_distance across loaded trips." },
    { metric: "Date Range", value: _formatDateRange(summary), notes: "Pickup dates found in the loaded database." },
    { metric: "Outside Jan 2019", value: formatNumber(summary.outsideJanuaryCount), notes: "Rows with pickup dates outside the expected January 2019 range." },
    { metric: "Removed Records", value: formatNumber(summary.suspiciousRecords), notes: "Rows stored in suspicious_records during cleaning." },
    { metric: "Rejection Rate", value: rejectionRate, notes: "Removed rows divided by loaded plus removed rows." },
    { metric: "Outliers Kept", value: formatNumber(summary.outlierCount), notes: "Rows flagged as outliers but retained for analysis." },
    { metric: "Taxi Zones", value: formatNumber(summary.locationCount), notes: "Location lookup records." },
    { metric: "Zone Boundaries", value: formatNumber(summary.zoneBoundaryCount), notes: "GeoJSON boundaries loaded for map rendering." },
    { metric: "API Endpoints", value: "11+", notes: "Includes summary, pickup/dropoff zones, fare, revenue, trips, locations, and suspicious records." },
  ];
}

function _formatDateRange(summary) {
  if (!summary || !summary.startDate || !summary.endDate) return "n/a";
  if (summary.startDate === summary.endDate) return summary.startDate;
  return summary.startDate + " to " + summary.endDate;
}

function _getReports() {
  var summary = _reportContext.summary || {};
  var topPickup = _reportContext.topPickupZones.slice(0, 3).map(_zoneName).join(", ") || "No pickup zone data loaded";
  var topDropoff = _reportContext.topDropoffZones.slice(0, 3).map(_dropoffZoneName).join(", ") || "No dropoff zone data loaded";
  var topBorough = _reportContext.revenueByBorough[0];
  var topBoroughText = topBorough
    ? topBorough.borough + " leads with " + formatCurrency(topBorough.total_revenue) + " from " + formatNumber(topBorough.total_trips) + " trips."
    : "No borough revenue data loaded.";

  return {
    executive: {
      title: "Executive Summary - NYC Yellow Taxi January 2019",
      sections: [
        { heading: "Current Database", body: formatNumber(summary.totalTrips || 0) + " clean trip records are currently loaded from " + formatNumber(_rawParquetRows) + " raw Parquet rows. This indicates the SQLite database is not yet a complete load of the raw dataset." },
        { heading: "Revenue", body: "Loaded trips contain " + formatCurrency(summary.totalRevenue || 0) + " in total revenue, with an average fare of " + formatCurrency(summary.avgFare || 0) + " and average distance of " + formatDecimal(summary.avgDistance || 0, 2) + " miles." },
        { heading: "Date Integrity", body: "The expected pickup window is January 1-31, 2019. The loaded database currently spans " + _formatDateRange(summary) + " and includes " + formatNumber(summary.outsideJanuaryCount || 0) + " rows outside January 2019." },
        { heading: "Top Pickup Zones", body: "The leading pickup zones in the loaded database are " + topPickup + "." },
      ],
    },
    revenue: {
      title: "Revenue Analysis - Borough & Payment Breakdown",
      sections: [
        { heading: "Borough Revenue", body: topBoroughText },
        { heading: "Loaded Revenue Base", body: "All revenue calculations on this page come from the current SQLite database, so they will change after a full ETL reload." },
        { heading: "Daily Trend", body: "The API currently returns " + formatNumber(_reportContext.revenueTrend.length) + " daily revenue points." },
      ],
    },
    zones: {
      title: "Zone Coverage Report - NYC Taxi Zones",
      sections: [
        { heading: "Coverage", body: formatNumber(summary.locationCount || 0) + " taxi zones are loaded, with " + formatNumber(summary.zoneBoundaryCount || 0) + " spatial boundaries available." },
        { heading: "High-Demand Pickups", body: "The highest pickup zones are " + topPickup + "." },
        { heading: "High-Demand Dropoffs", body: "The highest dropoff zones are " + topDropoff + "." },
      ],
    },
    quality: {
      title: "Data Quality Report - ETL Validation Results",
      sections: [
        { heading: "Removed Records", body: formatNumber(summary.suspiciousRecords || 0) + " records are currently stored in suspicious_records. In this database, removals are from invalid timestamps and negative money values." },
        { heading: "Outliers Retained", body: formatNumber(summary.outlierCount || 0) + " records are flagged as outliers but kept in the trips table for analysis." },
        { heading: "Date Anomalies", body: formatNumber(summary.outsideJanuaryCount || 0) + " loaded records fall outside January 2019. The ETL cleaner should reject out-of-period pickup/dropoff dates before the final load." },
      ],
    },
    mobility: {
      title: "Mobility Patterns - Trip Flow Analysis",
      sections: [
        { heading: "Pickup vs. Dropoff Demand", body: "Top pickup zones: " + topPickup + ". Top dropoff zones: " + topDropoff + "." },
        { heading: "Borough Flow", body: "The current data is strongly Manhattan-heavy, which may reflect the partial database load. Re-run the full ETL before treating borough share as final." },
        { heading: "Implemented Analytics", body: "Top dropoff zones and average distance by hour are implemented in the backend and available through the shared API client." },
      ],
    },
  };
}

function _zoneName(zone) {
  return zone.zone_name || zone.pickup_zone || "Unknown";
}

function _dropoffZoneName(zone) {
  return zone.dropoff_zone || zone.zone_name || "Unknown";
}

function viewReport(type) {
  var reports = _getReports();
  var def = reports[type];
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

document.addEventListener("DOMContentLoaded", function() {
  // Only run the full reports init (sidebar, navbar, all API calls) on the reports page.
  // On other pages (e.g. dashboard) that also load reports.js, do a lightweight summary
  // table population only — no sidebar override, no duplicate API calls.
  if (document.getElementById("report-cards")) {
    initReportsPage();
  } else if (document.getElementById("reports-data-tbody")) {
    _renderSummaryTable(null);
    fetchSummary().then(function(s) { _renderSummaryTable(s); }).catch(function() {});
  }
});
