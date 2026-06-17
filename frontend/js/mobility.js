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

function renderTopDropoffChart(zones) {
    const chartCanvas = document.getElementById("topDropoffZonesChart");
    const labels = zones.map((item) => item.dropoff_zone);
    const values = zones.map((item) => item.trip_count);

    new Chart(chartCanvas, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Trip Count",
                    data: values,
                    backgroundColor: "#2874a6",
                    borderRadius: 4,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Trip Count",
                    },
                    beginAtZero: true,
                },
                y: {
                    title: {
                        display: true,
                        text: "Dropoff Zone",
                    },
                },
            },
        },
    });
}

function renderAverageDistanceChart(hours) {
    const chartCanvas = document.getElementById("averageDistanceChart");
    const labels = hours.map((item) => item.pickup_hour);
    const values = hours.map((item) => item.average_distance);

    new Chart(chartCanvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Average Distance (Miles)",
                    data: values,
                    borderColor: "#1e8449",
                    backgroundColor: "rgba(30, 132, 73, 0.12)",
                    fill: true,
                    tension: 0.25,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Pickup Hour",
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: "Average Distance (Miles)",
                    },
                    beginAtZero: true,
                },
            },
        },
    });
}
