async function initMobilityPage() {
  injectSidebar("mobility");
  injectNavbar();
  setNavbarTitle("Mobility Analytics");

  await Promise.allSettled([
    loadTopPickupZones(),
    loadTopDropoffZones(),
    loadBoroughComparison(),
    loadAverageDistance(),
  ]);
}

async function loadTopPickupZones() {
  try {
    var data  = await fetchTopPickupZones(10);
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

async function loadTopDropoffZones() {
  var data = await fetchTopDropoffZones(10);   // returns null if 404

  if (!data) {
    showChartComingSoon("mob-dropoff-container", "Top Dropoff Zones");
    return;
  }

  var zones = data.zones || [];
  if (zones.length === 0) {
    showChartComingSoon("mob-dropoff-container", "Top Dropoff Zones");
    return;
  }

  var container = document.getElementById("mob-dropoff-container");
  if (container) container.innerHTML = '<canvas id="mob-dropoff-canvas"></canvas>';

  createHorizontalBarChart(
    document.getElementById("mob-dropoff-canvas"),
    zones.map(function(z) { return z.zone_name || ("Zone " + z.zone_id); }),
    zones.map(function(z) { return z.trip_count; }),
    zones.map(function(z) { return boroughColor(z.borough); })
  );
}

async function loadBoroughComparison() {
  try {
    var data     = await fetchRevenueByBorough();
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

async function loadAverageDistance() {
  var data = await fetchAverageDistanceByHour();   // returns null if 404

  if (!data) {
    showChartComingSoon("mob-distance-container", "Average Distance by Hour");
    // Populate the fare range KPI with fare distribution data as fallback
    _loadFareRangeKpi();
    return;
  }

  var hours = data.hours || [];
  if (hours.length === 0) {
    showChartComingSoon("mob-distance-container", "Average Distance by Hour");
    return;
  }

  var container = document.getElementById("mob-distance-container");
  if (container) container.innerHTML = '<canvas id="mob-distance-canvas"></canvas>';

  createLineChart(
    document.getElementById("mob-distance-canvas"),
    hours.map(function(h) { return h.hour + ":00"; }),
    hours.map(function(h) { return h.avg_distance; }),
    "#00D4FF",
    true
  );
}

async function _loadFareRangeKpi() {
  try {
    var data = await fetchFareDistribution();
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

document.addEventListener("DOMContentLoaded", initMobilityPage);
