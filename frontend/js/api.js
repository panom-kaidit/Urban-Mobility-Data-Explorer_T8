// Shared API client for all dashboard pages.
// Loads after Chart.js so it can set global chart defaults for the dark theme.

const API_BASE_URL = "http://localhost:8000/api";

// ---- Chart.js dark-theme global defaults ----
if (typeof Chart !== "undefined") {
  Chart.defaults.color           = "#8B9BB4";
  Chart.defaults.borderColor     = "rgba(0, 212, 255, 0.07)";
  Chart.defaults.font.family     = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size       = 12;
  Chart.defaults.plugins.legend.labels.color = "#8B9BB4";
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(11, 20, 71, 0.95)";
  Chart.defaults.plugins.tooltip.borderColor      = "rgba(0, 212, 255, 0.3)";
  Chart.defaults.plugins.tooltip.borderWidth      = 1;
  Chart.defaults.plugins.tooltip.titleColor       = "#E2E8F0";
  Chart.defaults.plugins.tooltip.bodyColor        = "#8B9BB4";
  Chart.defaults.plugins.tooltip.padding          = 10;
  Chart.defaults.plugins.tooltip.cornerRadius     = 8;
}

// ---- Core HTTP helper ----

async function fetchJSON(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${endpoint}`);
  }
  return response.json();
}

// ---- Trips ----

async function fetchTrips(filters = {}) {
  const params = [];
  if (filters.limit)   params.push(`limit=${encodeURIComponent(filters.limit)}`);
  if (filters.offset)  params.push(`offset=${encodeURIComponent(filters.offset)}`);
  if (filters.borough) params.push(`borough=${encodeURIComponent(filters.borough)}`);
  if (filters.distance) params.push(`distance=${encodeURIComponent(filters.distance)}`);
  if (filters.fare)    params.push(`fare=${encodeURIComponent(filters.fare)}`);
  if (filters.date)    params.push(`date=${encodeURIComponent(filters.date)}`);
  const qs = params.length ? `?${params.join("&")}` : "";
  return fetchJSON(`/trips${qs}`);
}

async function fetchTripById(tripId) {
  return fetchJSON(`/trips/${tripId}`);
}

// ---- Zones ----

async function fetchZone(zoneId) {
  return fetchJSON(`/zones/${zoneId}`);
}

// ---- Analytics — implemented endpoints ----

async function fetchTopPickupZones(topN = 10) {
  return fetchJSON(`/analytics/top-pickup-zones?top_n=${topN}`);
}

async function fetchFareDistribution() {
  return fetchJSON("/analytics/fare-distribution");
}

async function fetchFareDistributionDetailed() {
  return fetchJSON("/analytics/fare-distribution-detailed");
}

async function fetchRevenueByBorough() {
  return fetchJSON("/analytics/revenue-by-borough");
}

async function fetchRevenueTrends() {
  return fetchJSON("/analytics/revenue-trends");
}

async function fetchAverageFare() {
  return fetchJSON("/analytics/average-fare");
}

async function fetchSuspiciousRecords(limit = 100, offset = 0) {
  return fetchJSON(`/suspicious-records?limit=${limit}&offset=${offset}`);
}

// ---- Analytics — additional endpoints ----

async function fetchTopDropoffZones(topN = 10) {
  try {
    return await fetchJSON(`/analytics/top-dropoff-zones?top_n=${topN}`);
  } catch (_) {
    return null;
  }
}

async function fetchAverageDistanceByHour() {
  try {
    return await fetchJSON("/analytics/average-distance");
  } catch (_) {
    return null;
  }
}

// ---- Dashboard summary (exact aggregates from DB) ----

async function fetchSummary() {
  const raw = await fetchJSON("/analytics/summary");
  return {
    totalTrips:    raw.total_trips      || 0,
    totalRevenue:  raw.total_revenue    || 0,
    avgFare:       raw.average_fare     || 0,
    avgDistance:   raw.average_distance || 0,
  };
}

// ---- Format helpers used across pages ----

function formatCurrency(value) {
  return "$" + Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-US");
}

function formatDecimal(value, dp = 2) {
  return Number(value).toFixed(dp);
}

function formatCompact(value) {
  const v = Number(value);
  if (v >= 1e9)  return (v / 1e9).toFixed(1) + "B";
  if (v >= 1e6)  return (v / 1e6).toFixed(1) + "M";
  if (v >= 1e3)  return (v / 1e3).toFixed(1) + "K";
  return String(v);
}
