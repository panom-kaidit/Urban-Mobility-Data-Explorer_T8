

/* Backend server URL */
const API_BASE_URL = 'http://localhost:8000';

/* ================================================================
   CORE FETCH HELPER
================================================================ */

/**
 * GET request to API. Returns JSON or null.
 *
 * @param {string} path
 * @param {Object} params
 * @returns {Promise<Object|null>}
 */
async function apiGet(path, params = {}) {
  /* Build URL */
  const url = new URL(API_BASE_URL + path);

  /* Add query params */
  Object.entries(params).forEach(function([key, value]) {
    if (value !== null && value !== undefined && value !== '') {
      url.searchParams.append(key, value);
    }
  });

  try {
    const response = await fetch(url.toString());

    if (!response.ok) {
      const body = await response.json().catch(function() { return {}; });
      throw new Error(body.detail || 'HTTP ' + response.status);
    }

    return await response.json();

  } catch (error) {
    console.error('[API] Error fetching ' + path + ':', error.message);
    return null;
  }
}

/* TRIPS ENDPOINTS */

/**
 * Fetch trips with optional filters.
 *
 * @param {Object} filters
 * @returns {Promise<{items: Array, count: number, limit: number, offset: number}|null>}
 */
async function fetchTrips(filters) {
  filters = filters || {};
  return await apiGet('/api/trips', filters);
}

/**
 * Fetch one trip by ID.
 *
 * @param {number} tripId
 * @returns {Promise<Object|null>}
 */
async function fetchTripById(tripId) {
  return await apiGet('/api/trips/' + tripId);
}

/* ANALYTICS ENDPOINTS */

/**
 * Fetch top pickup zones by trip count.
 *
 * @param {number} topN
 * @returns {Promise<{algorithm: string, top_n: number, zones: Array}|null>}
 */
async function fetchTopPickupZones(topN) {
  topN = topN || 10;
  return await apiGet('/api/analytics/top-pickup-zones', { top_n: topN });
}

/**
 * Fetch fare distribution buckets.
 *
 * @returns {Promise<{distribution: Array}|null>}
 */
async function fetchFareDistribution() {
  return await apiGet('/api/analytics/fare-distribution');
}

/* ZONE / LOCATION ENDPOINTS */

/**
 * Fetch info for a taxi zone.
 *
 * @param {number} zoneId
 * @returns {Promise<Object|null>}
 */
async function fetchZone(zoneId) {
  return await apiGet('/api/zones/' + zoneId);
}

/* DASHBOARD SUMMARY HELPER */

/**
 * Estimate dashboard stats from a sample.
 *
 * @param {Object} filters
 * @returns {Promise<{totalTrips: number, totalRevenue: number, avgFare: number, avgDistance: number}>}
 */
async function fetchDashboardStats(filters) {
  filters = filters || {};

  var data = await fetchTrips(Object.assign({}, filters, { limit: 500 }));

  if (!data || !data.items || data.items.length === 0) {
    return { totalTrips: 0, totalRevenue: 0, avgFare: 0, avgDistance: 0 };
  }

  var trips      = data.items;
  var totalTrips = data.count;
  var sampleSize = trips.length;

  var sumRevenue  = 0;
  var sumFare     = 0;
  var sumDistance = 0;

  for (var i = 0; i < sampleSize; i++) {
    sumRevenue  += trips[i].total_amount  || 0;
    sumFare     += trips[i].fare_amount   || 0;
    sumDistance += trips[i].trip_distance || 0;
  }

  var avgRevenue  = sumRevenue  / sampleSize;
  var avgFare     = sumFare     / sampleSize;
  var avgDistance = sumDistance / sampleSize;

  var estimatedTotalRevenue = avgRevenue * totalTrips;

  return {
    totalTrips:   totalTrips,
    totalRevenue: estimatedTotalRevenue,
    avgFare:      avgFare,
    avgDistance:  avgDistance
  };
}

