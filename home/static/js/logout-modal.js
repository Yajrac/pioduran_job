(() => {
    const dialog = document.getElementById('portalLogoutDialog');
    const cancel = document.getElementById('portalLogoutCancel');
    const confirm = document.getElementById('portalLogoutConfirm');
    let destination = null;
    let busy = false;
    document.addEventListener('click', function (event) {
        const link = event.target.closest('a[data-portal-logout]');
        if (!link) return;
        event.preventDefault();
        if (busy || dialog.open) return;
        destination = link.href;
        dialog.showModal();
    });
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    dialog.addEventListener('close', () => { if (!busy) destination = null; });
    dialog.addEventListener('click', function (event) {
        if (busy || event.target !== dialog) return;
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
    confirm.addEventListener('click', function () {
        if (!destination || busy) return;
        busy = true;
        confirm.disabled = cancel.disabled = true;
        confirm.textContent = 'Logging out...';
        dialog.setAttribute('aria-busy', 'true');
        window.location.assign(destination);
    });
    window.addEventListener('pageshow', function () {
        busy = false;
        destination = null;
        confirm.disabled = cancel.disabled = false;
        confirm.textContent = 'Log Out';
        dialog.removeAttribute('aria-busy');
        if (dialog.open) dialog.close();
    });
})();
