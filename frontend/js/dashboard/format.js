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

function formatShortNumber(value) {
  const number = Number(value || 0);

  if (number >= 1000000) {
    return (number / 1000000).toFixed(1) + "M";
  }

  if (number >= 1000) {
    return (number / 1000).toFixed(0) + "K";
  }

  return number;
}
