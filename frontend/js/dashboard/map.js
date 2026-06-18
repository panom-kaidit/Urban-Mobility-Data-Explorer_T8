let nycMap;
let taxiZoneLayer;
let taxiZoneData;
let selectedMetric = "trip_count";

const mapMetricText = {
  trip_count: "pickups",
  total_revenue: "revenue",
  avg_fare: "average fare",
  avg_distance: "average distance",
};

function renderMap(zoneGeoJson) {
  taxiZoneData = zoneGeoJson;

  nycMap = L.map("nycMap", {
    zoomControl: true,
    scrollWheelZoom: true,
  }).setView([40.72, -73.94], 10);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(nycMap);

  taxiZoneLayer = L.geoJSON(taxiZoneData, {
    style: getZoneStyle,
    onEachFeature: function (feature, layer) {
      layer.on({
        mouseover: function () {
          layer.setStyle({ color: "#222222", weight: 2 });
        },
        mouseout: function () {
          taxiZoneLayer.resetStyle(layer);
        },
        click: function () {
          showZoneInfo(feature.properties);
        },
      });
    },
  }).addTo(nycMap);

  nycMap.fitBounds(taxiZoneLayer.getBounds(), { padding: [18, 18] });
}

function changeMapMetric(metricName) {
  selectedMetric = metricName;

  if (taxiZoneLayer) {
    taxiZoneLayer.setStyle(getZoneStyle);
  }
}

function getZoneStyle(feature) {
  const value = Number(feature.properties[selectedMetric] || 0);
  const maxValue = getMaxZoneValue(selectedMetric);

  return {
    color: "#F5E7C6",
    weight: 1,
    fillColor: getMapColor(value / maxValue),
    fillOpacity: 0.8,
  };
}

function getMaxZoneValue(metricName) {
  let maxValue = 0;

  taxiZoneData.features.forEach(function (feature) {
    const value = Number(feature.properties[metricName] || 0);
    if (value > maxValue) {
      maxValue = value;
    }
  });

  return maxValue || 1;
}

function getMapColor(percent) {
  if (percent > 0.75) return "#FA8112";
  if (percent > 0.5) return "#f49a3b";
  if (percent > 0.25) return "#efbc76";
  if (percent > 0.08) return "#F5E7C6";
  return "#FAF3E1";
}

function showZoneInfo(zone) {
  document.getElementById("zoneName").textContent = zone.zone || "--";
  document.getElementById("zoneBorough").textContent = zone.borough || "--";
  document.getElementById("zoneTrips").textContent = formatNumber(zone.trip_count);
  document.getElementById("zoneRevenue").textContent = formatMoney(zone.total_revenue);
  document.getElementById("zoneDistance").textContent = formatDecimal(zone.avg_distance, 2) + " mi";
  document.getElementById("zoneSummary").textContent =
    zone.zone + " shows " + formatMetric(zone[selectedMetric], selectedMetric) +
    " by " + mapMetricText[selectedMetric] + ".";
}
