(() => {
    const upload = document.getElementById('certificateUploadForm');
    upload.addEventListener('submit', function () {
        const button = upload.querySelector('button[type="submit"]');
        button.disabled = true;
        button.textContent = 'Uploading...';
    });
    const dialog = document.getElementById('certificateDeleteDialog');
    const confirm = document.getElementById('certificateDeleteConfirm');
    const cancel = document.getElementById('certificateDeleteCancel');
    let pending, busy = false;
    document.querySelectorAll('.certificate-delete-form').forEach(form => form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (busy || dialog.open) return;
        pending = form;
        document.getElementById('certificateDeleteText').textContent = 'Permanently delete “' + form.dataset.title + '”? This action cannot be undone.';
        dialog.showModal();
    }));
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    dialog.addEventListener('close', () => { if (!busy) pending = null; });
    confirm.addEventListener('click', function () {
        if (!pending || busy) return;
        busy = true;
        confirm.disabled = cancel.disabled = true;
        confirm.textContent = 'Deleting...';
        HTMLFormElement.prototype.submit.call(pending);
    });
})();
