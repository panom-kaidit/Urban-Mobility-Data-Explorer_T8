// Borough color system — kept consistent across every chart on this page,
// drawn from NYC subway line colors so each borough has one fixed identity.
const BOROUGH_COLORS = {
  Manhattan:        "#FCCC0A",
  Brooklyn:         "#FF6319",
  Queens:           "#B933AD",
  Bronx:            "#00933C",
  "Staten Island":  "#9AA0AC",
  EWR:              "#4D7FE0",
};

function formatCurrency(value) {
  return "$" + Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-US");
}

async function loadRevenueByBorough() {
  const data = await fetchJSON("/analytics/revenue-by-borough");
  const boroughs = data.boroughs;

  const totalRevenue = boroughs.reduce((sum, b) => sum + b.total_revenue, 0);
  const totalTrips    = boroughs.reduce((sum, b) => sum + b.total_trips, 0);
  const avgFare        = totalRevenue / totalTrips;
  const topBorough     = boroughs[0];

  document.getElementById("kpi-total-revenue").textContent = formatCurrency(totalRevenue);
  document.getElementById("kpi-total-trips").textContent   = formatNumber(totalTrips);
  document.getElementById("kpi-avg-fare").textContent      = formatCurrency(avgFare.toFixed(2));
  document.getElementById("kpi-top-borough").textContent   = topBorough.borough;
  document.getElementById("kpi-borough-count").textContent = boroughs.length;

  const topShare = ((topBorough.total_revenue / totalRevenue) * 100).toFixed(0);
  document.getElementById("caption-borough").textContent =
    `${topBorough.borough} generates ${topShare}% of all revenue from ${formatNumber(topBorough.total_trips)} trips.`;

  new Chart(document.getElementById("chart-revenue-by-borough"), {
    type: "bar",
    data: {
      labels: boroughs.map(b => b.borough),
      datasets: [{
        label: "Total Revenue",
        data: boroughs.map(b => b.total_revenue),
        backgroundColor: boroughs.map(b => BOROUGH_COLORS[b.borough] || "#9AA0AC"),
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: "#9AA0AC", callback: v => "$" + (v / 1e6).toFixed(0) + "M" },
          grid: { color: "#2A2E37" },
        },
        y: {
          ticks: { color: "#F2F1ED" },
          grid: { display: false },
        },
      },
    },
  });
}

async function loadRevenueTrend() {
  const data = await fetchJSON("/analytics/revenue-trends");
  const trend = data.trend;

  const peakDay = trend.reduce((max, d) => d.total_revenue > max.total_revenue ? d : max, trend[0]);
  const peakLabel = new Date(peakDay.date).toLocaleDateString("en-US", { month: "short", day: "numeric" });

  document.getElementById("caption-trend").textContent =
    `Peak day was ${peakLabel} with ${formatCurrency(peakDay.total_revenue)} in revenue.`;

  new Chart(document.getElementById("chart-revenue-trend"), {
    type: "line",
    data: {
      labels: trend.map(d => new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })),
      datasets: [{
        label: "Daily Revenue",
        data: trend.map(d => d.total_revenue),
        borderColor: "#FCCC0A",
        backgroundColor: "rgba(252, 204, 10, 0.12)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: "#9AA0AC", maxTicksLimit: 8 },
          grid: { display: false },
        },
        y: {
          ticks: { color: "#9AA0AC", callback: v => "$" + (v / 1000).toFixed(0) + "K" },
          grid: { color: "#2A2E37" },
        },
      },
    },
  });
}

async function loadAverageFare() {
  const data = await fetchJSON("/analytics/average-fare");
  const rows = data.fares;

  // Focus on the two dominant payment methods per borough to keep the
  // chart readable — Credit Card and Cash account for the vast majority
  // of trips, and comparing them is the most useful story here.
  const boroughs = [...new Set(rows.map(r => r.borough))];
  const creditCard = boroughs.map(b => {
    const row = rows.find(r => r.borough === b && r.payment_method === "Credit Card");
    return row ? row.avg_fare : 0;
  });
  const cash = boroughs.map(b => {
    const row = rows.find(r => r.borough === b && r.payment_method === "Cash");
    return row ? row.avg_fare : 0;
  });

  const ccAvg = creditCard.reduce((a, b) => a + b, 0) / creditCard.length;
  const cashAvg = cash.reduce((a, b) => a + b, 0) / cash.length;
  const higher = ccAvg > cashAvg ? "Credit card" : "Cash";

  document.getElementById("caption-fare").textContent =
    `${higher} fares run higher on average across boroughs.`;

  new Chart(document.getElementById("chart-average-fare"), {
    type: "bar",
    data: {
      labels: boroughs,
      datasets: [
        {
          label: "Credit Card",
          data: creditCard,
          backgroundColor: "#FCCC0A",
          borderRadius: 4,
        },
        {
          label: "Cash",
          data: cash,
          backgroundColor: "#4D7FE0",
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#F2F1ED" } },
      },
      scales: {
        x: {
          ticks: { color: "#9AA0AC" },
          grid: { display: false },
        },
        y: {
          ticks: { color: "#9AA0AC", callback: v => "$" + v },
          grid: { color: "#2A2E37" },
        },
      },
    },
  });
}

async function loadFareDistribution() {
  const data = await fetchJSON("/analytics/fare-distribution");
  const rows = data.distribution;

  const busiest = rows.reduce((max, r) => r.trip_count > max.trip_count ? r : max, rows[0]);

  document.getElementById("caption-distribution").textContent =
    `Most trips fall in the $${busiest.range} range, at an average of $${busiest.avg_fare}.`;

  new Chart(document.getElementById("chart-fare-distribution"), {
    type: "bar",
    data: {
      labels: rows.map(r => "$" + r.range),
      datasets: [{
        label: "Trips",
        data: rows.map(r => r.trip_count),
        backgroundColor: "#FF6319",
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: "#9AA0AC" },
          grid: { display: false },
        },
        y: {
          ticks: { color: "#9AA0AC", callback: v => (v / 1e6).toFixed(1) + "M" },
          grid: { color: "#2A2E37" },
        },
      },
    },
  });
}

loadRevenueByBorough();
loadRevenueTrend();
loadAverageFare();
loadFareDistribution();