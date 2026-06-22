// Injects the top navbar into #app-wrapper before #main-content.
// Call: injectNavbar()

function injectNavbar() {
  var existing = document.getElementById("navbar");
  if (existing) return;

  const nav = document.createElement("nav");
  nav.className = "navbar";
  nav.id        = "navbar";
  nav.innerHTML = `
    <div class="navbar-left">
      <button class="navbar-toggle" id="sidebar-toggle" aria-label="Toggle navigation" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <div>
        <div class="navbar-title" id="navbar-title">Urban Mobility Explorer</div>
        <div class="navbar-subtitle">NYC Yellow Taxi &middot; January 2019</div>
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
    var isOpen = sidebar ? !sidebar.classList.contains("open") : false;
    if (sidebar) sidebar.classList.toggle("open", isOpen);
    if (overlay) overlay.classList.toggle("active", isOpen);
    e.target.closest("#sidebar-toggle").setAttribute("aria-expanded", String(isOpen));
  });

  // Close sidebar on overlay click
  document.addEventListener("click", function(e) {
    if (!e.target.closest("#sidebar-overlay")) return;
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("active");
    var toggle = document.getElementById("sidebar-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  });

}

function showApp() {
  var wrapper = document.getElementById("app-wrapper");
  if (wrapper) wrapper.classList.add("ready");
}

function setNavbarTitle(title) {
  const el = document.getElementById("navbar-title");
  if (el) el.textContent = title;
}
