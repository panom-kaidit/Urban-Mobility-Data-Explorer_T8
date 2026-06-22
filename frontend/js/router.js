// Small client-side router for the dashboard pages.
// It keeps the sidebar/navbar mounted and swaps only the page content.

var _routeLoading = false;
var _currentPageUrl = window.location.href;

var PAGE_INITIALIZERS = {
  "dashboard.html": "initDashboard",
  "revenue.html": "initRevenuePage",
  "mobility.html": "initMobilityPage",
  "zones.html": "initZonesPage",
  "data_quality.html": "initDataQualityPage",
  "reports.html": "initReportsPage",
};

function _absoluteUrl(value, base) {
  return new URL(value, base).href;
}

function _hasStyle(url) {
  return Array.from(document.querySelectorAll('link[rel="stylesheet"]')).some(function(link) {
    return link.href === url;
  });
}

function _loadStyles(pageDocument, pageUrl) {
  var loads = [];
  pageDocument.querySelectorAll('link[rel="stylesheet"]').forEach(function(link) {
    var url = _absoluteUrl(link.getAttribute("href"), pageUrl);
    if (_hasStyle(url)) return;

    loads.push(new Promise(function(resolve) {
      var newLink = document.createElement("link");
      newLink.rel = "stylesheet";
      newLink.href = url;
      newLink.onload = resolve;
      newLink.onerror = resolve;
      document.head.appendChild(newLink);
    }));
  });
  return Promise.all(loads);
}

function _hasScript(url) {
  return Array.from(document.querySelectorAll("script[src]")).some(function(script) {
    return script.src === url;
  });
}

function _loadScript(url) {
  if (_hasScript(url)) return Promise.resolve();

  return new Promise(function(resolve, reject) {
    var script = document.createElement("script");
    script.src = url;
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });
}

async function _loadPageScripts(pageDocument, pageUrl) {
  var scripts = Array.from(pageDocument.querySelectorAll("script[src]"));
  for (var i = 0; i < scripts.length; i++) {
    var url = _absoluteUrl(scripts[i].getAttribute("src"), pageUrl);
    if (url.endsWith("/js/router.js")) continue;
    await _loadScript(url);
  }
}

async function _waitForFirstLayout() {
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (_) {}
  }

  await new Promise(function(resolve) {
    requestAnimationFrame(function() {
      requestAnimationFrame(resolve);
    });
  });
}

async function navigateToPage(href, addHistory) {
  if (_routeLoading) return;
  _routeLoading = true;

  var pageUrl = _absoluteUrl(href, window.location.href);
  var previousTitle = document.title;
  var currentContent = null;
  var nextContent = null;
  var mainContent = null;
  var idSnapshot = [];

  try {
    var response = await fetch(pageUrl);
    if (!response.ok) throw new Error("Page unavailable");

    var html = await response.text();
    var pageDocument = new DOMParser().parseFromString(html, "text/html");
    nextContent = pageDocument.querySelector(".content-inner");
    if (!nextContent) throw new Error("Page content unavailable");

    await _loadStyles(pageDocument, pageUrl);
    await _loadPageScripts(pageDocument, pageUrl);

    currentContent = document.querySelector(".content-inner");
    if (!currentContent) throw new Error("Current page content unavailable");
    mainContent = currentContent.parentElement;
    var mainHeight = mainContent.getBoundingClientRect().height;

    // Freeze the page dimensions while the incoming charts calculate sizes.
    mainContent.style.boxSizing = "border-box";
    mainContent.style.height = mainHeight + "px";
    mainContent.style.overflow = "hidden";

    nextContent.style.visibility = "hidden";
    nextContent.style.position = "absolute";
    nextContent.style.top = "var(--navbar-height)";
    nextContent.style.left = "0";
    nextContent.style.right = "0";

    // Keep the current tab visible while the next one loads. Remove its IDs so
    // the incoming page controller only finds elements in the new content.
    currentContent.querySelectorAll("[id]").forEach(function(element) {
      idSnapshot.push([element, element.id]);
      element.removeAttribute("id");
    });
    currentContent.style.position = "absolute";
    currentContent.style.top = "var(--navbar-height)";
    currentContent.style.left = "0";
    currentContent.style.right = "0";
    currentContent.style.zIndex = "5";
    currentContent.style.background = "var(--bg-primary)";
    currentContent.style.pointerEvents = "none";
    currentContent.parentElement.appendChild(nextContent);

    document.title = pageDocument.title;

    var pageName = new URL(pageUrl).pathname.split("/").pop();
    var initializerName = PAGE_INITIALIZERS[pageName];
    var initializer = initializerName ? window[initializerName] : null;
    if (typeof initializer !== "function") throw new Error("Page unavailable");

    await initializer();
    await _waitForFirstLayout();

    nextContent.style.position = "";
    nextContent.style.top = "";
    nextContent.style.left = "";
    nextContent.style.right = "";
    nextContent.style.visibility = "visible";
    if (addHistory) history.pushState({}, "", pageUrl);
    _currentPageUrl = pageUrl;
    currentContent.remove();
    mainContent.style.height = "";
    mainContent.style.overflow = "";
    mainContent.style.boxSizing = "";
    window.scrollTo(0, 0);
  } catch (error) {
    console.error("Client navigation failed:", error);

    // Keep the current page alive. A navigation error must never turn into a
    // hard browser reload, because that discards page and filter state.
    if (nextContent && nextContent.parentElement) nextContent.remove();
    idSnapshot.forEach(function(entry) {
      if (entry[0].isConnected) entry[0].id = entry[1];
    });
    if (currentContent) {
      currentContent.style.position = "";
      currentContent.style.top = "";
      currentContent.style.left = "";
      currentContent.style.right = "";
      currentContent.style.zIndex = "";
      currentContent.style.background = "";
      currentContent.style.pointerEvents = "";
    }
    if (mainContent) {
      mainContent.style.height = "";
      mainContent.style.overflow = "";
      mainContent.style.boxSizing = "";
    }
    document.title = previousTitle;
    if (window.location.href !== _currentPageUrl) {
      history.replaceState({}, "", _currentPageUrl);
    }
    _showNavigationError();
  } finally {
    _routeLoading = false;
  }
}

function replaceCurrentPageUrl(url) {
  history.replaceState({}, "", url);
  _currentPageUrl = window.location.href;
}

function _showNavigationError() {
  var existing = document.getElementById("navigation-error-toast");
  if (existing) existing.remove();

  var toast = document.createElement("div");
  toast.id = "navigation-error-toast";
  toast.setAttribute("role", "status");
  toast.textContent = "That page could not be loaded. Please try again.";
  toast.style.cssText = "position:fixed;right:1rem;bottom:1rem;z-index:1000;padding:.75rem 1rem;border-radius:8px;background:#7f1d1d;color:#fff;font-size:.8rem;box-shadow:0 8px 24px rgba(0,0,0,.2)";
  document.body.appendChild(toast);
  setTimeout(function() { if (toast.isConnected) toast.remove(); }, 3500);
}

document.addEventListener("click", function(event) {
  var link = event.target.closest(".sidebar-link");
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey) return;

  event.preventDefault();
  var sidebar = document.getElementById("sidebar");
  var overlay = document.getElementById("sidebar-overlay");
  var toggle = document.getElementById("sidebar-toggle");
  if (sidebar) sidebar.classList.remove("open");
  if (overlay) overlay.classList.remove("active");
  if (toggle) toggle.setAttribute("aria-expanded", "false");
  if (link.classList.contains("active")) return;
  navigateToPage(link.href, true);
});

window.addEventListener("popstate", function() {
  navigateToPage(window.location.href, false);
});
