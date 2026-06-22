// Global filter engine — renders filter panel and notifies subscribers on change.
// Call: injectFilters()
// Call: setupFilterHandlers(callback)  — callback receives current filter object

var _filterCallback = null;
var _activeFilters  = {};

var BOROUGH_OPTIONS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "EWR"];

function injectFilters() {
  var container = document.getElementById("filters-container");
  if (!container) return;

  var boroughOpts = '<option value="">All Boroughs</option>';
  BOROUGH_OPTIONS.forEach(function(b) {
    boroughOpts += '<option value="' + b + '">' + b + '</option>';
  });

  container.innerHTML = `
    <div class="filters-panel" id="filters-panel">
      <div class="filters-panel-header">
        <div class="filters-panel-title">
          <i class="fa-solid fa-sliders"></i> Filters
        </div>
        <button class="btn btn-ghost btn-sm" id="filters-clear-btn" type="button">Clear All</button>
      </div>
      <div class="filters-grid">
        <div class="form-group">
          <label class="form-label" for="filter-borough">Borough</label>
          <select class="form-control" id="filter-borough">${boroughOpts}</select>
        </div>
        <div class="form-group">
          <label class="form-label" for="filter-date">Pickup Date</label>
          <input class="form-control" type="date" id="filter-date"
                 min="2019-01-01" max="2019-01-31" placeholder="YYYY-MM-DD">
        </div>
        <div class="form-group">
          <label class="form-label" for="filter-distance">Max Distance (mi)</label>
          <input class="form-control" type="number" id="filter-distance"
                 min="0" max="200" step="0.5" placeholder="Any">
        </div>
        <div class="form-group">
          <label class="form-label" for="filter-fare">Max Fare ($)</label>
          <input class="form-control" type="number" id="filter-fare"
                 min="0" max="500" step="1" placeholder="Any">
        </div>
      </div>
      <div class="filters-actions">
        <span id="filters-active-label" style="font-size:0.73rem;color:var(--text-muted)"></span>
        <button class="btn btn-primary" id="filters-apply-btn" type="button">Apply Filters</button>
      </div>
    </div>
  `;
}

function setupFilterHandlers(callback) {
  _filterCallback = callback;

  document.addEventListener("click", function(e) {
    if (e.target.id === "filters-apply-btn") _applyFilters();
    if (e.target.id === "filters-clear-btn") _clearFilters();
  });

  // Also apply on Enter key in any filter input
  document.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && e.target.closest("#filters-panel")) {
      _applyFilters();
    }
  });
}

function _applyFilters() {
  var borough  = _val("filter-borough");
  var date     = _val("filter-date");
  var distance = _val("filter-distance");
  var fare     = _val("filter-fare");

  _activeFilters = {};
  if (borough)  _activeFilters.borough  = borough;
  if (date)     _activeFilters.date     = date;
  if (distance) _activeFilters.distance = parseFloat(distance);
  if (fare)     _activeFilters.fare     = parseFloat(fare);

  _updateActiveLabel();

  if (_filterCallback) _filterCallback(Object.assign({}, _activeFilters));
}

function _clearFilters() {
  _setVal("filter-borough",  "");
  _setVal("filter-date",     "");
  _setVal("filter-distance", "");
  _setVal("filter-fare",     "");
  _activeFilters = {};
  _updateActiveLabel();
  if (_filterCallback) _filterCallback({});
}

function _updateActiveLabel() {
  var label = document.getElementById("filters-active-label");
  if (!label) return;
  var count = Object.keys(_activeFilters).length;
  label.textContent = count > 0 ? count + " filter" + (count > 1 ? "s" : "") + " active" : "";
}

function _val(id) {
  var el = document.getElementById(id);
  return el ? el.value.trim() : "";
}
function _setVal(id, val) {
  var el = document.getElementById(id);
  if (el) el.value = val;
}

function getActiveFilters() {
  return Object.assign({}, _activeFilters);
}
