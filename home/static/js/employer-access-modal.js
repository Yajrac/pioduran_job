(() => {
    const dialog = document.getElementById('employerAccessDialog');
    const paths = new Set([dialog.dataset.jobsUrl, dialog.dataset.dashboardUrl, dialog.dataset.postUrl, dialog.dataset.applicantsUrl]);
    document.addEventListener('click', function (event) {
        const link = event.target.closest('a[href]');
        if (!link) return;
        const target = new URL(link.href, location.href);
        if (target.origin !== location.origin || !paths.has(target.pathname)) return;
        event.preventDefault();
        if (!dialog.open) dialog.showModal();
    }, true);
    document.getElementById('employerAccessClose').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', function (event) {
        if (event.target !== dialog) return;
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
})();
