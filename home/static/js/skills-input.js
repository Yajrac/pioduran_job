(() => {
    const source = document.getElementById('skills');
    const editor = document.getElementById('skills-editor');
    const input = document.getElementById('skill-entry');
    const tags = document.getElementById('skill-tags');
    const feedback = document.getElementById('skills-feedback');
    const suggestions = document.getElementById('skill-suggestions');
    let skills = source.value.split(',').map(s => s.trim()).filter(Boolean);
    source.hidden = true;
    source.required = false;
    editor.hidden = false;
    suggestions.hidden = false;
    document.querySelector('label[for="skills"]').htmlFor = 'skill-entry';
    function message(text) {
        feedback.textContent = text;
        editor.classList.toggle('skills-invalid', Boolean(text));
        input.setAttribute('aria-invalid', String(Boolean(text)));
    }
    function render() {
        tags.replaceChildren();
        skills.forEach((skill, index) => {
            const tag = document.createElement('li');
            const label = document.createElement('span');
            label.textContent = skill;
            const remove = document.createElement('button');
            remove.type = 'button'; remove.textContent = '\u00d7';
            remove.setAttribute('aria-label', 'Remove ' + skill);
            remove.addEventListener('click', () => {
                skills.splice(index, 1); render(); message(skills.length ? '' : 'Add at least one skill.'); input.focus();
            });
            tag.append(label, remove); tags.append(tag);
        });
        source.value = skills.join(', ');
        editor.classList.toggle('skills-valid', Boolean(skills.length));
        suggestions.querySelectorAll('button').forEach(button => {
            button.disabled = skills.some(s => s.toLocaleLowerCase() === button.textContent.toLocaleLowerCase());
        });
        if (source.closest('.skill-review-page')) {
            suggestions.hidden = !Array.from(suggestions.querySelectorAll('button')).some(button => !button.disabled);
        }
    }
    function add(value) {
        const items = value.split(',').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
        if (!items.length) { message('Type a skill to add.'); return false; }
        const next = [...skills];
        for (const skill of items) {
            if (skill.length > 60 || !/\p{L}/u.test(skill)) { message('Each skill must contain a letter and be 60 characters or fewer.'); return false; }
            if (next.some(s => s.toLocaleLowerCase() === skill.toLocaleLowerCase())) { message('That skill is already added.'); return false; }
            if (next.length >= 20) { message('Add up to 20 skills.'); return false; }
            next.push(skill);
        }
        skills = next; input.value = ''; message(''); render(); return true;
    }
    input.addEventListener('keydown', event => {
        if (event.isComposing) return;
        if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); add(input.value); }
    });
    input.addEventListener('input', () => { message(''); if (input.value.includes(',')) add(input.value); });
    document.getElementById('skill-add').addEventListener('click', () => { add(input.value); input.focus(); });
    suggestions.addEventListener('click', event => { if (event.target.matches('button')) add(event.target.textContent); });
    source.closest('form').addEventListener('submit', event => {
        const pendingValid = !input.value.trim() || add(input.value);
        const selectedSuggestions = source.closest('form').querySelectorAll('input[name="suggested"]:checked').length;
        if (!pendingValid || (!skills.length && !selectedSuggestions)) {
            event.preventDefault(); event.stopImmediatePropagation();
            if (!skills.length) message('Add at least one skill.');
            if (typeof renderStepUI === 'function') { activeStep = 2; renderStepUI(); }
            input.focus();
        }
    }, true);
    render();
})();
