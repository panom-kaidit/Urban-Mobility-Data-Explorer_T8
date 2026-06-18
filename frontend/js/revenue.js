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

  // derive KPIs from this single response — no extra endpoint needed
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

loadRevenueByBorough();