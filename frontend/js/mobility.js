const API_BASE_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
    loadTopDropoffZones();
    loadAverageDistance();
});

async function loadTopDropoffZones() {
    const statusElement = document.getElementById("dropoffStatus");

    try {
        const data = await fetchJson(`${API_BASE_URL}/api/analytics/top-dropoff-zones?top_n=10`);
        const zones = data.zones || [];

        if (zones.length === 0) {
            statusElement.textContent = "No dropoff zone data available.";
            return;
        }

        renderTopDropoffChart(zones);
        statusElement.textContent = "";
    } catch (error) {
        statusElement.textContent = "Could not load top dropoff zones.";
        console.error(error);
    }
}

async function loadAverageDistance() {
    const statusElement = document.getElementById("distanceStatus");

    try {
        const data = await fetchJson(`${API_BASE_URL}/api/analytics/average-distance`);
        const hours = data.hours || [];

        if (hours.length === 0) {
            statusElement.textContent = "No hourly distance data available.";
            return;
        }

        renderAverageDistanceChart(hours);
        statusElement.textContent = "";
    } catch (error) {
        statusElement.textContent = "Could not load average distance data.";
        console.error(error);
    }
}

async function fetchJson(url) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }

    return response.json();
}

