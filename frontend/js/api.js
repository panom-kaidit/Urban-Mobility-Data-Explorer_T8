// Shared API helper used by all dashboard pages (revenue, mobility, main).
// Points to the FastAPI backend running on port 8000.

const API_BASE_URL = "http://localhost:8000/api";

async function fetchJSON(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${endpoint} (status ${response.status})`);
  }
  return response.json();
}