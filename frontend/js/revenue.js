// Revenue analytics page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js

async function initRevenuePage() {
  injectSidebar("revenue");
  injectNavbar();
  setNavbarTitle("Revenue Analytics");

  await Promise.allSettled([
    loadRevenueByBorough(),
    loadRevenueTrend(),
    loadAverageFare(),
    loadFareDistribution(),
  ]);
}

async function loadRevenueByBorough() {
  var wrap = document.getElementById("wrap-revenue-by-borough");
  if (wrap) wrap.innerHTML = _loadHtml();

  try {
    var data     = await fetchRevenueByBorough();
    var boroughs = data.boroughs;

    var totalRevenue = boroughs.reduce(function(s, b) { return s + b.total_revenue; }, 0);
    var totalTrips   = boroughs.reduce(function(s, b) { return s + b.total_trips; }, 0);
    var avgFare      = totalRevenue / totalTrips;
    var top          = boroughs[0];

    _setKpi("kpi-total-revenue", formatCurrency(totalRevenue));
    _setKpi("kpi-total-trips",   formatNumber(totalTrips));
    _setKpi("kpi-avg-fare",      "$" + Number(avgFare).toFixed(2));
    _setKpi("kpi-top-borough",   top.borough);

    var topShare = ((top.total_revenue / totalRevenue) * 100).toFixed(0);
    _setCaption("caption-borough",
      top.borough + " generates " + topShare + "% of revenue from " +
      formatNumber(top.total_trips) + " trips."
    );

    if (wrap) wrap.innerHTML = '<canvas id="chart-revenue-by-borough"></canvas>';
    createHorizontalBarChart(
      document.getElementById("chart-revenue-by-borough"),
      boroughs.map(function(b) { return b.borough; }),
      boroughs.map(function(b) { return b.total_revenue; }),
      boroughs.map(function(b) { return boroughColor(b.borough); }),
      function(ctx) {
        return formatNumber(boroughs[ctx.dataIndex].total_trips) + " trips";
      }
    );

  } catch (err) {
    if (wrap) wrap.innerHTML = _errHtml("Revenue by Borough");
    console.error("loadRevenueByBorough:", err);
  }
}

async function loadRevenueTrend() {
  var wrap = document.getElementById("wrap-revenue-trend");
  if (wrap) wrap.innerHTML = _loadHtml();

  try {
    var data  = await fetchRevenueTrends();
    var trend = data.trend;

    var peak = trend.reduce(function(max, d) {
      return d.total_revenue > max.total_revenue ? d : max;
    }, trend[0]);
    var peakLabel = new Date(peak.date + "T00:00:00").toLocaleDateString("en-US", {
      month: "short", day: "numeric",
    });
    _setCaption("caption-trend",
      "Peak: " + peakLabel + " — " + formatCurrency(peak.total_revenue)
    );

    if (wrap) wrap.innerHTML = '<canvas id="chart-revenue-trend"></canvas>';
    createLineChart(
      document.getElementById("chart-revenue-trend"),
      trend.map(function(d) {
        return new Date(d.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
      }),
      trend.map(function(d) { return d.total_revenue; }),
      "#FCCC0A",
      true
    );

  } catch (err) {
    if (wrap) wrap.innerHTML = _errHtml("Revenue Trend");
    console.error("loadRevenueTrend:", err);
  }
}

async function loadAverageFare() {
  var wrap = document.getElementById("wrap-average-fare");
  if (wrap) wrap.innerHTML = _loadHtml();

  try {
    var data = await fetchAverageFare();
    var rows = data.fares;

    var boroughList = [];
    rows.forEach(function(r) {
      if (boroughList.indexOf(r.borough) === -1) boroughList.push(r.borough);
    });

    var creditCard = boroughList.map(function(b) {
      var r = rows.find(function(x) { return x.borough === b && x.payment_method === "Credit Card"; });
      return r ? r.avg_fare : 0;
    });
    var cash = boroughList.map(function(b) {
      var r = rows.find(function(x) { return x.borough === b && x.payment_method === "Cash"; });
      return r ? r.avg_fare : 0;
    });

    var ccAvg   = creditCard.reduce(function(a, b) { return a + b; }, 0) / Math.max(creditCard.length, 1);
    var cashAvg = cash.reduce(function(a, b) { return a + b; }, 0) / Math.max(cash.length, 1);
    _setCaption("caption-fare",
      (ccAvg > cashAvg ? "Credit card" : "Cash") + " fares run higher on average."
    );

    if (wrap) wrap.innerHTML = '<canvas id="chart-average-fare"></canvas>';
    createGroupedBarChart(
      document.getElementById("chart-average-fare"),
      boroughList,
      [
        { label: "Credit Card", data: creditCard, backgroundColor: "#FCCC0A", borderRadius: 4 },
        { label: "Cash",        data: cash,        backgroundColor: "#4D7FE0", borderRadius: 4 },
      ]
    );

  } catch (err) {
    if (wrap) wrap.innerHTML = _errHtml("Average Fare");
    console.error("loadAverageFare:", err);
  }
}

async function loadFareDistribution() {
  var wrap = document.getElementById("wrap-fare-distribution");
  if (wrap) wrap.innerHTML = _loadHtml();

  try {
    var data = await fetchFareDistribution();
    var rows = data.distribution;

    var busiest = rows.reduce(function(max, r) {
      return r.trip_count > max.trip_count ? r : max;
    }, rows[0]);

    _setCaption("caption-distribution",
      "Most trips: $" + busiest.range +
      (busiest.avg_fare ? " range — avg $" + busiest.avg_fare : "") + "."
    );

    if (wrap) wrap.innerHTML = '<canvas id="chart-fare-distribution"></canvas>';
    createBarChart(
      document.getElementById("chart-fare-distribution"),
      rows.map(function(r) { return "$" + r.range; }),
      rows.map(function(r) { return r.trip_count; }),
      ["#10F0A0", "#00D4FF", "#3B82F6", "#8B5CF6", "#FF9F43", "#FF5A7A"]
    );

  } catch (err) {
    if (wrap) wrap.innerHTML = _errHtml("Fare Distribution");
    console.error("loadFareDistribution:", err);
  }
}

function _setKpi(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}
function _setCaption(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}
function _loadHtml() {
  return '<div class="chart-placeholder"><div class="loading-spinner"></div></div>';
}
function _errHtml(title) {
  return (
    '<div class="chart-placeholder">' +
      '<span style="color:var(--accent-red)">&#x26A0;&#xFE0F; Could not load ' + title + '.</span>' +
    '</div>'
  );
}

document.addEventListener("DOMContentLoaded", initRevenuePage);