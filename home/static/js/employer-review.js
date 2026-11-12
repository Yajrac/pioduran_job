(() => {
    const form = document.getElementById('employerReviewForm');
    if (!form) return;
    const dialog = document.getElementById('employerReviewDialog');
    const remarks = form.querySelector('textarea');
    const confirm = document.getElementById('employerReviewConfirm');
    const cancel = document.getElementById('employerReviewCancel');
    let decision, busy = false;
    remarks.addEventListener('input', () => remarks.setCustomValidity(''));
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (busy || dialog.open || !event.submitter) return;
        decision = event.submitter.value;
        if (decision === 'rejected' && !remarks.value.trim()) {
            remarks.setCustomValidity('Provide a rejection reason.'); remarks.reportValidity(); return;
        }
        document.getElementById('employerReviewText').textContent = decision === 'approved' ? 'Approve this employer and enable their account?' : 'Reject this employer registration? The employer will see your remarks.';
        dialog.showModal();
    });
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    confirm.addEventListener('click', function () {
        if (busy) return;
        busy = true; confirm.disabled = cancel.disabled = true; confirm.textContent = 'Saving...';
        const input = document.createElement('input'); input.type = 'hidden'; input.name = 'decision'; input.value = decision; form.append(input);
        HTMLFormElement.prototype.submit.call(form);
    });
})();
