// Dashboard page controller.
// Requires: api.js, charts.js, cards.js, navbar.js, sidebar.js, filters.js

var _topZonesChart = null;
var _fareDistChart = null;
var _dashboardLoading = false;

async function initDashboard() {
  injectSidebar("dashboard");
  injectNavbar();
  setNavbarTitle("Dashboard");
  injectFilters();
  setupFilterHandlers(function(filters) { loadDashboardData(filters); });
  await loadDashboardData({});
  showApp();
}

async function loadDashboardData(filters) {
  filters = filters || {};
  var hasFilters = Object.keys(filters).length > 0;
  if (_dashboardLoading && !hasFilters) return;
  _dashboardLoading = true;

  showCardsLoading();
  showChartLoading("zones-chart-container", "Loading top pickup zones…");
  showChartLoading("fare-chart-container",  "Loading fare distribution…");

  var results = await Promise.allSettled([
    fetchSummary(filters),
    fetchTopPickupZones(10, filters),
    fetchFareDistribution(filters),
  ]);

  var summary  = results[0].status === "fulfilled" ? results[0].value : null;
  var zones    = results[1].status === "fulfilled" ? results[1].value : null;
  var fareDist = results[2].status === "fulfilled" ? results[2].value : null;

  if (summary) {
    renderCards(summary);
    if (typeof _renderSummaryTable === "function") _renderSummaryTable(summary);
  }
  else showCardsError();

  if (zones && zones.zones && zones.zones.length > 0) {
    _renderTopZones(zones.zones);
  } else {
    showChartError("zones-chart-container", "Pickup zone data unavailable.");
  }

  if (fareDist && fareDist.distribution && fareDist.distribution.length > 0) {
    _renderFareDist(fareDist.distribution);
  } else {
    showChartError("fare-chart-container", "Fare data unavailable.");
  }

  _dashboardLoading = false;
}

function _renderTopZones(zones) {
  var container = document.getElementById("zones-chart-container");
  if (!container) return;
  container.innerHTML = '<canvas id="top-zones-canvas"></canvas>';

  var labels = zones.map(function(z) { return z.zone_name || ("Zone " + z.zone_id); });
  var values = zones.map(function(z) { return z.trip_count; });
  var colors = zones.map(function(z) { return boroughColor(z.borough); });

  if (_topZonesChart) { _topZonesChart.destroy(); _topZonesChart = null; }

  _topZonesChart = createHorizontalBarChart(
    document.getElementById("top-zones-canvas"),
    labels,
    values,
    colors,
    function(ctx) {
      var z = zones[ctx.dataIndex];
      return "Borough: " + (z.borough || "Unknown");
    }
  );
}

function _renderFareDist(distribution) {
  var container = document.getElementById("fare-chart-container");
  if (!container) return;
  container.innerHTML = '<canvas id="fare-dist-canvas"></canvas>';

  var labels = distribution.map(function(d) { return "$" + d.range; });
  var values = distribution.map(function(d) { return d.trip_count; });

  if (_fareDistChart) { _fareDistChart.destroy(); _fareDistChart = null; }

  _fareDistChart = createBarChart(
    document.getElementById("fare-dist-canvas"),
    labels,
    values,
    ["#10F0A0", "#00D4FF", "#3B82F6", "#8B5CF6", "#FF9F43", "#FF5A7A"]
  );
}

document.addEventListener("DOMContentLoaded", initDashboard);
