(() => {
    const form = document.getElementById('applicantAssessmentForm');
    if (!form) return;
    form.noValidate = true;
    const fields = ['skills_score', 'interview_score'].map(name => form.elements[name]);
    const feedback = new Map();
    fields.forEach(function (field) {
        const message = document.createElement('p');
        message.id = field.id + '-feedback';
        message.className = 'assessment-field-feedback';
        message.setAttribute('aria-live', 'polite');
        field.after(message);
        field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'), message.id].filter(Boolean).join(' '));
        feedback.set(field, message);
        field.addEventListener('input', () => {
            const serverErrors = field.parentElement.querySelector('.errorlist');
            if (serverErrors) serverErrors.hidden = true;
            validate(field);
        });
        field.addEventListener('blur', () => validate(field));
    });
    function validate(field) {
        field.setCustomValidity('');
        const value = field.value.trim();
        let error = '';
        if (field.validity.badInput) error = 'Enter a whole number from 0 to 5.';
        else if (value) {
            const score = Number(value);
            if (score < 0) error = 'Score cannot be negative.';
            else if (score > 5) error = 'Score must not exceed 5.';
            else if (!Number.isInteger(score)) error = 'Enter a whole number from 0 to 5.';
        }
        feedback.get(field).textContent = error;
        field.setCustomValidity(error);
        field.setAttribute('aria-invalid', String(Boolean(error)));
        field.classList.toggle('assessment-score-invalid', Boolean(error));
        return !error;
    }
    form.addEventListener('submit', function (event) {
        const invalid = fields.filter(field => !validate(field));
        if (!invalid.length) return;
        event.preventDefault();
        invalid[0].focus();
    });
})();
