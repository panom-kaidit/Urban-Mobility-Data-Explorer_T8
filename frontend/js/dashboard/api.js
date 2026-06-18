const API_BASE_URL = window.DASHBOARD_API_BASE_URL || "http://localhost:8001/api";

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
