// Zone intelligence page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js, Leaflet

var _map = null;

async function initZonesPage() {
  injectSidebar("zones");
  injectNavbar();
  setNavbarTitle("Zone Intelligence");

  await loadZoneIntelligence();
  showApp();
}

async function loadZoneIntelligence() {
  try {
    var data  = await fetchTopPickupZones(15);
    var zones = data.zones || [];
    if (zones.length === 0) {
      showChartError("zone-bar-container", "No zone data available.");
      return;
    }

    var mapZones = zones.slice(0, 10);
    var zoneDetails = await Promise.all(mapZones.map(function(z) {
      return fetchZone(z.zone_id).catch(function() { return null; });
    }));

    // KPI cards
    var top = zones[0];
    var el1 = document.getElementById("zone-top-name");
    var el2 = document.getElementById("zone-top-trips");
    if (el1) el1.textContent = top.zone_name || ("Zone " + top.zone_id);
    if (el2) el2.textContent = formatNumber(top.trip_count) + " trips";

    // Ranking sidebar
    _renderRanking(zones.slice(0, 10));

    // Bar chart (top 15)
    var container = document.getElementById("zone-bar-container");
    if (container) container.innerHTML = '<canvas id="zone-bar-canvas"></canvas>';
    createHorizontalBarChart(
      document.getElementById("zone-bar-canvas"),
      zones.map(function(z) { return z.zone_name || ("Zone " + z.zone_id); }),
      zones.map(function(z) { return z.trip_count; }),
      zones.map(function(z) { return boroughColor(z.borough); }),
      function(ctx) {
        var z = zones[ctx.dataIndex];
        return z.borough || "";
      }
    );

    // Leaflet map — fetch GeoJSON for top 10 zones
    _initMap(mapZones, zoneDetails);

  } catch (err) {
    showChartError("zone-bar-container", "Zone data unavailable.");
    console.error("loadZoneIntelligence:", err);
  }
}

function _renderRanking(zones) {
  var list = document.getElementById("zone-ranking-list");
  if (!list) return;

  var html = "";
  zones.forEach(function(z, i) {
    var rank     = i + 1;
    var topCls   = rank <= 3 ? " top3" : "";
    var zoneName = (z.zone_name || ("Zone " + z.zone_id));
    if (zoneName.length > 26) zoneName = zoneName.slice(0, 24) + "…";

    html += (
      '<div class="zone-item">' +
        '<div class="zone-rank' + topCls + '">' + rank + '</div>' +
        '<div class="zone-info">' +
          '<div class="zone-name">' + zoneName + '</div>' +
          '<div class="zone-borough">' + (z.borough || "Unknown") + '</div>' +
        '</div>' +
        '<div class="zone-count">' + formatCompact(z.trip_count) + '</div>' +
      '</div>'
    );
  });
  list.innerHTML = html;
}

function _initMap(zones, zoneDetails) {
  if (typeof L === "undefined") {
    var mapEl = document.getElementById("zone-map");
    if (mapEl) mapEl.innerHTML = '<div class="coming-soon"><div class="coming-soon-icon">&#x1F5FA;</div><div>Map unavailable.</div></div>';
    return;
  }

  var mapEl = document.getElementById("zone-map");
  if (mapEl) mapEl.style.visibility = "hidden";

  // Init Leaflet map centered on NYC
  _map = L.map("zone-map", { zoomControl: true }).setView([40.73, -73.94], 11);

  var tiles = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  });

  // Fetch GeoJSON for each of the top 10 zones in parallel and overlay
  var maxTrips = zones[0].trip_count;
  var minTrips = zones[zones.length - 1].trip_count;
  var tripRange = Math.max(maxTrips - minTrips, 1);
  var zoneGreen = "#16A34A";

  zones.forEach(function(z, i) {
    var detail = zoneDetails[i];
    if (!detail || !detail.geometry) return;

    var geo;
    try { geo = JSON.parse(detail.geometry); } catch (_) { return; }

    var strength = (z.trip_count - minTrips) / tripRange;
    var fillOpacity = 0.22 + 0.63 * strength;

    L.geoJSON(geo, {
      style: {
        fillColor:   zoneGreen,
        fillOpacity: fillOpacity,
        color:       zoneGreen,
        weight:      1.5,
        opacity:     0.8,
      },
    })
    .bindTooltip(
      "<strong>" + (z.zone_name || "Zone " + z.zone_id) + "</strong><br>" +
      (z.borough || "") + "<br>" +
      "<em>" + formatNumber(z.trip_count) + " trips</em>",
      { sticky: true, className: "leaflet-dark-tip" }
    )
    .addTo(_map);
  });

  var legend = L.control({ position: "bottomright" });
  legend.onAdd = function() {
    var div = L.DomUtil.create("div");
    div.style.cssText = "background:rgba(255,255,255,0.94);border:1px solid #BBF7D0;padding:8px 12px;border-radius:8px;font-size:11px;color:#526174;";
    div.innerHTML = "<strong style='color:#166534'>Top Pickup Zones</strong><br>More green = more trips";
    return div;
  };
  legend.addTo(_map);

  function showMap() {
    if (mapEl) mapEl.style.visibility = "visible";
    _map.invalidateSize();
  }
  tiles.on("load", showMap);
  tiles.addTo(_map);
  setTimeout(showMap, 2000);
}

document.addEventListener("DOMContentLoaded", initZonesPage);
