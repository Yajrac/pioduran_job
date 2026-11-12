document.querySelectorAll('.sidebar-reports details').forEach(function (details) {
    const summary = details.querySelector('summary');
    const submenu = details.querySelector('.reports-submenu');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let animation;
    let expanded = details.open;
    summary.setAttribute('aria-expanded', String(expanded));
    summary.addEventListener('click', function (event) {
        event.preventDefault();
        const start = details.getBoundingClientRect().height;
        if (animation) animation.cancel();
        expanded = !expanded;
        summary.setAttribute('aria-expanded', String(expanded));
        submenu.inert = !expanded;
        details.classList.toggle('is-closing', !expanded);
        details.open = true;
        const end = expanded ? details.getBoundingClientRect().height : summary.getBoundingClientRect().height;
        function finish() {
            details.open = expanded;
            details.classList.remove('is-closing');
            animation = null;
        }
        if (reducedMotion.matches) {
            finish();
            return;
        }
        animation = details.animate([{ height: start + 'px' }, { height: end + 'px' }], {
            duration: 260,
            easing: 'cubic-bezier(.22,1,.36,1)'
        });
        animation.onfinish = finish;
    });
});
