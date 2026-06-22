// Complete NYC taxi-zone revenue choropleth.
// Requires: api.js, charts.js, navbar.js, sidebar.js, Leaflet, Chart.js

var _zoneRevenueMap = null;
var _zoneRevenueChart = null;

async function initZonesPage() {
  injectSidebar("zones");
  injectNavbar();
  setNavbarTitle("Zone Intelligence");

  var heading = document.querySelector(".zone-map-header h2");
  if (heading) heading.textContent = "NYC Taxi Zone Revenue Map";
  var subtitle = document.querySelector(".chart-card-subtitle");
  if (subtitle) {
    subtitle.textContent = "Total amount collected from trips originating in each zone";
  }

  await loadZoneRevenueMap();
  showApp();
}

async function loadZoneRevenueMap() {
  try {
    var data = await fetchZoneMap();
    var zones = data.zones || [];
    if (!zones.length) throw new Error("No mapped zones available");

    var ranked = zones.slice().sort(function(a, b) {
      return Number(b.total_revenue) - Number(a.total_revenue);
    });
    var top = ranked[0];

    _setZoneText("zone-total-count", formatNumber(data.total_zones || zones.length));
    _setZoneText("zone-boundary-count", formatNumber(data.boundary_count || zones.length));
    _setZoneText("zone-borough-count", formatNumber(data.borough_count || 0));
    _setZoneText("zone-top-name", top.zone || ("Zone " + top.location_id));
    _setZoneText("zone-top-trips", formatCurrency(top.total_revenue) + " pickup revenue");

    _renderRevenueRanking(ranked.slice(0, 10));
    _renderRevenueChart(ranked.slice(0, 15));
    _renderCompleteZoneMap(zones);
  } catch (error) {
    console.error("loadZoneRevenueMap:", error);
    showChartError("zone-bar-container", "Zone revenue data unavailable.");
    var map = document.getElementById("zone-map");
    if (map) {
      map.innerHTML = '<div class="chart-placeholder"><span>Zone map unavailable.</span></div>';
    }
  }
}

function _setZoneText(id, value) {
  var element = document.getElementById(id);
  if (element) element.textContent = value;
}

function _renderRevenueRanking(zones) {
  var list = document.getElementById("zone-ranking-list");
  if (!list) return;

  list.innerHTML = zones.map(function(zone, index) {
    var rank = index + 1;
    return (
      '<div class="zone-item">' +
        '<div class="zone-rank' + (rank <= 3 ? " top3" : "") + '">' + rank + '</div>' +
        '<div class="zone-info">' +
          '<div class="zone-name">' + _escapeZoneText(zone.zone || ("Zone " + zone.location_id)) + '</div>' +
          '<div class="zone-borough">' + _escapeZoneText(zone.borough || "Unknown") +
            ' &middot; ' + formatCompact(zone.trip_count) + ' trips</div>' +
        '</div>' +
        '<div class="zone-count">' + formatCurrency(zone.total_revenue) + '</div>' +
      '</div>'
    );
  }).join("");
}

function _renderRevenueChart(zones) {
  var container = document.getElementById("zone-bar-container");
  if (!container || typeof Chart === "undefined") return;
  container.innerHTML = '<canvas id="zone-revenue-canvas"></canvas>';

  if (_zoneRevenueChart) _zoneRevenueChart.destroy();
  var maxRevenue = Math.max.apply(null, zones.map(function(zone) {
    return Number(zone.total_revenue) || 0;
  }));

  _zoneRevenueChart = new Chart(document.getElementById("zone-revenue-canvas"), {
    type: "bar",
    data: {
      labels: zones.map(function(zone) { return zone.zone || ("Zone " + zone.location_id); }),
      datasets: [{
        data: zones.map(function(zone) { return Number(zone.total_revenue) || 0; }),
        backgroundColor: zones.map(function(zone) {
          return _zoneRevenueColor(Number(zone.total_revenue) || 0, maxRevenue);
        }),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        tooltip: {
          callbacks: {
            label: function(context) { return " " + formatCurrency(context.raw); },
            afterLabel: function(context) {
              var zone = zones[context.dataIndex];
              return formatNumber(zone.trip_count) + " trips · " +
                "$" + Number(zone.average_revenue_per_trip).toFixed(2) + " per trip";
            },
          },
        },
      }),
      scales: darkScales({
        x: { ticks: { callback: function(value) { return "$" + formatCompact(value); } } },
        y: { grid: { display: false } },
      }),
    },
  });
}

function _renderCompleteZoneMap(zones) {
  var mapElement = document.getElementById("zone-map");
  if (!mapElement || typeof L === "undefined") return;
  mapElement.style.visibility = "hidden";

  if (_zoneRevenueMap) {
    _zoneRevenueMap.remove();
    _zoneRevenueMap = null;
  }
  _zoneRevenueMap = L.map("zone-map", { zoomControl: true });

  var tiles = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; CARTO',
      subdomains: "abcd",
      maxZoom: 19,
    }
  ).addTo(_zoneRevenueMap);

  var maxRevenue = Math.max.apply(null, zones.map(function(zone) {
    return Number(zone.total_revenue) || 0;
  }));
  var totalRevenue = zones.reduce(function(sum, zone) {
    return sum + (Number(zone.total_revenue) || 0);
  }, 0);

  var features = zones.map(function(zone) {
    return {
      type: "Feature",
      geometry: zone.geometry,
      properties: zone,
    };
  });

  var layerGroup;
  layerGroup = L.geoJSON({ type: "FeatureCollection", features: features }, {
    style: function(feature) {
      var revenue = Number(feature.properties.total_revenue) || 0;
      return {
        fillColor: _zoneRevenueColor(revenue, maxRevenue),
        fillOpacity: revenue > 0 ? 0.82 : 0.45,
        color: revenue > 0 ? "#166534" : "#94A3B8",
        weight: 0.8,
        opacity: 0.75,
      };
    },
    onEachFeature: function(feature, layer) {
      var zone = feature.properties;
      layer.bindTooltip(_zoneTooltip(zone, totalRevenue), {
        sticky: true,
        className: "zone-revenue-tooltip",
      });
      layer.on({
        mouseover: function(event) {
          event.target.setStyle({ weight: 3, color: "#14532D", fillOpacity: 0.95 });
          event.target.bringToFront();
        },
        mouseout: function(event) {
          layerGroup.resetStyle(event.target);
        },
      });
    },
  }).addTo(_zoneRevenueMap);

  var bounds = layerGroup.getBounds();
  if (bounds.isValid()) _zoneRevenueMap.fitBounds(bounds, { padding: [16, 16] });
  _addRevenueLegend(maxRevenue);

  function showMap() {
    mapElement.style.visibility = "visible";
    _zoneRevenueMap.invalidateSize();
  }
  tiles.on("load", showMap);
  setTimeout(showMap, 1200);
}

function _zoneRevenueColor(revenue, maxRevenue) {
  if (revenue <= 0 || maxRevenue <= 0) return "#E2E8F0";
  var strength = Math.log1p(revenue) / Math.log1p(maxRevenue);
  var lightness = 94 - (strength * 54);
  return "hsl(142, 58%, " + lightness.toFixed(1) + "%)";
}

function _zoneTooltip(zone, totalRevenue) {
  var revenue = Number(zone.total_revenue) || 0;
  var share = totalRevenue > 0 ? ((revenue / totalRevenue) * 100).toFixed(2) : "0.00";
  return (
    '<div class="zone-map-tooltip">' +
      '<strong>' + _escapeZoneText(zone.zone || ("Zone " + zone.location_id)) + '</strong>' +
      '<div class="zone-tooltip-borough">' + _escapeZoneText(zone.borough || "Unknown") +
        (zone.service_zone ? " · " + _escapeZoneText(zone.service_zone) : "") + '</div>' +
      '<div class="zone-tooltip-row"><span>Pickup revenue</span><span>' + formatCurrency(revenue) + '</span></div>' +
      '<div class="zone-tooltip-row"><span>Pickup trips</span><span>' + formatNumber(zone.trip_count) + '</span></div>' +
      '<div class="zone-tooltip-row"><span>Revenue / trip</span><span>$' +
        Number(zone.average_revenue_per_trip || 0).toFixed(2) + '</span></div>' +
      '<div class="zone-tooltip-row"><span>Revenue share</span><span>' + share + '%</span></div>' +
    '</div>'
  );
}

function _addRevenueLegend(maxRevenue) {
  var legend = L.control({ position: "bottomright" });
  legend.onAdd = function() {
    var div = L.DomUtil.create("div");
    div.style.cssText = "background:rgba(255,255,255,.96);border:1px solid #BBF7D0;padding:9px 11px;border-radius:8px;font-size:11px;color:#475569;box-shadow:0 4px 14px rgba(15,23,42,.12)";
    div.innerHTML =
      '<strong style="color:#14532D">Pickup revenue</strong>' +
      '<div style="width:150px;height:9px;margin:6px 0 3px;border-radius:5px;background:linear-gradient(90deg,#ECFDF5,#166534)"></div>' +
      '<div style="display:flex;justify-content:space-between"><span>$0</span><span>' +
        formatCurrency(maxRevenue) + '</span></div>';
    return div;
  };
  legend.addTo(_zoneRevenueMap);
}

function _escapeZoneText(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", initZonesPage);
