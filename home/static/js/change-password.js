(() => {
    const form = document.getElementById('password-change-form');
    const dialog = document.getElementById('password-confirm');
    const save = document.getElementById('password-save');
    const label = document.getElementById('password-save-label');
    const spinner = save.querySelector('.password-spinner');
    let confirmed = false;
    let saving = false;

    const toggles = form.querySelectorAll('.password-toggle');
    const hidePasswords = () => {
        toggles.forEach((toggle) => {
            document.getElementById(toggle.getAttribute('aria-controls')).type = 'password';
            toggle.setAttribute('aria-pressed', 'false');
            toggle.setAttribute('aria-label', `Show ${toggle.dataset.fieldLabel}`);
            toggle.classList.remove('is-visible');
        });
    };
    toggles.forEach((toggle) => {
        toggle.hidden = false;
        toggle.addEventListener('click', () => {
            const input = document.getElementById(toggle.getAttribute('aria-controls'));
            const visible = input.type === 'password';
            input.type = visible ? 'text' : 'password';
            toggle.setAttribute('aria-pressed', String(visible));
            toggle.setAttribute('aria-label', `${visible ? 'Hide' : 'Show'} ${toggle.dataset.fieldLabel}`);
            toggle.classList.toggle('is-visible', visible);
        });
    });

    form.addEventListener('submit', (event) => {
        if (saving) {
            event.preventDefault();
            return;
        }
        if (!confirmed) {
            event.preventDefault();
            dialog.showModal();
            return;
        }
        saving = true;
        hidePasswords();
        save.disabled = true;
        form.setAttribute('aria-busy', 'true');
        spinner.hidden = false;
        label.textContent = 'Saving password…';
    });
    document.getElementById('password-cancel').addEventListener('click', () => dialog.close());
    document.getElementById('password-confirm-save').addEventListener('click', () => {
        dialog.close();
        confirmed = true;
        form.requestSubmit();
        confirmed = false;
    });
    window.addEventListener('pageshow', () => {
        hidePasswords();
        saving = false;
        confirmed = false;
        save.disabled = false;
        spinner.hidden = true;
        label.textContent = 'Save New Password';
        form.removeAttribute('aria-busy');
    });
})();
