// Applicants list: "View details" opens the match/likelihood/benchmark modal for that row.
document.addEventListener('click', function (event) {
    var opener = event.target.closest('.jm-details-open');
    if (opener) {
        var dialog = document.getElementById(opener.dataset.dialog);
        if (dialog && !dialog.open) dialog.showModal();
        return;
    }
    var modal = event.target.closest('.jm-modal');
    if (!modal) return;
    // Close on the X button, or on a click on the backdrop (outside the box).
    if (event.target.closest('[data-close]') || event.target === modal) modal.close();
});
