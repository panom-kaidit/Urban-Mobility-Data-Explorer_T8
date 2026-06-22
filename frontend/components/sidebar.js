// Injects the sidebar and overlay into #app-wrapper.
// Call: injectSidebar(activePage)
// activePage: 'dashboard' | 'revenue' | 'mobility' | 'zones' | 'data-quality' | 'reports'

var SIDEBAR_LINKS = [
  {
    section: "Analytics",
    links: [
      { id: "dashboard",    href: "/dashboard",    icon: '<i class="fa-solid fa-chart-line"></i>',       label: "Dashboard" },
      { id: "revenue",      href: "/revenue",      icon: '<i class="fa-solid fa-dollar-sign"></i>',      label: "Revenue" },
      { id: "mobility",     href: "/mobility",     icon: '<i class="fa-solid fa-route"></i>',            label: "Mobility" },
      { id: "zones",        href: "/zones",        icon: '<i class="fa-solid fa-map-location-dot"></i>', label: "Zone Intelligence" },
    ],
  },
  {
    section: "Operations",
    links: [
      { id: "data-quality", href: "/data-quality", icon: '<i class="fa-solid fa-shield-halved"></i>',   label: "Data Quality" },
      { id: "reports",      href: "/reports",      icon: '<i class="fa-solid fa-file-lines"></i>',      label: "Reports" },
    ],
  },
];

function injectSidebar(activePage) {
  var linksHtml = "";

  SIDEBAR_LINKS.forEach(function(section) {
    linksHtml += '<div class="sidebar-section">';
    linksHtml += '<div class="sidebar-section-title">' + section.section + '</div>';

    section.links.forEach(function(link) {
      var isActive = link.id === activePage ? " active" : "";
      linksHtml += (
        '<a href="' + link.href + '" class="sidebar-link' + isActive + '">' +
          '<span class="sidebar-link-icon">' + link.icon + '</span>' +
          '<span class="sidebar-link-label">' + link.label + '</span>' +
        '</a>'
      );
    });

    linksHtml += '</div>';
  });

  // Sidebar element
  var aside = document.createElement("aside");
  aside.className = "sidebar";
  aside.id        = "sidebar";
  aside.setAttribute("role", "navigation");
  aside.setAttribute("aria-label", "Main navigation");
  aside.innerHTML = `
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon"><img src="/assets/images/logo.png" alt="logo"></div>
      <div class="sidebar-logo-text">
        Urban Mobility
        <span>Data Explorer T8</span>
      </div>
    </div>
    ${linksHtml}
    <div class="sidebar-footer">
      <strong>Dataset:</strong> NYC Yellow Taxi<br>
      January 2019 &middot; 7.68M trips
    </div>
  `;

  // Overlay (for mobile)
  var overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  overlay.id        = "sidebar-overlay";

  var wrapper = document.getElementById("app-wrapper");
  if (wrapper) {
    wrapper.insertBefore(aside, wrapper.firstChild);
    wrapper.insertBefore(overlay, wrapper.firstChild);
  }
}
