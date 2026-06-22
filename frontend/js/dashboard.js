// Dashboard page controller.
// Requires: api.js, charts.js, cards.js, navbar.js, sidebar.js

var _topZonesChart = null;
var _fareDistChart = null;
var _dashboardRequestId = 0;
var _dashboardFilters = { borough: "", pickupDate: "" };
var _dashboardFilterStorageKey = "urbanMobility.dashboardFilters";

async function initDashboard() {
  var dashboardHost = document.getElementById("stats-cards");
  if (!dashboardHost || dashboardHost.dataset.dashboardInitialized === "true") return;
  dashboardHost.dataset.dashboardInitialized = "true";

  injectSidebar("dashboard");
  injectNavbar();
  setNavbarTitle("Dashboard");
  _dashboardFilters = _restoreDashboardFilters();
  _setupDashboardFilters();
  await Promise.allSettled([
    _loadDashboardFilterOptions(),
    loadDashboardData(_dashboardFilters),
  ]);
  showApp();
}

function _setupDashboardFilters() {
  var borough = document.getElementById("dashboard-borough-filter");
  var pickupDate = document.getElementById("dashboard-date-filter");
  var reset = document.getElementById("dashboard-filter-reset");
  if (!borough || !pickupDate || !reset) return;

  borough.value = _dashboardFilters.borough;
  pickupDate.value = _dashboardFilters.pickupDate;

  function applyFilters() {
    _dashboardFilters = {
      borough: borough.value,
      pickupDate: pickupDate.value,
    };
    _persistDashboardFilters();
    _updateDashboardFilterState();
    loadDashboardData(_dashboardFilters);
  }

  borough.addEventListener("change", applyFilters);
  pickupDate.addEventListener("change", applyFilters);
  reset.addEventListener("click", function() {
    borough.value = "";
    pickupDate.value = "";
    applyFilters();
  });
  _updateDashboardFilterState();
}

function _restoreDashboardFilters() {
  var params = new URLSearchParams(window.location.search);
  var hasUrlState = params.has("borough") || params.has("pickup_date");
  if (hasUrlState) {
    return {
      borough: params.get("borough") || "",
      pickupDate: params.get("pickup_date") || "",
    };
  }

  try {
    var saved = JSON.parse(sessionStorage.getItem(_dashboardFilterStorageKey));
    if (saved && typeof saved === "object") {
      return {
        borough: typeof saved.borough === "string" ? saved.borough : "",
        pickupDate: typeof saved.pickupDate === "string" ? saved.pickupDate : "",
      };
    }
  } catch (_) {}

  return { borough: "", pickupDate: "" };
}

function _persistDashboardFilters() {
  var active = Boolean(_dashboardFilters.borough || _dashboardFilters.pickupDate);
  try {
    if (active) {
      sessionStorage.setItem(
        _dashboardFilterStorageKey,
        JSON.stringify(_dashboardFilters)
      );
    } else {
      sessionStorage.removeItem(_dashboardFilterStorageKey);
    }
  } catch (_) {}

  var url = new URL(window.location.href);
  if (_dashboardFilters.borough) {
    url.searchParams.set("borough", _dashboardFilters.borough);
  } else {
    url.searchParams.delete("borough");
  }
  if (_dashboardFilters.pickupDate) {
    url.searchParams.set("pickup_date", _dashboardFilters.pickupDate);
  } else {
    url.searchParams.delete("pickup_date");
  }

  if (typeof replaceCurrentPageUrl === "function") {
    replaceCurrentPageUrl(url.href);
  } else {
    history.replaceState({}, "", url.href);
  }
}

async function _loadDashboardFilterOptions() {
  try {
    var options = await fetchDashboardFilterOptions();
    var borough = document.getElementById("dashboard-borough-filter");
    var pickupDate = document.getElementById("dashboard-date-filter");
    if (!borough || !pickupDate) return;

    (options.boroughs || []).forEach(function(value) {
      borough.add(new Option(value, value));
    });
    (options.pickup_dates || []).forEach(function(value) {
      var label = new Date(value + "T00:00:00").toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric",
      });
      pickupDate.add(new Option(label, value));
    });

    borough.value = _dashboardFilters.borough;
    pickupDate.value = _dashboardFilters.pickupDate;
  } catch (error) {
    console.error("Dashboard filter options:", error);
    var status = document.getElementById("dashboard-filter-status");
    if (status) status.textContent = "Filters unavailable";
  }
}

function _updateDashboardFilterState(isLoading) {
  var reset = document.getElementById("dashboard-filter-reset");
  var status = document.getElementById("dashboard-filter-status");
  var active = Boolean(_dashboardFilters.borough || _dashboardFilters.pickupDate);
  if (reset) reset.disabled = !active;
  if (!status) return;

  if (isLoading) {
    status.textContent = "Updating dashboard...";
    return;
  }

  var parts = [];
  if (_dashboardFilters.borough) parts.push(_dashboardFilters.borough + " pickups");
  if (_dashboardFilters.pickupDate) parts.push(_dashboardFilters.pickupDate);
  status.textContent = parts.length ? parts.join(" · ") : "All January 2019 trips";
}

async function loadDashboardData(filters) {
  var requestId = ++_dashboardRequestId;
  _updateDashboardFilterState(true);
  showCardsLoading();
  showChartLoading("zones-chart-container", "Loading top pickup zonesâ€¦");
  showChartLoading("fare-chart-container", "Loading fare distributionâ€¦");

  var results = await Promise.allSettled([
    fetchSummary(filters),
    fetchTopPickupZones(10, filters),
    fetchFareDistribution(filters),
  ]);

  // A newer selection won while this request was in flight.
  if (requestId !== _dashboardRequestId) return;

  var summary = results[0].status === "fulfilled" ? results[0].value : null;
  var zones = results[1].status === "fulfilled" ? results[1].value : null;
  var fareDist = results[2].status === "fulfilled" ? results[2].value : null;

  if (summary) {
    renderCards(summary);
    if (typeof _renderSummaryTable === "function") _renderSummaryTable(summary);
  } else {
    showCardsError();
  }

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
  _updateDashboardFilterState(false);
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
