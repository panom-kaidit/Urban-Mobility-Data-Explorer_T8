let dashboardMetrics;
let dashboardZones;

document.addEventListener("DOMContentLoaded", initDashboard);

async function initDashboard() {
  setStatus("Loading");

  try {
    const data = await getDashboardData();
    dashboardMetrics = data.metrics;
    dashboardZones = data.zoneGeoJson;

    populateBoroughFilter(dashboardMetrics.boroughs);
    renderDashboard("all");
    renderMap(dashboardZones);
    selectFirstZone(dashboardZones);
    bindControls();

    setStatus("Ready");
  } catch {
    setStatus("Unavailable", true);
  }
}

function renderDashboard(borough) {
  const viewMetrics = getMetricsForBorough(borough);

  renderSummary(viewMetrics.summary);
  renderCharts(viewMetrics);
  setText("dataset-label", formatNumber(viewMetrics.summary.total_trips) + " trips");
}

function renderSummary(summary) {
  setText("total-trips", formatNumber(summary.total_trips));
  setText("total-revenue", formatMoney(summary.total_revenue));
  setText("average-fare", formatMoney(summary.avg_fare));

  if (summary.top_borough) {
    setText("top-borough", summary.top_borough.borough);
  } else {
    setText("top-borough", "--");
  }
}

function populateBoroughFilter(rows) {
  const select = document.getElementById("borough-filter");

  if (!select) {
    return;
  }

  rows.forEach(function (row) {
    const option = document.createElement("option");
    option.value = row.borough;
    option.textContent = row.borough;
    select.appendChild(option);
  });
}

function bindControls() {
  const boroughFilter = document.getElementById("borough-filter");
  const mapMetricFilter = document.getElementById("map-metric-filter");
  const resetButton = document.getElementById("reset-view");
  const exportButton = document.getElementById("export-view");
  const metricButtons = document.querySelectorAll("[data-map-metric]");

  if (boroughFilter) {
    boroughFilter.addEventListener("change", function (event) {
      const borough = event.target.value;
      renderDashboard(borough);
      setMapBorough(borough);
      selectFirstZone(getVisibleZoneData());
    });
  }

  if (mapMetricFilter) {
    mapMetricFilter.addEventListener("change", function (event) {
      updateMapMetric(event.target.value);
    });
  }

  metricButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      updateMapMetric(button.dataset.mapMetric);
    });
  });

  if (resetButton) {
    resetButton.addEventListener("click", function () {
      if (boroughFilter) {
        boroughFilter.value = "all";
      }

      if (mapMetricFilter) {
        mapMetricFilter.value = "trip_count";
      }

      setActiveMetricButton("trip_count");
      renderDashboard("all");
      resetMapView();
      selectFirstZone(dashboardZones);
      setStatus("Ready");
    });
  }

  if (exportButton) {
    exportButton.addEventListener("click", function () {
      exportTopZones();
    });
  }
}

function updateMapMetric(metricName) {
  const mapMetricFilter = document.getElementById("map-metric-filter");

  if (mapMetricFilter) {
    mapMetricFilter.value = metricName;
  }

  setMapMetric(metricName);
  setActiveMetricButton(metricName);
}

function setActiveMetricButton(metricName) {
  const buttons = document.querySelectorAll("[data-map-metric]");

  buttons.forEach(function (button) {
    button.classList.toggle("active", button.dataset.mapMetric === metricName);
  });
}

function getMetricsForBorough(borough) {
  if (borough === "all") {
    return dashboardMetrics;
  }

  const boroughRow = dashboardMetrics.boroughs.find(function (row) {
    return row.borough === borough;
  });

  const zoneFeatures = dashboardZones.features.filter(function (feature) {
    return feature.properties.borough === borough;
  });

  return {
    summary: buildBoroughSummary(borough, boroughRow, zoneFeatures),
    boroughs: boroughRow ? [boroughRow] : [],
    service_zones: buildServiceZonesFromFeatures(zoneFeatures),
    top_zones: buildTopZonesFromFeatures(zoneFeatures),
    fare_distribution: dashboardMetrics.fare_distribution,
  };
}

function buildBoroughSummary(borough, boroughRow, zoneFeatures) {
  const totals = zoneFeatures.reduce(function (result, feature) {
    const zone = feature.properties;
    const trips = Number(zone.trip_count || 0);

    result.active_zones += 1;
    result.total_trips += trips;
    result.total_revenue += Number(zone.total_revenue || 0);
    result.distance_weight += Number(zone.avg_distance || 0) * trips;

    return result;
  }, {
    active_zones: 0,
    total_trips: 0,
    total_revenue: 0,
    distance_weight: 0,
  });

  const totalTrips = boroughRow ? boroughRow.total_trips : totals.total_trips;
  const totalRevenue = boroughRow ? boroughRow.total_revenue : totals.total_revenue;

  return {
    total_trips: totalTrips,
    total_revenue: totalRevenue,
    avg_fare: boroughRow ? boroughRow.avg_fare : totalRevenue / Math.max(totalTrips, 1),
    avg_distance: totals.distance_weight / Math.max(totals.total_trips, 1),
    active_zones: totals.active_zones,
    top_borough: {
      borough: borough,
      trip_count: totalTrips,
    },
  };
}

function buildServiceZonesFromFeatures(features) {
  const grouped = {};

  features.forEach(function (feature) {
    const zone = feature.properties;
    const key = zone.service_zone || "Unknown";

    if (!grouped[key]) {
      grouped[key] = {
        service_zone: key,
        total_trips: 0,
        total_revenue: 0,
      };
    }

    grouped[key].total_trips += Number(zone.trip_count || 0);
    grouped[key].total_revenue += Number(zone.total_revenue || 0);
  });

  return Object.values(grouped).sort(function (a, b) {
    return b.total_trips - a.total_trips;
  });
}

function buildTopZonesFromFeatures(features) {
  return features
    .map(function (feature) {
      const zone = feature.properties;

      return {
        zone_id: zone.location_id,
        zone_name: zone.zone,
        borough: zone.borough,
        trip_count: Number(zone.trip_count || 0),
        total_revenue: Number(zone.total_revenue || 0),
        avg_fare: Number(zone.avg_fare || 0),
        avg_distance: Number(zone.avg_distance || 0),
      };
    })
    .sort(function (a, b) {
      return b.trip_count - a.trip_count;
    })
    .slice(0, 8);
}

function selectFirstZone(zoneGeoJson) {
  if (!zoneGeoJson || !zoneGeoJson.features.length) {
    showZoneInfo({});
    return;
  }

  showZoneInfo(zoneGeoJson.features[0].properties);
}

function exportTopZones() {
  const boroughFilter = document.getElementById("borough-filter");
  const borough = boroughFilter ? boroughFilter.value : "all";
  const rows = getMetricsForBorough(borough).top_zones;
  const header = "zone,borough,trips,revenue";
  const lines = rows.map(function (row) {
    return [
      csvValue(row.zone_name),
      csvValue(row.borough),
      row.trip_count,
      row.total_revenue,
    ].join(",");
  });

  const csv = [header].concat(lines).join("\n");
  const blob = new Blob([csv], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "top-pickup-zones.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function csvValue(value) {
  return '"' + String(value || "").replaceAll('"', '""') + '"';
}

function setStatus(message, isError) {
  const status = document.getElementById("load-status");

  if (!status) {
    return;
  }

  status.textContent = message;
  status.classList.toggle("error", Boolean(isError));
}

function setText(elementId, value) {
  const element = document.getElementById(elementId);

  if (element) {
    element.textContent = value;
  }
}
