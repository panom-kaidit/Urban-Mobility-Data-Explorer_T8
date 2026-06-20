// Data quality page controller.
// Requires: api.js, charts.js, navbar.js, sidebar.js

var _dqPage    = 0;
var _dqLimit   = 50;
var _dqTotal   = 0;
var _dqReasons = {};

async function initDataQualityPage() {
  injectSidebar("data-quality");
  injectNavbar();
  setNavbarTitle("Data Quality");

  document.getElementById("dq-prev-btn").addEventListener("click", function() {
    if (_dqPage > 0) { _dqPage--; _loadPage(); }
  });
  document.getElementById("dq-next-btn").addEventListener("click", function() {
    var maxPage = Math.ceil(_dqTotal / _dqLimit) - 1;
    if (_dqPage < maxPage) { _dqPage++; _loadPage(); }
  });

  await _loadPage();
}

async function _loadPage() {
  _setNavBtns(false, false);

  try {
    var data  = await fetchSuspiciousRecords(_dqLimit, _dqPage * _dqLimit);
    var items = data.items || [];

    _dqTotal = _estimateTotal(data, items);

    // Count reasons
    items.forEach(function(r) {
      var reason = r.removal_reason || "unknown";
      _dqReasons[reason] = (_dqReasons[reason] || 0) + 1;
    });

    _updateKpis(items);
    _renderTable(items);
    _updateLabel();
    _setNavBtns(_dqPage > 0, items.length === _dqLimit);

    if (_dqPage === 0) {
      _renderCharts();
    }

  } catch (err) {
    var tbody = document.getElementById("dq-records-tbody");
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--accent-red);padding:1.5rem">Could not load records. Is the backend running?</td></tr>';
    console.error("initDataQualityPage:", err);
  }
}

function _estimateTotal(data, items) {
  // Backend returns count = len(rows) not total. We estimate from offset + rows.
  if (data.count < _dqLimit) {
    return _dqPage * _dqLimit + data.count;
  }
  // If we got a full page, estimate total as 13,677 (known from ETL)
  return 13677;
}

function _updateKpis(items) {
  var known = 13677;
  var el = document.getElementById("dq-total-count");
  if (el) el.textContent = formatNumber(known);

  var rate = ((known / (known + 7682940)) * 100).toFixed(2);
  var ratEl = document.getElementById("dq-reject-rate");
  if (ratEl) ratEl.textContent = rate + "%";

  // Top reason from accumulated data
  var topReason = Object.keys(_dqReasons).sort(function(a, b) {
    return _dqReasons[b] - _dqReasons[a];
  })[0];
  var reasonEl = document.getElementById("dq-top-reason");
  if (reasonEl && topReason) {
    reasonEl.textContent = topReason.replace(/_/g, " ");
  }
}

function _renderTable(items) {
  var tbody = document.getElementById("dq-records-tbody");
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-muted)">No records found.</td></tr>';
    return;
  }

  var rows = items.map(function(r) {
    var reasonBadge = _reasonBadge(r.removal_reason || "unknown");
    var pickup  = r.pickup_datetime  ? r.pickup_datetime.slice(0, 16).replace("T", " ") : "—";
    var dropoff = r.dropoff_datetime ? r.dropoff_datetime.slice(0, 16).replace("T", " ") : "—";
    return (
      "<tr>" +
        "<td style='font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted)'>" + r.record_id + "</td>" +
        "<td style='white-space:nowrap;font-size:0.77rem'>" + pickup + "</td>" +
        "<td style='white-space:nowrap;font-size:0.77rem'>" + dropoff + "</td>" +
        "<td>" + (r.trip_distance != null ? Number(r.trip_distance).toFixed(2) + " mi" : "—") + "</td>" +
        "<td>" + (r.fare_amount != null ? "$" + Number(r.fare_amount).toFixed(2) : "—") + "</td>" +
        "<td>" + reasonBadge + "</td>" +
      "</tr>"
    );
  });

  tbody.innerHTML = rows.join("");
}

function _reasonBadge(reason) {
  var cls = "reason-missing";
  if (reason.indexOf("invalid")    !== -1) cls = "reason-invalid";
  if (reason.indexOf("negative")   !== -1) cls = "reason-negative";
  if (reason.indexOf("duplicate")  !== -1) cls = "reason-duplicate";
  return '<span class="reason-badge ' + cls + '">' + reason.replace(/_/g, " ") + '</span>';
}

function _renderCharts() {
  // Collect reason counts from current _dqReasons
  var labels = Object.keys(_dqReasons);
  var values = labels.map(function(k) { return _dqReasons[k]; });
  var colors = ["#FF9F43", "#FF5A7A", "#8B5CF6", "#00D4FF", "#10F0A0", "#3B82F6"];

  // Reason breakdown bar chart
  var rc = document.getElementById("dq-reason-chart");
  if (rc) {
    rc.innerHTML = '<canvas id="dq-reason-canvas"></canvas>';
    createBarChart(
      document.getElementById("dq-reason-canvas"),
      labels.map(function(l) { return l.replace(/_/g, " "); }),
      values,
      colors.slice(0, labels.length)
    );
  }

  // Doughnut: clean vs flagged
  var qc = document.getElementById("dq-quality-chart");
  if (qc) {
    qc.innerHTML = '<canvas id="dq-quality-canvas"></canvas>';
    createDoughnutChart(
      document.getElementById("dq-quality-canvas"),
      ["Clean Trips (7.68M)", "Flagged (13,677)"],
      [7682940, 13677],
      ["#10F0A0", "#FF5A7A"]
    );
  }
}

function _updateLabel() {
  var from  = _dqPage * _dqLimit + 1;
  var to    = _dqPage * _dqLimit + _dqLimit;
  var label = document.getElementById("dq-showing-label");
  if (label) label.textContent = "Showing " + from + "–" + Math.min(to, _dqTotal);
}

function _setNavBtns(prevEnabled, nextEnabled) {
  var prev = document.getElementById("dq-prev-btn");
  var next = document.getElementById("dq-next-btn");
  if (prev) prev.disabled = !prevEnabled;
  if (next) next.disabled = !nextEnabled;
}

document.addEventListener("DOMContentLoaded", initDataQualityPage);
