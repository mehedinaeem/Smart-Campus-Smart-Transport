(function () {
    const app = document.querySelector("[data-tracking-app]");
    const payloadScript = document.getElementById("tracking-payload");
    if (!app || !payloadScript || typeof L === "undefined") {
        return;
    }

    const initialState = JSON.parse(payloadScript.textContent);
    const feedUrl = app.dataset.feedUrl;
    const overlay = document.getElementById("tracking-map-overlay");
    const routeLabel = document.getElementById("tracking-route-label");
    const statusChip = document.getElementById("tracking-status-chip");
    const busCode = document.getElementById("tracking-bus-code");
    const busRoute = document.getElementById("tracking-bus-route");
    const speed = document.getElementById("tracking-speed");
    const eta = document.getElementById("tracking-eta");
    const lastUpdate = document.getElementById("tracking-last-update");
    const tripStatus = document.getElementById("tracking-trip-status");
    const panelTitle = document.getElementById("tracking-panel-title");
    const driver = document.getElementById("tracking-driver");
    const windowText = document.getElementById("tracking-window");
    const occupancy = document.getElementById("tracking-occupancy");
    const ignition = document.getElementById("tracking-ignition");
    const coordinates = document.getElementById("tracking-coordinates");
    const stopsList = document.getElementById("tracking-stops-list");
    const vehicleList = document.getElementById("tracking-vehicle-list");

    const map = L.map("live-tracking-map", {
        zoomControl: false,
        attributionControl: true,
    }).setView([23.8103, 90.4125], 12);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const busIcon = L.divIcon({
        className: "",
        html: '<div class="tracking-bus-marker"><span>BUS</span></div>',
        iconSize: [42, 42],
        iconAnchor: [21, 21],
    });

    const stopIcon = L.divIcon({
        className: "",
        html: '<div class="tracking-stop-marker"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
    });

    let state = initialState;
    let selectedAssignmentId = initialState.selected_assignment_id || null;
    let routeLine = null;
    let stopLayer = L.layerGroup().addTo(map);
    let markers = new Map();
    let selectedPopup = null;
    let mapHasBeenFit = false;

    function getVehicleById(assignmentId, vehicles) {
        return vehicles.find((item) => item.assignment_id === assignmentId) || null;
    }

    function ensureMarker(vehicle) {
        let marker = markers.get(vehicle.assignment_id);
        if (!marker) {
            marker = L.marker([vehicle.latitude || 0, vehicle.longitude || 0], { icon: busIcon, keyboard: false });
            marker.on("click", () => {
                selectedAssignmentId = vehicle.assignment_id;
                render(state);
            });
            marker.addTo(map);
            markers.set(vehicle.assignment_id, marker);
        }

        if (vehicle.latitude !== null && vehicle.longitude !== null) {
            marker.setLatLng([vehicle.latitude, vehicle.longitude]);
        }

        const popupHtml = `
            <div class="tracking-popup">
                <strong>${vehicle.bus_code}</strong>
                <p>${vehicle.route_label}</p>
                <span>${vehicle.live_status} • ${vehicle.speed_kph !== null ? `${vehicle.speed_kph.toFixed(0)} km/h` : "Speed pending"}</span>
            </div>
        `;
        marker.bindPopup(popupHtml, { closeButton: false, offset: [0, -18] });
        return marker;
    }

    function syncMarkers(vehicles) {
        const activeIds = new Set(vehicles.map((vehicle) => vehicle.assignment_id));
        vehicles.forEach((vehicle) => {
            if (vehicle.latitude === null || vehicle.longitude === null) {
                return;
            }
            ensureMarker(vehicle);
        });

        markers.forEach((marker, assignmentId) => {
            if (!activeIds.has(assignmentId)) {
                map.removeLayer(marker);
                markers.delete(assignmentId);
            }
        });
    }

    function renderVehicleList(vehicles) {
        if (!vehicleList) {
            return;
        }

        if (!vehicles.length) {
            vehicleList.innerHTML = `
                <div class="tracking-inline-empty">
                    <strong>No active or upcoming trips.</strong>
                    <p>Completed or cancelled trips are intentionally excluded from live tracking.</p>
                </div>
            `;
            return;
        }

        vehicleList.innerHTML = vehicles.map((vehicle) => `
            <button
                type="button"
                class="timeline-stop tracking-trip-row ${vehicle.assignment_id === selectedAssignmentId ? "active" : ""}"
                data-assignment-option
                data-assignment-id="${vehicle.assignment_id}"
            >
                <div class="timeline-dot"></div>
                <div>
                    <strong>${vehicle.route_label}</strong>
                    <p>${vehicle.bus_code} | ${vehicle.start_time} | ${vehicle.live_status}</p>
                </div>
            </button>
        `).join("");

        vehicleList.querySelectorAll("[data-assignment-option]").forEach((button) => {
            button.addEventListener("click", () => {
                selectedAssignmentId = Number.parseInt(button.dataset.assignmentId, 10);
                render(state);
                history.replaceState({}, "", `${window.location.pathname}?assignment=${selectedAssignmentId}`);
            });
        });
    }

    function renderStops(vehicle) {
        if (!stopsList) {
            return;
        }

        if (!vehicle || !vehicle.stops.length) {
            stopsList.innerHTML = `
                <div class="tracking-inline-empty">
                    <strong>No stop coordinates yet.</strong>
                    <p>Add route stops in the admin to unlock stop sequencing and route polyline rendering.</p>
                </div>
            `;
            return;
        }

        stopsList.innerHTML = vehicle.stops.map((stop, index) => `
            <div class="timeline-stop ${index === 0 ? "is-highlighted" : ""}">
                <div class="timeline-dot"></div>
                <div>
                    <strong>${stop.name}</strong>
                    <p>${stop.eta_label}</p>
                </div>
            </div>
        `).join("");
    }

    function updateDetails(vehicle) {
        if (!vehicle) {
            routeLabel.textContent = "No active or upcoming trips";
            statusChip.textContent = "Unavailable";
            statusChip.className = "status-chip";
            busCode.textContent = "--";
            busRoute.textContent = "Waiting for assigned trips";
            speed.textContent = "--";
            eta.textContent = "--";
            lastUpdate.textContent = "No telemetry yet";
            tripStatus.textContent = "Trips appear here once assigned";
            panelTitle.textContent = "No live vehicle selected";
            driver.textContent = "Unassigned";
            windowText.textContent = "--";
            occupancy.textContent = "--";
            ignition.textContent = "Unknown";
            coordinates.textContent = "Waiting for GPS fix";
            renderStops(null);
            return;
        }

        routeLabel.textContent = vehicle.route_label;
        statusChip.textContent = vehicle.live_status;
        statusChip.className = `status-chip ${vehicle.live_status_tone || ""}`.trim();
        busCode.textContent = vehicle.bus_code;
        busRoute.textContent = vehicle.route_section;
        speed.textContent = vehicle.speed_kph !== null ? `${vehicle.speed_kph.toFixed(0)} km/h` : "--";
        eta.textContent = vehicle.eta_label;
        lastUpdate.textContent = vehicle.last_reported_label;
        tripStatus.textContent = `Trip ${vehicle.trip_status_label}`;
        panelTitle.textContent = vehicle.bus_label;
        driver.textContent = vehicle.driver_name;
        windowText.textContent = `${vehicle.start_time} - ${vehicle.end_time}`;
        occupancy.textContent = vehicle.occupancy_label;
        ignition.textContent = vehicle.ignition_on === null ? "Unknown" : (vehicle.ignition_on ? "On" : "Off");
        coordinates.textContent = vehicle.latitude !== null && vehicle.longitude !== null
            ? `${vehicle.latitude.toFixed(6)}, ${vehicle.longitude.toFixed(6)}`
            : "Waiting for GPS fix";
        renderStops(vehicle);
    }

    function updateRoute(vehicle) {
        if (routeLine) {
            map.removeLayer(routeLine);
            routeLine = null;
        }
        stopLayer.clearLayers();

        if (!vehicle) {
            return;
        }

        const routePoints = vehicle.route_points
            .filter((point) => Array.isArray(point) && point[0] !== null && point[1] !== null);

        if (routePoints.length >= 2) {
            routeLine = L.polyline(routePoints, {
                color: "#6ec1ff",
                weight: 5,
                opacity: 0.92,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(map);
        }

        vehicle.stops.forEach((stop) => {
            if (stop.latitude === null || stop.longitude === null) {
                return;
            }
            const marker = L.marker([stop.latitude, stop.longitude], { icon: stopIcon, keyboard: false });
            marker.bindTooltip(stop.name, { direction: "top", offset: [0, -8] });
            stopLayer.addLayer(marker);
        });
    }

    function updateMapFocus(vehicles, selectedVehicle) {
        const selectedMarker = selectedVehicle ? markers.get(selectedVehicle.assignment_id) : null;
        if (selectedMarker) {
            selectedMarker.openPopup();
            if (selectedPopup && selectedPopup !== selectedMarker) {
                selectedPopup.closePopup();
            }
            selectedPopup = selectedMarker;
        }

        if (selectedVehicle && selectedVehicle.latitude !== null && selectedVehicle.longitude !== null) {
            map.setView([selectedVehicle.latitude, selectedVehicle.longitude], Math.max(map.getZoom(), 14), { animate: true });
            mapHasBeenFit = true;
            return;
        }

        if (mapHasBeenFit) {
            return;
        }

        const boundsPoints = vehicles
            .filter((vehicle) => vehicle.latitude !== null && vehicle.longitude !== null)
            .map((vehicle) => [vehicle.latitude, vehicle.longitude]);
        if (boundsPoints.length) {
            map.fitBounds(boundsPoints, { padding: [40, 40], maxZoom: 14 });
            mapHasBeenFit = true;
        }
    }

    function render(nextState) {
        state = nextState;
        overlay.hidden = state.has_assignments;
        syncMarkers(state.vehicles);
        renderVehicleList(state.vehicles);

        const selectedVehicle = getVehicleById(selectedAssignmentId, state.vehicles)
            || state.selected_vehicle
            || state.vehicles[0]
            || null;

        if (selectedVehicle) {
            selectedAssignmentId = selectedVehicle.assignment_id;
        } else {
            selectedAssignmentId = null;
        }

        updateDetails(selectedVehicle);
        updateRoute(selectedVehicle);
        updateMapFocus(state.vehicles, selectedVehicle);
    }

    async function refresh() {
        const url = new URL(feedUrl, window.location.origin);
        if (selectedAssignmentId) {
            url.searchParams.set("assignment", selectedAssignmentId);
        }

        try {
            const response = await fetch(url.toString(), {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });
            if (!response.ok) {
                throw new Error(`Tracking refresh failed with ${response.status}`);
            }
            const nextState = await response.json();
            render(nextState);
        } catch (error) {
            console.error(error);
        }
    }

    render(initialState);
    window.setInterval(refresh, 10000);
})();
