const API_BASE_URL = window.DASHBOARD_API_BASE_URL || "http://127.0.0.1:8000/api";

async function apiGet(endpoint) {
  const response = await fetch(API_BASE_URL + endpoint);

  if (!response.ok) {
    throw new Error("HTTP_" + response.status);
  }

  return response.json();
}

async function getDashboardData() {
  const requests = [
    apiGet("/analytics/dashboard-metrics?top_n=8"),
    apiGet("/zones/map/summary"),
  ];

  const results = await Promise.all(requests);

  return {
    metrics: results[0],
    zoneGeoJson: results[1],
  };
}

function getZoneRevenueRanking(limit, offset) {
  return apiGet("/analytics/zone-revenue-ranking?limit=" + limit + "&offset=" + offset);
}

function getHourlyTripCounts() {
  return apiGet("/analytics/hourly-trip-counts");
}

function getBoroughTripRanking(limit, offset) {
  return apiGet("/analytics/borough-trip-ranking?limit=" + limit + "&offset=" + offset);
}
