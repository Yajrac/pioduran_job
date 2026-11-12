(() => {
    const dialog = document.getElementById('applicationResponseDialog');
    const confirm = document.getElementById('applicationResponseConfirm');
    const cancel = document.getElementById('applicationResponseCancel');
    let pending, action, busy = false;
    document.querySelectorAll('.application-response-form').forEach(form => form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (busy || dialog.open || !event.submitter) return;
        pending = form;
        action = event.submitter.value;
        const labels = {withdraw:'Withdraw application', accept:'Accept offer', decline:'Decline offer'};
        document.getElementById('applicationResponseTitle').textContent = labels[action] + '?';
        document.getElementById('applicationResponseText').textContent = labels[action] + ' for “' + form.dataset.job + '”? ' + (action === 'accept' ? 'Your status will become Hired.' : 'This action cannot be undone.');
        confirm.textContent = labels[action];
        dialog.showModal();
    }));
    cancel.addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
    dialog.addEventListener('close', () => { if (!busy) pending = null; });
    confirm.addEventListener('click', function () {
        if (!pending || busy) return;
        busy = true;
        confirm.disabled = cancel.disabled = true;
        confirm.textContent = 'Processing...';
        const input = document.createElement('input');
        input.type = 'hidden'; input.name = 'action'; input.value = action;
        pending.append(input);
        HTMLFormElement.prototype.submit.call(pending);
    });
})();
