(() => {
    const dialog = document.getElementById('assessmentSavedDialog');
    dialog.showModal();
    dialog.addEventListener('close', () => window.location.assign(dialog.dataset.returnUrl));
})();
