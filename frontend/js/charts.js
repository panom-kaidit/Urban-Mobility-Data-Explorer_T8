// Shared chart utilities for the dark analytics theme.
// Requires: Chart.js, api.js (for dark defaults already applied in api.js)

// ---- Borough color palette (NYC subway lines) ----
var BOROUGH_COLORS = {
  Manhattan:       "#FCCC0A",
  Brooklyn:        "#FF6319",
  Queens:          "#B933AD",
  Bronx:           "#00933C",
  "Staten Island": "#9AA0AC",
  EWR:             "#4D7FE0",
};

// Fallback gradient for non-borough data
var GRADIENT_COLORS = [
  "#10F0A0", "#00D4FF", "#3B82F6",
  "#8B5CF6", "#FF9F43", "#FF5A7A",
];

function boroughColor(borough) {
  return BOROUGH_COLORS[borough] || "#8B9BB4";
}

// ---- Dark chart option presets ----

function darkScales(opts) {
  opts = opts || {};
  return {
    x: Object.assign({
      grid:  { color: "rgba(0, 212, 255, 0.06)", drawBorder: false },
      ticks: { color: "#8B9BB4" },
    }, opts.x || {}),
    y: Object.assign({
      grid:  { color: "rgba(0, 212, 255, 0.06)", drawBorder: false },
      ticks: { color: "#8B9BB4" },
      beginAtZero: true,
    }, opts.y || {}),
  };
}

function darkPlugins(opts) {
  opts = opts || {};
  return Object.assign({
    legend:  { display: false },
    tooltip: {},
  }, opts);
}

// ---- Chart factory helpers ----

function createHorizontalBarChart(canvas, labels, values, colors, tooltipExtra) {
  return new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        data:            values,
        backgroundColor: colors || GRADIENT_COLORS.slice(0, values.length),
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      indexAxis: "y",
      responsive:          true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        tooltip: {
          callbacks: {
            label:      function(ctx) { return " " + formatNumber(ctx.raw); },
            afterLabel: tooltipExtra || undefined,
          },
        },
      }),
      scales: darkScales({
        x: { ticks: { color: "#8B9BB4", callback: function(v) { return formatCompact(v); } } },
        y: { grid: { display: false }, ticks: {
          color: "#8B9BB4",
          callback: function(v, i) {
            var s = labels[i] || "";
            return s.length > 24 ? s.slice(0, 22) + "…" : s;
          },
        }},
      }),
    },
  });
}

function createBarChart(canvas, labels, values, colors) {
  return new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        data:            values,
        backgroundColor: colors || GRADIENT_COLORS.slice(0, values.length),
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        tooltip: {
          callbacks: {
            label: function(ctx) { return " " + formatNumber(ctx.raw); },
          },
        },
      }),
      scales: darkScales({
        x: { grid: { display: false } },
        y: { ticks: { color: "#8B9BB4", callback: function(v) { return formatCompact(v); } } },
      }),
    },
  });
}

function createLineChart(canvas, labels, values, color, fill) {
  color = color || "#00D4FF";
  return new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        data:            values,
        borderColor:     color,
        backgroundColor: color.replace(")", ", 0.10)").replace("rgb", "rgba"),
        fill:            fill !== false,
        tension:         0.3,
        pointRadius:     0,
        borderWidth:     2,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        tooltip: {
          mode:      "index",
          intersect: false,
        },
      }),
      scales: darkScales({
        x: { grid: { display: false }, ticks: { color: "#8B9BB4", maxTicksLimit: 8 } },
        y: { ticks: { color: "#8B9BB4", callback: function(v) { return formatCompact(v); } } },
      }),
    },
  });
}

function createGroupedBarChart(canvas, labels, datasets) {
  return new Chart(canvas, {
    type: "bar",
    data: {
      labels:   labels,
      datasets: datasets,
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        legend: {
          display: true,
          position: "top",
          labels: { color: "#8B9BB4", boxWidth: 12, padding: 16 },
        },
      }),
      scales: darkScales({
        x: { grid: { display: false } },
        y: { ticks: { color: "#8B9BB4", callback: function(v) { return "$" + v; } } },
      }),
    },
  });
}

function createDoughnutChart(canvas, labels, values, colors) {
  return new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data:            values,
        backgroundColor: colors || GRADIENT_COLORS,
        borderColor:     "transparent",
        hoverOffset:     6,
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: darkPlugins({
        legend: {
          display:  true,
          position: "bottom",
          labels:   { color: "#8B9BB4", padding: 12, boxWidth: 12 },
        },
      }),
      cutout: "65%",
    },
  });
}

// ---- Chart container state helpers ----

function showChartLoading(containerId, msg) {
  var el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = (
    '<div class="chart-placeholder">' +
      '<div class="loading-spinner"></div>' +
      '<span>' + (msg || "Loading…") + '</span>' +
    '</div>'
  );
}

function showChartError(containerId, msg) {
  var el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = (
    '<div class="chart-placeholder">' +
      '<div class="chart-placeholder-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>' +
      '<span style="color:var(--accent-red);max-width:260px;text-align:center;">' + (msg || "Data unavailable.") + '</span>' +
    '</div>'
  );
}

function showChartComingSoon(containerId, label) {
  var el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = (
    '<div class="coming-soon">' +
      '<div class="coming-soon-icon"><i class="fa-solid fa-clock"></i></div>' +
      '<div class="section-title">' + (label || "Coming Soon") + '</div>' +
      '<div class="coming-soon-label">No data available.</div>' +
    '</div>'
  );
}
