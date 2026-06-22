// Small client-side router for the dashboard pages.
// It keeps the sidebar/navbar mounted and swaps only the page content.

var _routeLoading = false;

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

  try {
    var response = await fetch(pageUrl);
    if (!response.ok) throw new Error("Could not load page");

    var html = await response.text();
    var pageDocument = new DOMParser().parseFromString(html, "text/html");
    var nextContent = pageDocument.querySelector(".content-inner");
    if (!nextContent) throw new Error("Page content was not found");

    await _loadStyles(pageDocument, pageUrl);
    await _loadPageScripts(pageDocument, pageUrl);

    var currentContent = document.querySelector(".content-inner");
    var mainContent = currentContent.parentElement;
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
    if (addHistory) history.pushState({}, "", pageUrl);

    var pageName = new URL(pageUrl).pathname.split("/").pop();
    var initializerName = PAGE_INITIALIZERS[pageName];
    var initializer = initializerName ? window[initializerName] : null;
    if (typeof initializer !== "function") throw new Error("Page initializer was not found");

    await initializer();
    await _waitForFirstLayout();

    nextContent.style.position = "";
    nextContent.style.top = "";
    nextContent.style.left = "";
    nextContent.style.right = "";
    nextContent.style.visibility = "visible";
    currentContent.remove();
    mainContent.style.height = "";
    mainContent.style.overflow = "";
    mainContent.style.boxSizing = "";
    window.scrollTo(0, 0);
  } catch (error) {
    console.error("Client navigation failed:", error);
    window.location.href = pageUrl;
  } finally {
    _routeLoading = false;
  }
}

document.addEventListener("click", function(event) {
  var link = event.target.closest(".sidebar-link");
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey) return;

  event.preventDefault();
  navigateToPage(link.href, true);
});

window.addEventListener("popstate", function() {
  navigateToPage(window.location.href, false);
});
