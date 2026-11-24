// Applicants list: filters apply on their own - dropdowns at once, the skill box after a short pause in typing.
(function () {
    var form = document.getElementById('candidateFilters');
    if (!form) return;
    var skill = form.querySelector('#candidateSkill');
    var timer;
    var KEY = 'candidateFilters.focusSkill';

    function submit(fromSkill) {
        clearTimeout(timer);
        try { if (fromSkill) sessionStorage.setItem(KEY, '1'); } catch (e) {}
        // A new filter starts again on page 1.
        var page = form.querySelector('input[name=page]');
        if (page) page.remove();
        form.requestSubmit ? form.requestSubmit() : form.submit();
    }

    form.addEventListener('change', function (event) {
        if (event.target.tagName === 'SELECT') submit(false);
    });

    if (skill) {
        var last = skill.value;
        skill.addEventListener('input', function () {
            clearTimeout(timer);
            if (skill.value.trim() === last.trim()) return;
            timer = setTimeout(function () { submit(true); }, 600);
        });
        // Keep typing where you left off after the page reloads with the new results.
        var refocus = false;
        try { refocus = sessionStorage.getItem(KEY) === '1'; sessionStorage.removeItem(KEY); } catch (e) {}
        if (refocus) {
            skill.focus();
            var end = skill.value.length;
            skill.setSelectionRange(end, end);
        }
    }
})();
