// Dashboard page controller.
// Requires: api.js, charts.js, cards.js, navbar.js, sidebar.js, filters.js

var _topZonesChart = null;
var _fareDistChart = null;

async function initDashboard() {
  injectSidebar("dashboard");
  injectNavbar();
  setNavbarTitle("Dashboard");
  injectFilters();
  setupFilterHandlers(function(filters) { loadDashboardData(filters); });
  await loadDashboardData({});
}

async function loadDashboardData(filters) {
  showCardsLoading();
  showChartLoading("zones-chart-container", "Loading top pickup zones…");
  showChartLoading("fare-chart-container",  "Loading fare distribution…");

  var results = await Promise.allSettled([
    fetchDashboardStats(filters),
    fetchTopPickupZones(10),
    fetchFareDistribution(),
  ]);

  var stats    = results[0].status === "fulfilled" ? results[0].value : null;
  var zonesData = results[1].status === "fulfilled" ? results[1].value : null;
  var fareData  = results[2].status === "fulfilled" ? results[2].value : null;

  if (stats) {
    renderCards(stats);
  } else {
    showCardsError();
  }

  if (zonesData && zonesData.zones && zonesData.zones.length > 0) {
    _renderTopZones(zonesData.zones);
  } else {
    showChartError("zones-chart-container", "Could not load pickup zones. Is the backend running?");
  }

  if (fareData && fareData.distribution && fareData.distribution.length > 0) {
    _renderFareDist(fareData.distribution);
  } else {
    showChartError("fare-chart-container", "Could not load fare data. Is the backend running?");
  }
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
