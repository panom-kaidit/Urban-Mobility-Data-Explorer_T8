// Zone intelligence page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js, Leaflet

var _map = null;

async function initZonesPage() {
  injectSidebar("zones");
  injectNavbar();
  setNavbarTitle("Zone Intelligence");

  await loadZoneIntelligence();
}

async function loadZoneIntelligence() {
  try {
    var data  = await fetchTopPickupZones(15);
    var zones = data.zones || [];
    if (zones.length === 0) {
      showChartError("zone-bar-container", "No zone data returned.");
      return;
    }

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
    _initMap(zones.slice(0, 10));

  } catch (err) {
    showChartError("zone-bar-container", "Could not load zone data. Is the backend running?");
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

function _initMap(zones) {
  if (typeof L === "undefined") {
    var mapEl = document.getElementById("zone-map");
    if (mapEl) mapEl.innerHTML = '<div class="coming-soon"><div class="coming-soon-icon">&#x1F5FA;</div><div>Leaflet failed to load.</div></div>';
    return;
  }

  // Init Leaflet map centered on NYC
  _map = L.map("zone-map", { zoomControl: true }).setView([40.73, -73.94], 11);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(_map);

  // Fetch GeoJSON for each of the top 10 zones in parallel and overlay
  var colorScale = ["#FF5A7A","#FF9F43","#FCCC0A","#10F0A0","#00D4FF",
                    "#3B82F6","#8B5CF6","#B933AD","#FF6319","#00933C"];

  var maxTrips = zones[0].trip_count;

  var promises = zones.map(function(z, i) {
    return fetchZone(z.zone_id)
      .then(function(detail) {
        if (!detail || !detail.geometry) return;
        var geo;
        try { geo = JSON.parse(detail.geometry); } catch (_) { return; }

        var fillOpacity = 0.25 + 0.45 * (z.trip_count / maxTrips);
        var color       = colorScale[i % colorScale.length];

        L.geoJSON(geo, {
          style: {
            fillColor:   color,
            fillOpacity: fillOpacity,
            color:       color,
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
      })
      .catch(function() {});
  });

  Promise.all(promises).then(function() {
    // Add legend
    var legend = L.control({ position: "bottomright" });
    legend.onAdd = function() {
      var div = L.DomUtil.create("div");
      div.style.cssText = "background:rgba(11,20,71,0.92);border:1px solid rgba(0,212,255,0.2);padding:8px 12px;border-radius:8px;font-size:11px;color:#8B9BB4;";
      div.innerHTML = "<strong style='color:#E2E8F0'>Top Pickup Zones</strong><br>Darker = more trips";
      return div;
    };
    legend.addTo(_map);
  });
}

document.addEventListener("DOMContentLoaded", initZonesPage);
