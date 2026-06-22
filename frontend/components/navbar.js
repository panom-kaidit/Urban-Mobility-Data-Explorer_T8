// Injects the top navbar into #app-wrapper before #main-content.
// Call: injectNavbar()

function injectNavbar() {
  var existing = document.getElementById("navbar");
  if (existing) return;

  const now     = new Date();
  const dateStr = now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });

  const nav = document.createElement("nav");
  nav.className = "navbar";
  nav.id        = "navbar";
  nav.innerHTML = `
    <div class="navbar-left">
      <button class="navbar-toggle" id="sidebar-toggle" aria-label="Toggle navigation">
        <span></span><span></span><span></span>
      </button>
      <div>
        <div class="navbar-title" id="navbar-title">Urban Mobility Explorer</div>
        <div class="navbar-subtitle">NYC Yellow Taxi &middot; January 2019</div>
      </div>
    </div>
    <div class="navbar-right">
      <span class="navbar-date">${dateStr}</span>
      <div class="navbar-status">
        <span class="status-dot online" id="api-status-dot"></span>
        <span id="api-status-label" style="font-size:0.75rem;color:var(--text-secondary)">Connecting&hellip;</span>
      </div>
    </div>
  `;

  const wrapper = document.getElementById("app-wrapper");
  const main    = document.getElementById("main-content");
  if (wrapper && main) wrapper.insertBefore(nav, main);

  // Wire sidebar toggle
  document.addEventListener("click", function(e) {
    if (!e.target.closest("#sidebar-toggle")) return;
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.toggle("open");
    if (overlay) overlay.classList.toggle("active");
  });

  // Close sidebar on overlay click
  document.addEventListener("click", function(e) {
    if (!e.target.closest("#sidebar-overlay")) return;
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
  });

  _checkBackendStatus();
}

function showApp() {
  var wrapper = document.getElementById("app-wrapper");
  if (wrapper) wrapper.classList.add("ready");
}

function setNavbarTitle(title) {
  const el = document.getElementById("navbar-title");
  if (el) el.textContent = title;
}

function _checkBackendStatus() {
  const dot   = document.getElementById("api-status-dot");
  const label = document.getElementById("api-status-label");
  if (!dot || !label) return;

  fetch("http://localhost:8000/")
    .then(function(r) {
      if (r.ok) {
        dot.className     = "status-dot online";
        label.textContent = "Backend Online";
        label.style.color = "var(--accent-green)";
      } else {
        _setOffline(dot, label);
      }
    })
    .catch(function() { _setOffline(dot, label); });
}

function _setOffline(dot, label) {
  dot.className     = "status-dot offline";
  label.textContent = "Backend Offline";
  label.style.color = "var(--accent-red)";
}
