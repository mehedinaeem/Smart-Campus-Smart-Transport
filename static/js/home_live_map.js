(function () {
    const mapElement = document.querySelector("[data-home-live-map]");
    const payloadScript = document.getElementById("home-live-fleet-data");
    if (!mapElement || !payloadScript || typeof L === "undefined") {
        return;
    }

    const liveFleet = JSON.parse(payloadScript.textContent);
    if (liveFleet.latitude === null || liveFleet.longitude === null) {
        return;
    }

    const map = L.map(mapElement, {
        zoomControl: false,
        attributionControl: false,
        dragging: true,
        scrollWheelZoom: false,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19,
        subdomains: "abcd",
    }).addTo(map);

    const busIcon = L.divIcon({
        className: "",
        html: '<div class="tracking-bus-marker"><span class="tracking-bus-marker__dot"></span></div>',
        iconSize: [28, 28],
        iconAnchor: [14, 28],
    });

    const stopIcon = L.divIcon({
        className: "",
        html: '<div class="tracking-stop-marker"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
    });

    const busMarker = L.marker([liveFleet.latitude, liveFleet.longitude], {
        icon: busIcon,
        keyboard: false,
    }).addTo(map);

    busMarker.bindPopup(
        `
            <div class="tracking-popup">
                <strong>${liveFleet.bus_label || "Bus"}</strong>
                <p>${liveFleet.route_label || "Live route"}</p>
                <span>${liveFleet.current_location || "GPS live"}</span>
            </div>
        `,
        { closeButton: false, offset: [0, -18] }
    ).openPopup();

    const bounds = [];

    if (Array.isArray(liveFleet.route_points)) {
        const routePoints = liveFleet.route_points.filter((point) => (
            Array.isArray(point) && point[0] !== null && point[1] !== null
        ));

        if (routePoints.length >= 2) {
            L.polyline(routePoints, {
                color: "#6ec1ff",
                weight: 4,
                opacity: 0.9,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(map);
            bounds.push(...routePoints);
        }
    }

    if (Array.isArray(liveFleet.stops_payload)) {
        liveFleet.stops_payload.forEach((stop) => {
            if (stop.latitude === null || stop.longitude === null) {
                return;
            }
            L.marker([stop.latitude, stop.longitude], { icon: stopIcon, keyboard: false })
                .addTo(map)
                .bindTooltip(stop.name, { direction: "top", offset: [0, -8] });
            bounds.push([stop.latitude, stop.longitude]);
        });
    }

    bounds.push([liveFleet.latitude, liveFleet.longitude]);

    if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [32, 32], maxZoom: 15 });
    } else {
        map.setView([liveFleet.latitude, liveFleet.longitude], 15);
    }

    window.setTimeout(() => map.invalidateSize(), 120);
})();
