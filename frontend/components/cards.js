// KPI card renderer with sparklines.
// Requires: Chart.js (loaded before this file).
// Exports: renderCards(stats), showCardsLoading(), showCardsError()

var _sparkCharts = {};

var CARD_DEFS = [
  {
    id:      "card-total-trips",
    label:   "Total Trips",
    icon:    '<i class="fa-solid fa-taxi"></i>',
    iconCls: "icon-blue",
    key:     "totalTrips",
    format:  "compact",
    meta:    "January 2019 dataset",
    trend:   { pct: 0, label: "Jan 2019" },
    sparkColor: "rgba(0, 212, 255, 0.7)",
  },
  {
    id:      "card-total-revenue",
    label:   "Total Revenue",
    icon:    '<i class="fa-solid fa-money-bill-wave"></i>',
    iconCls: "icon-green",
    key:     "totalRevenue",
    format:  "currency",
    meta:    "Exact aggregate (Jan 2019)",
    trend:   { pct: 0, label: "" },
    sparkColor: "rgba(16, 240, 160, 0.7)",
  },
  {
    id:      "card-avg-fare",
    label:   "Avg Fare",
    icon:    '<i class="fa-solid fa-credit-card"></i>',
    iconCls: "icon-yellow",
    key:     "avgFare",
    format:  "currency2",
    meta:    "Exact average (Jan 2019)",
    trend:   { pct: 0, label: "" },
    sparkColor: "rgba(255, 159, 67, 0.7)",
  },
  {
    id:      "card-avg-distance",
    label:   "Avg Distance",
    icon:    '<i class="fa-solid fa-location-dot"></i>',
    iconCls: "icon-purple",
    key:     "avgDistance",
    format:  "miles",
    meta:    "Miles per trip",
    trend:   { pct: 0, label: "" },
    sparkColor: "rgba(139, 92, 246, 0.7)",
  },
];

function _formatValue(val, fmt) {
  switch (fmt) {
    case "compact":  return formatCompact(val);
    case "currency": return formatCurrency(val);
    case "currency2": return "$" + Number(val).toFixed(2);
    case "miles":    return Number(val).toFixed(1) + " mi";
    default:         return String(val);
  }
}

function _makeSpark(canvasId, color) {
  var canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") return;

  // Generate synthetic sparkline data (placeholder wave)
  var pts = [];
  for (var i = 0; i < 20; i++) {
    pts.push(50 + 30 * Math.sin(i * 0.5) + Math.random() * 10);
  }

  if (_sparkCharts[canvasId]) {
    _sparkCharts[canvasId].destroy();
  }

  _sparkCharts[canvasId] = new Chart(canvas, {
    type: "line",
    data: {
      labels: pts.map(function(_, i) { return i; }),
      datasets: [{
        data:        pts,
        borderColor: color,
        borderWidth: 1.5,
        fill:        true,
        backgroundColor: color.replace("0.7", "0.10"),
        tension:     0.4,
        pointRadius: 0,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales:  {
        x: { display: false },
        y: { display: false },
      },
    },
  });
}

function renderCards(stats) {
  var container = document.getElementById("stats-cards");
  if (!container) return;

  container.innerHTML = "";

  CARD_DEFS.forEach(function(def) {
    var val     = stats[def.key] || 0;
    var display = _formatValue(val, def.format);
    var sparkId = def.id + "-spark";

    var card = document.createElement("div");
    card.className = "stat-card fade-in-up";
    card.id        = def.id;
    card.innerHTML = (
      '<div class="stat-card-header">' +
        '<span class="stat-card-label">' + def.label + '</span>' +
        '<div class="stat-card-icon ' + def.iconCls + '">' + def.icon + '</div>' +
      '</div>' +
      '<div class="stat-card-value">' + display + '</div>' +
      '<div class="stat-card-meta">' + def.meta + '</div>' +
      '<div class="sparkline-wrap"><canvas id="' + sparkId + '"></canvas></div>'
    );

    container.appendChild(card);
    _makeSpark(sparkId, def.sparkColor);
  });
}

function showCardsLoading() {
  var container = document.getElementById("stats-cards");
  if (!container) return;

  var html = "";
  for (var i = 0; i < 4; i++) {
    html += (
      '<div class="stat-card">' +
        '<div class="stat-card-header">' +
          '<div class="skeleton" style="width:80px;height:10px;border-radius:4px"></div>' +
          '<div class="skeleton" style="width:38px;height:38px;border-radius:10px"></div>' +
        '</div>' +
        '<div class="skeleton" style="width:100px;height:28px;border-radius:6px;margin-top:8px"></div>' +
        '<div class="skeleton" style="width:60px;height:10px;border-radius:4px;margin-top:8px"></div>' +
        '<div class="skeleton" style="height:36px;border-radius:4px;margin-top:10px"></div>' +
      '</div>'
    );
  }
  container.innerHTML = html;
}

function showCardsError() {
  var container = document.getElementById("stats-cards");
  if (!container) return;

  container.innerHTML = (
    '<div style="grid-column:1/-1;padding:1.5rem;text-align:center;color:var(--accent-red);font-size:0.82rem;">' +
      '<i class="fa-solid fa-triangle-exclamation" style="margin-right:0.4rem"></i>' +
      'Dashboard data unavailable.' +
    '</div>'
  );
}
