let fareChart;
let serviceChart;

const chartColors = ["#574964", "#9F8383", "#C8AAAA", "#B8744F", "#6B8F71", "#445E78"];

function renderCharts(metrics) {
  renderFareChart(metrics.fare_distribution);
  renderServiceChart(metrics.service_zones);
  renderServiceZoneList(metrics.service_zones);
  renderTopZones(metrics.top_zones);
}

function renderFareChart(rows) {
  if (fareChart) {
    fareChart.destroy();
  }

  fareChart = new Chart(document.getElementById("fare-chart"), {
    type: "bar",
    data: {
      labels: rows.map(function (row) {
        return "$" + row.range;
      }),
      datasets: [
        {
          label: "Trips",
          data: rows.map(function (row) {
            return row.trip_count;
          }),
          backgroundColor: "#6B8F71",
          borderRadius: 5,
        },
      ],
    },
    options: singleAxisOptions(),
  });
}

function renderServiceChart(rows) {
  if (serviceChart) {
    serviceChart.destroy();
  }

  serviceChart = new Chart(document.getElementById("service-chart"), {
    type: "doughnut",
    data: {
      labels: rows.map(function (row) {
        return row.service_zone;
      }),
      datasets: [
        {
          data: rows.map(function (row) {
            return row.total_trips;
          }),
          backgroundColor: chartColors,
          borderColor: "#fff8ed",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return context.label + ": " + formatNumber(context.raw) + " trips";
            },
          },
        },
      },
    },
  });
}

function renderServiceZoneList(rows) {
  const list = document.getElementById("service-zone-list");
  list.innerHTML = "";

  rows.slice(0, 5).forEach(function (row, index) {
    const item = document.createElement("li");
    item.innerHTML =
      '<span style="background:' + chartColors[index % chartColors.length] + '"></span>' +
      escapeHtml(row.service_zone || "Unknown") +
      " - " +
      formatShortNumber(row.total_trips);
    list.appendChild(item);
  });
}

function renderTopZones(rows) {
  const list = document.getElementById("top-zone-list");
  list.innerHTML = "";

  rows.forEach(function (zone) {
    const item = document.createElement("div");
    item.className = "zone-row";
    item.innerHTML =
      "<span>" + escapeHtml(zone.zone_name || "--") + "</span>" +
      "<span>" + escapeHtml(zone.borough || "--") + "</span>" +
      "<span>" + formatShortNumber(zone.trip_count) + "</span>" +
      "<span>" + formatMoney(zone.total_revenue) + "</span>";
    list.appendChild(item);
  });
}

function singleAxisOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#251f2a",
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: "#6f6173",
        },
      },
      y: {
        beginAtZero: true,
        grid: {
          color: "rgba(87, 73, 100, 0.12)",
        },
        ticks: {
          color: "#6f6173",
          callback: formatShortNumber,
        },
      },
    },
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
