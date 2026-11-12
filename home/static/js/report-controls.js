document.addEventListener('DOMContentLoaded', function () {
    function bindControls(form) {
        const dates = form.querySelectorAll('input[type="date"]');
        const submit = form.querySelector('button[type="submit"]');
        form.addEventListener('submit', function (event) {
            dates[1].setCustomValidity('');
            if (dates[0].value && dates[1].value && dates[0].value > dates[1].value) {
                event.preventDefault();
                dates[1].setCustomValidity('Date To must be on or after Date From.');
                dates[1].reportValidity();
            }
        });
        dates.forEach(input => input.addEventListener('input', () => dates[1].setCustomValidity('')));
        form.querySelector('.report-reset').addEventListener('click', function () {
            dates.forEach(input => { input.value = ''; });
            dates[1].setCustomValidity('');
            form.querySelector('input[name="generate"]').value = '';
            form.requestSubmit();
        });
        form.querySelector('.report-print').addEventListener('click', function () {
            form.closest('.report-panel').classList.add('print-selected-report');
            document.body.classList.add('printing-one-report');
            window.print();
        });
    }
    document.querySelectorAll('.report-table-controls').forEach(bindControls);
    window.addEventListener('afterprint', function () {
        document.body.classList.remove('printing-one-report');
        document.querySelectorAll('.print-selected-report').forEach(panel => panel.classList.remove('print-selected-report'));
    });
});
