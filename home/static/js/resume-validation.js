(() => {
    const endpoint = document.currentScript.dataset.url;
    document.querySelectorAll('input[type="file"][name="resume"]').forEach(function (field) {
        const form = field.form;
        const feedback = document.createElement('p');
        feedback.id = 'resume-content-feedback';
        feedback.setAttribute('aria-live', 'polite');
        feedback.style.cssText = 'font-size:12px;line-height:1.6;margin-top:8px';
        field.after(feedback);
        field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'), feedback.id].filter(Boolean).join(' '));
        let revision = 0;
        let pending = false;
        let error = '';
        field.addEventListener('change', async function () {
            const version = ++revision;
            error = '';
            pending = false;
            field.setCustomValidity('');
            field.removeAttribute('aria-invalid');
            field.style.removeProperty('border-color');
            feedback.textContent = '';
            if (!field.files.length) return;
            pending = true;
            feedback.style.color = '#626976';
            feedback.textContent = 'Checking résumé...';
            const data = new FormData();
            data.append('resume', field.files[0]);
            const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
            try {
                const response = await fetch(endpoint, {method:'POST', body:data, headers:{'X-CSRFToken':csrf}, credentials:'same-origin'});
                if (!response.ok) throw new Error();
                const result = await response.json();
                if (version !== revision) return;
                error = result.error;
                feedback.textContent = result.error || result.warning || 'Résumé check complete.';
                feedback.style.color = error ? '#b83f39' : result.warning ? '#94671e' : '#27406b';
                field.setCustomValidity(error);
                field.setAttribute('aria-invalid', String(Boolean(error)));
                if (error) {
                    field.style.borderColor = '#b83f39';
                    field.value = '';
                    const label = document.getElementById('resumeSelectedName') || document.getElementById('resume-selected');
                    if (label) label.textContent = 'No file selected';
                }
            } catch (_) {
                if (version === revision) {
                    error = 'Unable to check this file. Please select it again to retry.';
                    feedback.textContent = error;
                    feedback.style.color = '#b83f39';
                }
            } finally {
                if (version === revision) pending = false;
            }
        });
        form.addEventListener('submit', function (event) {
            if (!pending && !error) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            feedback.textContent = pending ? 'Checking résumé. Please wait.' : error;
            field.focus();
        }, true);
    });
})();
