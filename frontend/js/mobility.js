async function initMobilityPage() {
  injectSidebar("mobility");
  injectNavbar();
  setNavbarTitle("Mobility Analytics");

  var results = await Promise.allSettled([
    fetchTopPickupZones(10),
    fetchTopDropoffZones(10),
    fetchRevenueByBorough(),
    fetchAverageDistanceByHour(),
    fetchFareDistribution(),
  ]);

  loadTopPickupZones(_mobilityResult(results[0]));
  loadTopDropoffZones(_mobilityResult(results[1]));
  loadBoroughComparison(_mobilityResult(results[2]));
  loadAverageDistance(_mobilityResult(results[3]));
  _loadFareRangeKpi(_mobilityResult(results[4]));
  showApp();
}

function loadTopPickupZones(data) {
  try {
    if (!data) throw new Error("Top pickup zones request failed");
    var zones = data.zones || [];

    if (zones.length === 0) {
      showChartError("mob-pickup-container", "No pickup zone data returned.");
      return;
    }

    // Populate KPI cards
    var top = zones[0];
    _set("mob-top-zone",      top.zone_name || ("Zone " + top.zone_id));
    _set("mob-top-zone-meta", formatNumber(top.trip_count) + " trips");
    _set("mob-top-borough",   top.borough || "—");
    _set("mob-zone-count",    String(zones.length));

    var container = document.getElementById("mob-pickup-container");
    if (container) container.innerHTML = '<canvas id="mob-pickup-canvas"></canvas>';

    createHorizontalBarChart(
      document.getElementById("mob-pickup-canvas"),
      zones.map(function(z) { return z.zone_name || ("Zone " + z.zone_id); }),
      zones.map(function(z) { return z.trip_count; }),
      zones.map(function(z) { return boroughColor(z.borough); }),
      function(ctx) {
        return "Borough: " + (zones[ctx.dataIndex].borough || "Unknown");
      }
    );

  } catch (err) {
    showChartError("mob-pickup-container", "Could not load pickup zones.");
    console.error("loadTopPickupZones:", err);
  }
}

function loadTopDropoffZones(data) {
  if (!data) {
    showChartComingSoon("mob-dropoff-container", "Top Dropoff Zones");
    return;
  }

  var zones = data.zones || [];
  if (zones.length === 0) {
    showChartComingSoon("mob-dropoff-container", "Top Dropoff Zones");
    return;
  }

  try {
    var container = document.getElementById("mob-dropoff-container");
    if (container) container.innerHTML = '<canvas id="mob-dropoff-canvas"></canvas>';

    createHorizontalBarChart(
      document.getElementById("mob-dropoff-canvas"),
      zones.map(function(z) { return z.zone_name || ("Zone " + z.zone_id); }),
      zones.map(function(z) { return z.trip_count; }),
      zones.map(function(z) { return boroughColor(z.borough); })
    );
  } catch (err) {
    showChartError("mob-dropoff-container", "Could not render Top Dropoff Zones.");
    console.error("loadTopDropoffZones render:", err);
  }
}

function loadBoroughComparison(data) {
  try {
    if (!data) throw new Error("Borough comparison request failed");
    var boroughs = data.boroughs;

    var container = document.getElementById("mob-borough-container");
    if (container) container.innerHTML = '<canvas id="mob-borough-canvas"></canvas>';

    createBarChart(
      document.getElementById("mob-borough-canvas"),
      boroughs.map(function(b) { return b.borough; }),
      boroughs.map(function(b) { return b.total_trips; }),
      boroughs.map(function(b) { return boroughColor(b.borough); })
    );

  } catch (err) {
    showChartError("mob-borough-container", "Could not load borough data.");
    console.error("loadBoroughComparison:", err);
  }
}

function loadAverageDistance(data) {
  if (!data) {
    showChartComingSoon("mob-distance-container", "Average Distance by Hour");
    return;
  }

  var hours = data.distances || [];
  if (hours.length === 0) {
    showChartComingSoon("mob-distance-container", "Average Distance by Hour");
    return;
  }

  try {
    var container = document.getElementById("mob-distance-container");
    if (container) container.innerHTML = '<canvas id="mob-distance-canvas"></canvas>';

    createLineChart(
      document.getElementById("mob-distance-canvas"),
      hours.map(function(h) { return h.hour + ":00"; }),
      hours.map(function(h) { return h.avg_distance; }),
      "#00D4FF",
      true
    );
  } catch (err) {
    showChartError("mob-distance-container", "Could not render Average Distance chart.");
    console.error("loadAverageDistance render:", err);
  }
}

function _loadFareRangeKpi(data) {
  try {
    if (!data || !data.distribution) return;
    var busiest = data.distribution.reduce(function(max, r) {
      return r.trip_count > max.trip_count ? r : max;
    }, data.distribution[0]);
    _set("mob-busiest-range", "$" + busiest.range);
  } catch (_) {}
}

function _set(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}

function _mobilityResult(result) {
  return result && result.status === "fulfilled" ? result.value : null;
}

document.addEventListener("DOMContentLoaded", initMobilityPage);
