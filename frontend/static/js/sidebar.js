document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const desktopToggle = document.getElementById("toggle-sidebar");
    const mobileToggle = document.getElementById("toggle-sidebar-movil");
    if (!sidebar) return;

    const mobileQuery = window.matchMedia("(max-width: 760px)");
    const backdrop = document.createElement("button");
    backdrop.type = "button";
    backdrop.className = "sidebar-backdrop";
    backdrop.setAttribute("aria-label", "Cerrar menú");
    document.body.append(backdrop);

    const setMobileOpen = (open) => {
        document.body.classList.toggle("sidebar-abierto", open);
        mobileToggle?.setAttribute("aria-expanded", String(open));
        mobileToggle?.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
    };

    desktopToggle?.addEventListener("click", () => {
        if (mobileQuery.matches) {
            setMobileOpen(!document.body.classList.contains("sidebar-abierto"));
            return;
        }
        const compressed = sidebar.classList.toggle("comprimido");
        desktopToggle.setAttribute("aria-expanded", String(!compressed));
        desktopToggle.setAttribute("aria-label", compressed ? "Expandir menú" : "Comprimir menú");
    });

    mobileToggle?.addEventListener("click", () => {
        setMobileOpen(!document.body.classList.contains("sidebar-abierto"));
    });
    backdrop.addEventListener("click", () => setMobileOpen(false));
    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            if (mobileQuery.matches) setMobileOpen(false);
        });
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setMobileOpen(false);
    });
    mobileQuery.addEventListener("change", () => setMobileOpen(false));
});
