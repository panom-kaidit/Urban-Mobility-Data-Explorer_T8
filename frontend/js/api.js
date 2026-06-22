// Shared API client for all dashboard pages.
// Loads after Chart.js so it can set global chart defaults for the dark theme.

const API_BASE_URL = "http://localhost:8000/api";

// Set global Chart.js defaults for the dark theme.
if (typeof Chart !== "undefined") {
  Chart.defaults.animation       = false;
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

// API client functions for fetching data from the backend API. All functions return a Promise that resolves to the parsed JSON response.

async function fetchJSON(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${endpoint}`);
  }
  return response.json();
}

// Trips endpoints

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

// Zones endpoints

async function fetchZone(zoneId) {
  return fetchJSON(`/zones/${zoneId}`);
}

// Analytics endpoints

function _analyticsFilterParams(filters) {
  const params = [];
  if (filters.borough)  params.push(`borough=${encodeURIComponent(filters.borough)}`);
  if (filters.distance) params.push(`distance=${encodeURIComponent(filters.distance)}`);
  if (filters.fare)     params.push(`fare=${encodeURIComponent(filters.fare)}`);
  if (filters.date)     params.push(`date=${encodeURIComponent(filters.date)}`);
  return params;
}

async function fetchTopPickupZones(topN = 10, filters = {}) {
  const params = [`top_n=${topN}`].concat(_analyticsFilterParams(filters));
  return fetchJSON(`/analytics/top-pickup-zones?${params.join("&")}`);
}

async function fetchFareDistribution(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  return fetchJSON(`/analytics/fare-distribution${qs}`);
}

async function fetchFareDistributionDetailed() {
  return fetchJSON("/analytics/fare-distribution-detailed");
}

async function fetchRevenueByBorough(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  return fetchJSON(`/analytics/revenue-by-borough${qs}`);
}

async function fetchRevenueTrends(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  return fetchJSON(`/analytics/revenue-trends${qs}`);
}

async function fetchAverageFare(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  return fetchJSON(`/analytics/average-fare${qs}`);
}

async function fetchSuspiciousRecords(limit = 100, offset = 0) {
  return fetchJSON(`/suspicious-records?limit=${limit}&offset=${offset}`);
}

// Analytics endpoints additional

async function fetchTopDropoffZones(topN = 10, filters = {}) {
  const params = [`top_n=${topN}`].concat(_analyticsFilterParams(filters));
  try {
    return await fetchJSON(`/analytics/top-dropoff-zones?${params.join("&")}`);
  } catch (_) {
    return null;
  }
}

async function fetchAverageDistanceByHour(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  try {
    return await fetchJSON(`/analytics/average-distance${qs}`);
  } catch (_) {
    return null;
  }
}

// summary endpoint

async function fetchSummary(filters = {}) {
  const params = _analyticsFilterParams(filters);
  const qs = params.length ? `?${params.join("&")}` : "";
  const raw = await fetchJSON(`/analytics/summary${qs}`);
  return {
    totalTrips:    raw.total_trips      || 0,
    totalRevenue:  raw.total_revenue    || 0,
    avgFare:       raw.average_fare     || 0,
    avgDistance:   raw.average_distance || 0,
    startDate:     raw.start_date       || null,
    endDate:       raw.end_date         || null,
    outlierCount:  raw.outlier_count    || 0,
    outsideJanuaryCount: raw.outside_january_count || 0,
    suspiciousRecords: raw.suspicious_records || 0,
    locationCount: raw.location_count || 0,
    zoneBoundaryCount: raw.zone_boundary_count || 0,
  };
}

// Formatting utility functions for displaying numbers in the dashboard.

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
