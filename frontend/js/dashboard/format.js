function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-US");
}

function formatMoney(value) {
  return "$" + Number(value || 0).toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
}

function formatDecimal(value, digits) {
  return Number(value || 0).toLocaleString("en-US", {
    maximumFractionDigits: digits,
  });
}

function formatMetric(value, metricName) {
  if (metricName === "total_revenue" || metricName === "avg_fare") {
    return formatMoney(value);
  }

  if (metricName === "avg_distance") {
    return formatDecimal(value, 2) + " mi";
  }

  return formatNumber(value);
}
