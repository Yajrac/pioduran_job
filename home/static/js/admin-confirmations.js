(() => {
    const dialog = document.getElementById('adminConfirmDialog');
    const proceed = document.getElementById('adminConfirmProceed');
    const cancel = document.getElementById('adminConfirmCancel');
    let pending = null;
    let busy = false;
    function open(title, message, label, action, danger = false) {
        if (dialog.open || busy) return;
        document.getElementById('adminConfirmTitle').textContent = title;
        document.getElementById('adminConfirmDescription').textContent = message;
        proceed.textContent = label;
        proceed.classList.toggle('confirm-danger-delete', danger);
        dialog.classList.toggle('confirming-deletion', danger);
        pending = action;
        dialog.showModal();
    }
    document.addEventListener('click', function (event) {
        const link = event.target.closest('[data-confirm-approve],[data-confirm-logout]');
        if (!link) return;
        event.preventDefault();
        if (link.hasAttribute('data-confirm-logout')) {
            open('Log out?', 'You will be signed out of the admin portal.', 'Log Out', () => window.location.assign(link.href));
        } else {
            open('Approve job post?', 'Approve and publish “' + link.dataset.jobTitle + '” on the job portal?', 'Approve & Publish', function () {
                const form = document.getElementById('adminConfirmForm');
                form.action = link.href;
                HTMLFormElement.prototype.submit.call(form);
            });
        }
    });
    document.addEventListener('submit', function (event) {
        if (event.target.id === 'deleteApplicantsForm') {
            event.preventDefault();
            event.stopImmediatePropagation();
            const form = event.target;
            const selected = form.querySelectorAll('.applicant-checkbox:checked');
            if (!selected.length) return;
            const count = selected.length;
            open('Delete selected applicants?', 'Permanently delete ' + count + ' selected applicant' + (count === 1 ? '' : 's') + '? This action cannot be undone.', 'Delete ' + count + ' Applicant' + (count === 1 ? '' : 's'), () => HTMLFormElement.prototype.submit.call(form), true);
            return;
        }
        if (event.target.id !== 'authorizeForm') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const form = event.target;
        open('Approve job post?', 'Publish this reviewed job post on the public job portal?', 'Approve & Publish', () => HTMLFormElement.prototype.submit.call(form));
    }, true);
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    dialog.addEventListener('close', () => { if (!busy) pending = null; });
    dialog.addEventListener('click', function (event) {
        if (event.target !== dialog || busy) return;
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
    proceed.addEventListener('click', function () {
        if (!pending || busy) return;
        busy = true;
        proceed.disabled = cancel.disabled = true;
        proceed.textContent = 'Please wait...';
        dialog.setAttribute('aria-busy', 'true');
        pending();
    });
})();
