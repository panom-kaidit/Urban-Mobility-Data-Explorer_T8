// Dashboard controller for the UI
// - Injects navbar, sidebar, and filters
// - Calls APIs and renders cards and charts
// Requires: api.js, cards.js, navbar.js, sidebar.js, filters.js

// Chart.js instances (kept so we can destroy before re-render)
var topZonesChart = null;
var fareDistChart = null;

// Initialization — runs on DOM ready

// Entry point: setup UI and load data
async function initDashboard() {
  injectSidebar('dashboard');
  injectNavbar();
  injectFilters();
  setupFilterHandlers(function(filters) { loadDashboardData(filters); });
  await loadDashboardData({});
}

// Data loading

// Load and render all dashboard data. filters may be empty.
async function loadDashboardData(filters) {
  showCardsLoading();
  showChartLoading('zones-chart-container', 'Loading top pickup zones…');
  showChartLoading('fare-chart-container', 'Loading fare distribution…');

  // Run API calls in parallel
  var results = await Promise.all([
    fetchDashboardStats(filters),
    fetchTopPickupZones(10),
    fetchFareDistribution(),
  ]);

  var stats     = results[0];
  var zonesData = results[1];
  var fareData  = results[2];

  // Render summary cards
  if (stats) {
    renderCards(stats);                                      /* cards.js */
  } else {
    showCardsError();                                        /* cards.js */
  }

  // Render top pickup zones chart
  if (zonesData && zonesData.zones && zonesData.zones.length > 0) {
    renderTopZonesChart(zonesData.zones);
  } else {
    showChartError('zones-chart-container', 'Could not load pickup zone data. Is the backend running?');
  }

  // Render fare distribution chart
  if (fareData && fareData.distribution && fareData.distribution.length > 0) {
    renderFareDistributionChart(fareData.distribution);
  } else {
    showChartError('fare-chart-container', 'Could not load fare distribution data. Is the backend running?');
  }
}

// Chart helpers: loading and error states

// Show a spinner and message in a chart container
function showChartLoading(containerId, message) {
  var el = document.getElementById(containerId);
  if (!el) { return; }
  el.innerHTML = (
    '<div class="chart-placeholder">' +
      '<div class="loading-spinner"></div>' +
      '<span>' + message + '</span>' +
    '</div>'
  );
}

// Show an error message in a chart container
function showChartError(containerId, message) {
  var el = document.getElementById(containerId);
  if (!el) { return; }
  el.innerHTML = (
    '<div class="chart-placeholder">' +
      '<div class="chart-placeholder-icon">&#x26A0;&#xFE0F;</div>' +   /* ⚠️ */
      '<span style="color:var(--danger-color); text-align:center;">' + message + '</span>' +
    '</div>'
  );
}

// Chart rendering

// Render top pickup zones (horizontal bar). zones = [{zone_id, zone_name, borough, trip_count}]
function renderTopZonesChart(zones) {
  var container = document.getElementById('zones-chart-container');
  if (!container) { return; }

  // Replace placeholder with canvas
  container.innerHTML = '<canvas id="top-zones-canvas"></canvas>';
  var canvas = document.getElementById('top-zones-canvas');

  // Prepare labels and values
  var labels = zones.map(function(z) {
    return z.zone_name || ('Zone ' + z.zone_id);
  });
  var values = zones.map(function(z) { return z.trip_count; });

  // One color per borough
  var BOROUGH_COLORS = {
    'Manhattan':    '#2563eb',   /* blue   */
    'Brooklyn':     '#0ea5e9',   /* sky    */
    'Queens':       '#10b981',   /* green  */
    'Bronx':        '#f59e0b',   /* amber  */
    'Staten Island':'#7c3aed',   /* purple */
    'EWR':          '#ef4444',   /* red    */
  };
  var colors = zones.map(function(z) {
    return BOROUGH_COLORS[z.borough] || '#94a3b8';
  });

  // Destroy old chart if present
  if (topZonesChart) {
    topZonesChart.destroy();
    topZonesChart = null;
  }

  // Create horizontal bar chart
  topZonesChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label:           'Trip Count',
        data:            values,
        backgroundColor: colors,
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      indexAxis:         'y',        /* makes bars horizontal */
      responsive:        true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            /* Show borough in the tooltip */
            afterLabel: function(context) {
              var zone = zones[context.dataIndex];
              return 'Borough: ' + (zone.borough || 'Unknown');
            },
            label: function(context) {
              return ' Trips: ' + context.raw.toLocaleString();
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            callback: function(val) { return val.toLocaleString(); },
          },
        },
        y: {
          grid: { display: false },
          ticks: {
            /* Trim long zone names so they fit */
            callback: function(val, index) {
              var name = labels[index] || '';
              return name.length > 22 ? name.slice(0, 20) + '…' : name;
            },
          },
        },
      },
    },
  });
}

// Render fare distribution bar chart. distribution = [{range, trip_count}]
function renderFareDistributionChart(distribution) {
  var container = document.getElementById('fare-chart-container');
  if (!container) { return; }

  // Replace placeholder with canvas
  container.innerHTML = '<canvas id="fare-dist-canvas"></canvas>';
  var canvas = document.getElementById('fare-dist-canvas');

  var labels = distribution.map(function(d) { return d.range; });
  var values = distribution.map(function(d) { return d.trip_count; });

  // Colors from cheap → expensive
  var BAR_COLORS = ['#10b981', '#0ea5e9', '#2563eb', '#7c3aed', '#f59e0b', '#ef4444'];

  // Destroy old chart
  if (fareDistChart) {
    fareDistChart.destroy();
    fareDistChart = null;
  }

  fareDistChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label:           'Number of Trips',
        data:            values,
        backgroundColor: BAR_COLORS.slice(0, distribution.length),
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      responsive:        true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ' ' + context.raw.toLocaleString() + ' trips';
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            callback: function(val) { return val.toLocaleString(); },
          },
        },
        x: { grid: { display: false } },
      },
    },
  });
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', initDashboard);
