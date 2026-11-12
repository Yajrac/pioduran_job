(() => {
    const form = document.getElementById('workExperienceForm');
    if (form) {
        const current = form.querySelector('#id_is_current');
        const end = form.querySelector('#id_end_date');
        function update() { end.disabled = current.checked; end.required = !current.checked; }
        current.addEventListener('change', update);
        update();
        form.addEventListener('submit', function () {
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true; button.textContent = 'Saving...';
        });
    }
    const dialog = document.getElementById('experienceDeleteDialog');
    if (!dialog) return;
    let pending, busy = false;
    const cancel = document.getElementById('experienceDeleteCancel');
    const confirm = document.getElementById('experienceDeleteConfirm');
    document.querySelectorAll('.experience-delete-form').forEach(form => form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (busy || dialog.open) return;
        pending = form;
        document.getElementById('experienceDeleteText').textContent = 'Delete “' + form.dataset.title + '” from your profile?';
        dialog.showModal();
    }));
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { if (!busy) pending = null; });
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    confirm.addEventListener('click', function () {
        if (!pending || busy) return;
        busy = true; confirm.disabled = cancel.disabled = true;
        confirm.textContent = 'Deleting...';
        HTMLFormElement.prototype.submit.call(pending);
    });
})();
