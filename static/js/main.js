(function () {
    const body = document.body;
    const authTrigger = document.querySelector("[data-auth-trigger]");
    const authMenu = document.querySelector("[data-auth-menu]");
    const mobileMenuToggle = document.querySelector("[data-mobile-menu-toggle]");
    const mobileMenuClose = document.querySelector("[data-mobile-menu-close]");
    const mobileMenuBackdrop = document.querySelector("[data-mobile-menu-backdrop]");
    const mobileDrawer = document.querySelector("[data-mobile-drawer]");
    const mobileNavLinks = document.querySelectorAll(".sidebar-nav a");

    authTrigger?.addEventListener("click", () => {
        const willOpen = authMenu?.hasAttribute("hidden");
        setAuthMenuOpen(Boolean(willOpen));
    });

    mobileMenuToggle?.addEventListener("click", () => {
        const open = !body.classList.contains("mobile-menu-open");
        setMobileMenuOpen(open);
    });

    mobileMenuClose?.addEventListener("click", () => {
        setMobileMenuOpen(false);
    });

    mobileMenuBackdrop?.addEventListener("click", () => {
        setMobileMenuOpen(false);
    });

    mobileNavLinks.forEach((link) => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 760) {
                setMobileMenuOpen(false);
            }
        });
    });

    document.addEventListener("click", (event) => {
        if (!authTrigger || !authMenu) {
            return;
        }

        if (!authTrigger.closest(".auth-shell")?.contains(event.target)) {
            setAuthMenuOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setAuthMenuOpen(false);
            setMobileMenuOpen(false);
        }
    });

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

    function setMobileMenuOpen(open) {
        if (!mobileDrawer || !mobileMenuToggle || !mobileMenuBackdrop) {
            return;
        }

        body.classList.toggle("mobile-menu-open", open);
        mobileMenuToggle.setAttribute("aria-expanded", open ? "true" : "false");
        mobileDrawer.setAttribute("aria-hidden", open ? "false" : "true");

        if (open) {
            mobileMenuBackdrop.removeAttribute("hidden");
        } else {
            mobileMenuBackdrop.setAttribute("hidden", "hidden");
        }
    }

    window.addEventListener("resize", () => {
        if (window.innerWidth > 760) {
            setMobileMenuOpen(false);
        }
    });

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

    const addAssignmentRowButton = document.querySelector("[data-add-assignment-row]");
    const assignmentList = document.querySelector("[data-assignment-list]");
    const assignmentEmptyTemplate = document.getElementById("assignment-empty-form");
    const totalFormsInput = document.getElementById("id_assignments-TOTAL_FORMS");

    addAssignmentRowButton?.addEventListener("click", () => {
        if (!assignmentList || !assignmentEmptyTemplate || !totalFormsInput) {
            return;
        }

        const index = Number.parseInt(totalFormsInput.value, 10);
        assignmentList.insertAdjacentHTML(
            "beforeend",
            assignmentEmptyTemplate.innerHTML.replace(/__prefix__/g, index),
        );
        totalFormsInput.value = String(index + 1);
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
