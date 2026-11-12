(() => {
    const toggle = document.getElementById('sidebarCollapseToggle');
    const sidebar = document.getElementById('pesoSidebar');
    const desktop = matchMedia('(min-width:769px)');
    let collapsed = false;
    try { collapsed = localStorage.getItem('peso-sidebar-collapsed') === 'true'; } catch (_) {}
    sidebar.querySelectorAll('.sidebar-menu-item a,.sidebar-reports summary').forEach(item => {
        const label = item.textContent.trim().replace(/\s+/g, ' ');
        item.setAttribute('aria-label', label);
        item.title = label;
    });
    function render() {
        const active = collapsed && desktop.matches;
        document.body.classList.toggle('sidebar-collapsed', active);
        toggle.setAttribute('aria-expanded', String(!active));
        toggle.setAttribute('aria-label', active ? 'Expand sidebar' : 'Collapse sidebar');
        toggle.title = active ? 'Expand sidebar' : 'Collapse sidebar';
    }
    toggle.addEventListener('click', function () {
        collapsed = !collapsed;
        try { localStorage.setItem('peso-sidebar-collapsed', String(collapsed)); } catch (_) {}
        render();
    });
    sidebar.querySelector('.sidebar-reports summary').addEventListener('click', function () {
        if (collapsed && desktop.matches) {
            collapsed = false;
            try { localStorage.setItem('peso-sidebar-collapsed', 'false'); } catch (_) {}
            render();
        }
    }, true);
    desktop.addEventListener('change', render);
    render();
    requestAnimationFrame(() => requestAnimationFrame(() => {
        document.body.classList.remove('sidebar-initializing');
    }));
})();
