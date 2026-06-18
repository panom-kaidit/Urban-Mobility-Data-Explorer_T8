const API_BASE_URL = "http://localhost:8000/api";

async function apiGet(endpoint) {
  const response = await fetch(API_BASE_URL + endpoint);

  if (!response.ok) {
    throw new Error("Request failed: " + endpoint + " (" + response.status + ")");
  }

  return response.json();
}
