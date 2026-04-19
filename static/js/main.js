(function () {
    const appShell = document.querySelector(".app-shell");
    const pageName = appShell?.dataset.pageName || "dashboard";
    const defaultRole = appShell?.dataset.defaultRole || "student";
    const adminOnlyPages = new Set(["admin", "alerts", "analytics"]);
    const storageKey = "smart-campus-auth";

    const sidebarNav = document.querySelector(".sidebar-nav-single");
    const authShell = document.querySelector("[data-auth-shell]");
    const authTrigger = document.querySelector("[data-auth-trigger]");
    const authMenu = document.querySelector("[data-auth-menu]");
    const authLabel = document.querySelector("[data-auth-label]");
    const authAvatar = document.querySelector("[data-auth-avatar]");
    const authPanels = document.querySelectorAll("[data-auth-panel]");
    const loginButtons = document.querySelectorAll("[data-login-role]");
    const switchRoleLinks = document.querySelectorAll("[data-switch-role]");
    const logoutButton = document.querySelector("[data-logout]");
    const profileName = document.querySelector("[data-profile-name]");
    const profileRole = document.querySelector("[data-profile-role]");
    const profileAvatar = document.querySelector("[data-profile-avatar]");
    const studentHomeLink = document.querySelector('[href="/"]');
    const adminLink = document.querySelector('[href="/admin/"]');

    const profileCopy = {
        student: {
            label: "Student Profile",
            name: "Student User",
            role: "Student Access",
            avatar: "S",
        },
        admin: {
            label: "Admin Profile",
            name: "Operations Admin",
            role: "Admin Access",
            avatar: "A",
        },
    };

    let authState = loadAuthState();

    if (adminOnlyPages.has(pageName) && authState.role !== "admin") {
        authState = { loggedIn: true, role: "admin" };
        persistAuthState();
    }

    applyAuthState();

    authTrigger?.addEventListener("click", () => {
        const willOpen = authMenu?.hasAttribute("hidden");
        setAuthMenuOpen(Boolean(willOpen));
    });

    loginButtons.forEach((button) => {
        button.addEventListener("click", () => {
            authState = {
                loggedIn: true,
                role: button.dataset.loginRole === "admin" ? "admin" : "student",
            };
            persistAuthState();
            applyAuthState();
            setAuthMenuOpen(false);
        });
    });

    switchRoleLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            const nextRole = link.dataset.switchRole === "admin" ? "admin" : "student";
            authState = { loggedIn: true, role: nextRole };
            persistAuthState();
            applyAuthState();

            if (nextRole === "admin" && adminLink && !adminOnlyPages.has(pageName)) {
                window.location.href = adminLink.getAttribute("href");
                return;
            }

            if (nextRole === "student" && adminOnlyPages.has(pageName) && studentHomeLink) {
                window.location.href = studentHomeLink.getAttribute("href");
                return;
            }

            setAuthMenuOpen(false);
        });
    });

    logoutButton?.addEventListener("click", () => {
        authState = { loggedIn: false, role: "student" };
        persistAuthState();
        applyAuthState();
        setAuthMenuOpen(false);

        if (adminOnlyPages.has(pageName) && studentHomeLink) {
            window.location.href = studentHomeLink.getAttribute("href");
        }
    });

    document.addEventListener("click", (event) => {
        if (!authShell?.contains(event.target)) {
            setAuthMenuOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setAuthMenuOpen(false);
        }
    });

    function loadAuthState() {
        try {
            const parsed = JSON.parse(window.localStorage.getItem(storageKey) || "null");
            if (!parsed || typeof parsed !== "object") {
                return {
                    loggedIn: defaultRole === "admin",
                    role: defaultRole,
                };
            }

            return {
                loggedIn: Boolean(parsed.loggedIn),
                role: parsed.role === "admin" ? "admin" : "student",
            };
        } catch (error) {
            return {
                loggedIn: defaultRole === "admin",
                role: defaultRole,
            };
        }
    }

    function persistAuthState() {
        window.localStorage.setItem(storageKey, JSON.stringify(authState));
    }

    function applyAuthState() {
        const activeRole = authState.loggedIn && authState.role === "admin" ? "admin" : "student";
        sidebarNav?.classList.toggle("is-student", activeRole !== "admin");

        const loggedIn = authState.loggedIn;
        authPanels.forEach((panel) => {
            panel.classList.toggle("is-active", panel.dataset.authPanel === (loggedIn ? "logged-in" : "logged-out"));
        });

        const copy = profileCopy[authState.role];
        if (authLabel) {
            authLabel.textContent = "Login";
        }
        authTrigger?.classList.toggle("is-logged-in", loggedIn);
        if (authAvatar) {
            authAvatar.hidden = !loggedIn;
            authAvatar.textContent = copy.avatar;
        }
        if (profileName) {
            profileName.textContent = copy.name;
        }
        if (profileRole) {
            profileRole.textContent = copy.role;
        }
        if (profileAvatar) {
            profileAvatar.textContent = copy.avatar;
        }
    }

    function setAuthMenuOpen(open) {
        if (!authMenu || !authTrigger) {
            return;
        }

        if (open) {
            authMenu.removeAttribute("hidden");
        } else {
            authMenu.setAttribute("hidden", "hidden");
        }

        authTrigger.setAttribute("aria-expanded", open ? "true" : "false");
    }

    const seats = document.querySelectorAll(".seat-layout .seat:not(:disabled)");
    const activeSeatLabel = document.getElementById("active-seat");
    const confirmButton = document.getElementById("confirm-booking-btn");
    const bookingModal = document.getElementById("booking-modal");
    const selectedSeatLabel = document.getElementById("selected-seat-label");
    const closeModalButton = document.querySelector("[data-close-modal]");
    let selectedSeat = null;

    seats.forEach((seat) => {
        seat.addEventListener("click", () => {
            seats.forEach((item) => item.classList.remove("selected"));
            seat.classList.add("selected");
            selectedSeat = seat.dataset.seatCode;

            if (activeSeatLabel) {
                activeSeatLabel.textContent = `Seat ${selectedSeat} selected`;
            }
        });
    });

    if (confirmButton) {
        confirmButton.addEventListener("click", () => {
            if (!selectedSeat) {
                if (activeSeatLabel) {
                    activeSeatLabel.textContent = "Select any available seat first";
                }
                return;
            }

            if (selectedSeatLabel) {
                selectedSeatLabel.textContent = selectedSeat;
            }

            bookingModal?.classList.add("open");
            bookingModal?.setAttribute("aria-hidden", "false");
        });
    }

    function closeModal() {
        bookingModal?.classList.remove("open");
        bookingModal?.setAttribute("aria-hidden", "true");
    }

    closeModalButton?.addEventListener("click", closeModal);
    bookingModal?.addEventListener("click", (event) => {
        if (event.target === bookingModal) {
            closeModal();
        }
    });

    const busMarkers = document.querySelectorAll(".moving-bus");
    busMarkers.forEach((marker, index) => {
        const phase = index * 0.8;
        const animate = () => {
            const time = Date.now() / 1000 + phase;
            const x = 18 + Math.sin(time * 0.7) * 26 + Math.cos(time * 0.23) * 8;
            const y = 26 + Math.cos(time * 0.9) * 18 + Math.sin(time * 0.35) * 10;
            marker.style.left = `${x}%`;
            marker.style.top = `${y}%`;
            requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
    });

    function renderLineChart(canvasId, points, colorA, colorB) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext("2d");
        const width = canvas.width = canvas.offsetWidth * 2;
        const height = canvas.height = canvas.offsetHeight * 2;
        ctx.scale(2, 2);

        const displayWidth = width / 2;
        const displayHeight = height / 2;
        const padding = 26;
        const maxPoint = Math.max(...points);
        const step = (displayWidth - padding * 2) / (points.length - 1);

        ctx.clearRect(0, 0, displayWidth, displayHeight);
        ctx.strokeStyle = "rgba(255,255,255,0.08)";
        ctx.lineWidth = 1;

        for (let i = 0; i < 4; i += 1) {
            const y = padding + ((displayHeight - padding * 2) / 3) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(displayWidth - padding, y);
            ctx.stroke();
        }

        const gradient = ctx.createLinearGradient(0, 0, displayWidth, 0);
        gradient.addColorStop(0, colorA);
        gradient.addColorStop(1, colorB);

        ctx.beginPath();
        points.forEach((point, index) => {
            const x = padding + step * index;
            const y = displayHeight - padding - (point / maxPoint) * (displayHeight - padding * 2);
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 4;
        ctx.stroke();

        points.forEach((point, index) => {
            const x = padding + step * index;
            const y = displayHeight - padding - (point / maxPoint) * (displayHeight - padding * 2);
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = "#eff5ff";
            ctx.fill();
        });
    }

    function renderBarChart(canvasId, points, colorA, colorB) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            return;
        }

        const ctx = canvas.getContext("2d");
        const width = canvas.width = canvas.offsetWidth * 2;
        const height = canvas.height = canvas.offsetHeight * 2;
        ctx.scale(2, 2);

        const displayWidth = width / 2;
        const displayHeight = height / 2;
        const maxPoint = Math.max(...points);
        const barWidth = 42;
        const gap = 22;
        const startX = 32;

        ctx.clearRect(0, 0, displayWidth, displayHeight);
        const gradient = ctx.createLinearGradient(0, 0, 0, displayHeight);
        gradient.addColorStop(0, colorA);
        gradient.addColorStop(1, colorB);

        points.forEach((point, index) => {
            const heightRatio = point / maxPoint;
            const x = startX + index * (barWidth + gap);
            const y = displayHeight - 26 - heightRatio * (displayHeight - 52);
            const h = displayHeight - 26 - y;

            ctx.fillStyle = "rgba(255,255,255,0.06)";
            ctx.fillRect(x, 20, barWidth, displayHeight - 46);
            ctx.fillStyle = gradient;
            ctx.fillRect(x, y, barWidth, h);
        });
    }

    renderLineChart("usageChart", [120, 188, 164, 242, 280, 324, 302], "#61a8ff", "#9f7bff");
    renderBarChart("fuelChart", [42, 55, 34, 61, 48], "#34d399", "#61a8ff");

    window.addEventListener("resize", () => {
        renderLineChart("usageChart", [120, 188, 164, 242, 280, 324, 302], "#61a8ff", "#9f7bff");
        renderBarChart("fuelChart", [42, 55, 34, 61, 48], "#34d399", "#61a8ff");
    });
})();
