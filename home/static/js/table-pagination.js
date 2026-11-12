document.addEventListener('DOMContentLoaded', function () {
    ['jobTable', 'employerTable', 'applicantTable'].forEach(function (id) {
        const table = document.getElementById(id);
        if (!table) return;
        const rows = Array.from(table.querySelectorAll('tbody tr[data-status]'));
        const nav = document.createElement('nav');
        nav.className = 'table-pagination';
        nav.setAttribute('aria-label', 'Table pages');
        table.closest('.table-responsive').after(nav);
        let page = 1;
        const pageSize = 10;

        function button(label, target, disabled, current) {
            const item = document.createElement('button');
            item.type = 'button';
            item.textContent = label;
            item.disabled = disabled;
            if (current) item.setAttribute('aria-current', 'page');
            if (typeof label === 'number') item.setAttribute('aria-label', 'Page ' + label);
            item.addEventListener('click', function () {
                page = target;
                render();
                const active = nav.querySelector('[aria-current="page"]');
                if (active) active.focus();
            });
            nav.append(item);
        }

        function render() {
            const matches = rows.filter(row => row.dataset.filterHidden !== 'true');
            const total = Math.max(1, Math.ceil(matches.length / pageSize));
            page = Math.min(page, total);
            rows.forEach(row => { row.hidden = true; });
            matches.slice((page - 1) * pageSize, page * pageSize).forEach(row => { row.hidden = false; });
            nav.replaceChildren();
            const info = document.createElement('span');
            info.className = 'pagination-info';
            info.setAttribute('role', 'status');
            info.textContent = matches.length ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, matches.length)} of ${matches.length}` : '0 results';
            nav.append(info);
            button('Previous', page - 1, page === 1);
            const pages = new Set([1, total]);
            for (let n = Math.max(1, page - 2); n <= Math.min(total, page + 2); n++) pages.add(n);
            let previous = 0;
            [...pages].sort((a, b) => a - b).forEach(function (n) {
                if (previous && n - previous > 1) {
                    const gap = document.createElement('span');
                    gap.textContent = '…';
                    nav.append(gap);
                }
                button(n, n, false, n === page);
                previous = n;
            });
            button('Next', page + 1, page === total);
            table.dispatchEvent(new Event('table-page-change'));
        }
        table.addEventListener('table-filter-change', function () { page = 1; render(); });
        render();
    });
});
