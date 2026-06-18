let boroughChart;
let serviceChart;
let fareChart;

const chartColors = ["#FA8112", "#222222", "#c96a12", "#8e5d2a", "#d9b36f", "#7a705e"];

function renderCharts(metrics) {
  renderBoroughChart(metrics.boroughs);
  renderServiceChart(metrics.service_zones);
  renderFareChart(metrics.fare_distribution);
  renderTopZoneList(metrics.top_zones);
}

function renderBoroughChart(rows) {
  const labels = rows.map(row => row.borough);
  const tripCounts = rows.map(row => row.total_trips);
  const revenue = rows.map(row => row.total_revenue);

  if (boroughChart) {
    boroughChart.destroy();
  }

  boroughChart = new Chart(document.getElementById("boroughChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Trips",
          data: tripCounts,
          backgroundColor: "#FA8112",
          borderRadius: 4,
        },
        {
          label: "Revenue",
          data: revenue,
          backgroundColor: "#222222",
          borderRadius: 4,
        },
      ],
    },
    options: baseChartOptions({
      yTick: value => formatShortNumber(value),
    }),
  });
}

function renderServiceChart(rows) {
  if (serviceChart) {
    serviceChart.destroy();
  }

  serviceChart = new Chart(document.getElementById("serviceChart"), {
    type: "doughnut",
    data: {
      labels: rows.map(row => row.service_zone),
      datasets: [{
        data: rows.map(row => row.total_trips),
        backgroundColor: chartColors,
        borderColor: "#fffaf0",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#222222",
            boxWidth: 12,
          },
        },
      },
    },
  });
}

function renderFareChart(rows) {
  if (fareChart) {
    fareChart.destroy();
  }

  fareChart = new Chart(document.getElementById("fareChart"), {
    type: "bar",
    data: {
      labels: rows.map(row => "$" + row.range),
      datasets: [{
        label: "Trips",
        data: rows.map(row => row.trip_count),
        backgroundColor: "#222222",
        borderRadius: 4,
      }],
    },
    options: baseChartOptions({
      yTick: value => formatShortNumber(value),
    }),
  });
}

function renderTopZoneList(rows) {
  const list = document.getElementById("topZoneList");
  list.innerHTML = "";

  rows.forEach(function (zone, index) {
    const item = document.createElement("div");
    item.className = "top-zone-row";
    item.innerHTML = `
      <span class="rank">${index + 1}</span>
      <div>
        <strong>${zone.zone_name}</strong>
        <small>${zone.borough}</small>
      </div>
      <span>${formatNumber(zone.trip_count)}</span>
      <span>${formatMoney(zone.total_revenue)}</span>
    `;
    list.appendChild(item);
  });
}

function baseChartOptions(settings) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#222222",
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#716858" },
      },
      y: {
        grid: { color: "#ead9b7" },
        ticks: {
          color: "#716858",
          callback: settings.yTick,
        },
      },
    },
  };
}

function formatShortNumber(value) {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + "M";
  }

  if (value >= 1000) {
    return (value / 1000).toFixed(0) + "K";
  }

  return value;
}
