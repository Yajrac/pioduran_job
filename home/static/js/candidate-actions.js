document.querySelectorAll('.candidate-actions-toggle').forEach(function (button) {
    const menu = document.getElementById(button.getAttribute('aria-controls'));
    function position() {
        const box = button.getBoundingClientRect();
        menu.style.left = Math.max(8, Math.min(box.right - 210, innerWidth - 218)) + 'px';
        const height = menu.getBoundingClientRect().height;
        menu.style.top = Math.max(8, box.bottom + height + 8 > innerHeight ? box.top - height - 6 : box.bottom + 6) + 'px';
    }
    menu.addEventListener('toggle', function (event) {
        button.setAttribute('aria-expanded', String(event.newState === 'open'));
        if (event.newState === 'open') position();
    });
    function close() { if (menu.matches(':popover-open')) menu.hidePopover(); }
    window.addEventListener('resize', close);
    document.addEventListener('scroll', event => { if (!menu.contains(event.target)) close(); }, true);
});
