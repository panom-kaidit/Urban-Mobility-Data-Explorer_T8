document.addEventListener("DOMContentLoaded", initDashboard);

async function initDashboard() {
  const status = document.getElementById("loadStatus");

  try {
    const results = await Promise.all([
      apiGet("/analytics/dashboard-metrics?top_n=8"),
      apiGet("/zones/map/summary"),
    ]);

    const metrics = results[0];
    const zoneGeoJson = results[1];

    renderSummary(metrics.summary);
    renderCharts(metrics);
    renderMap(zoneGeoJson);
    bindControls();

    status.textContent = "Loaded";
  } catch (error) {
    console.error(error);
    status.textContent = "Load failed";
  }
}

function renderSummary(summary) {
  document.getElementById("kpiTrips").textContent = formatNumber(summary.total_trips);
  document.getElementById("kpiRevenue").textContent = formatMoney(summary.total_revenue);
  document.getElementById("kpiFare").textContent = formatMoney(summary.avg_fare);

  if (summary.top_borough) {
    document.getElementById("kpiBorough").textContent = summary.top_borough.borough;
  } else {
    document.getElementById("kpiBorough").textContent = "--";
  }
}

function bindControls() {
  document.getElementById("mapMetricSelect").addEventListener("change", function (event) {
    changeMapMetric(event.target.value);
  });
}
