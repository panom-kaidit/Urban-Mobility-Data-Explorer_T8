let nycMap;
let taxiZoneLayer;
let taxiZoneData;
let selectedMetric = "trip_count";
let selectedBorough = "all";

const mapMetricLabels = {
  trip_count: "Pickup volume",
  total_revenue: "Total revenue",
  avg_fare: "Average fare",
  avg_distance: "Average distance",
};

function renderMap(zoneGeoJson) {
  taxiZoneData = zoneGeoJson;

  nycMap = L.map("nyc-map", {
    zoomControl: true,
    scrollWheelZoom: true,
  }).setView([40.72, -73.94], 10);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(nycMap);

  drawZoneLayer();
}

function drawZoneLayer() {
  const visibleData = getVisibleZoneData();

  if (taxiZoneLayer) {
    taxiZoneLayer.remove();
  }

  taxiZoneLayer = L.geoJSON(visibleData, {
    style: getZoneStyle,
    onEachFeature: function (feature, layer) {
      layer.bindPopup(getPopupHtml(feature.properties));

      layer.on({
        mouseover: function () {
          layer.setStyle({
            color: "#251f2a",
            weight: 2,
          });
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

  if (taxiZoneLayer.getBounds().isValid()) {
    nycMap.fitBounds(taxiZoneLayer.getBounds(), {
      padding: [18, 18],
    });
  }
}

function setMapMetric(metricName) {
  selectedMetric = metricName;

  if (taxiZoneLayer) {
    taxiZoneLayer.eachLayer(function (layer) {
      layer.setStyle(getZoneStyle(layer.feature));
      layer.setPopupContent(getPopupHtml(layer.feature.properties));
    });
  }
}

function setMapBorough(borough) {
  selectedBorough = borough;
  drawZoneLayer();
}

function resetMapView() {
  selectedBorough = "all";
  selectedMetric = "trip_count";
  drawZoneLayer();
}

function getVisibleZoneData() {
  if (!taxiZoneData || selectedBorough === "all") {
    return taxiZoneData;
  }

  return {
    type: "FeatureCollection",
    features: taxiZoneData.features.filter(function (feature) {
      return feature.properties.borough === selectedBorough;
    }),
  };
}

function getZoneStyle(feature) {
  const value = Number(feature.properties[selectedMetric] || 0);
  const maxValue = getMaxZoneValue(selectedMetric);

  return {
    color: "#fff8ed",
    weight: 1,
    fillColor: getMapColor(value / maxValue),
    fillOpacity: 0.82,
  };
}

function getMaxZoneValue(metricName) {
  const visibleData = getVisibleZoneData();
  let maxValue = 0;

  visibleData.features.forEach(function (feature) {
    const value = Number(feature.properties[metricName] || 0);

    if (value > maxValue) {
      maxValue = value;
    }
  });

  return maxValue || 1;
}

function getMapColor(percent) {
  if (percent > 0.75) return "#574964";
  if (percent > 0.5) return "#7D6374";
  if (percent > 0.25) return "#9F8383";
  if (percent > 0.08) return "#C8AAAA";
  return "#F2DDD0";
}

function getPopupHtml(zone) {
  return (
    '<div class="zone-popup">' +
    "<strong>" + escapeHtml(zone.zone || "--") + "</strong>" +
    "<span>" + escapeHtml(zone.borough || "--") + "</span>" +
    "<span>" + escapeHtml(mapMetricLabels[selectedMetric]) + ": " +
    formatMetric(zone[selectedMetric], selectedMetric) + "</span>" +
    "</div>"
  );
}

function showZoneInfo(zone) {
  document.getElementById("selected-zone").textContent = zone.zone || "--";
  document.getElementById("selected-borough").textContent = zone.borough || "--";
  document.getElementById("selected-trips").textContent = formatNumber(zone.trip_count);
  document.getElementById("selected-revenue").textContent = formatMoney(zone.total_revenue);
  document.getElementById("selected-distance").textContent = formatDecimal(zone.avg_distance, 2) + " mi";
}
