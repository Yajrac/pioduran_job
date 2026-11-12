/* Shared hover/focus tooltip for the PESO dashboard charts.
   Tooltips only repeat values that are also on the page (legend lists,
   value labels, "View as table"), so nothing is hidden behind hover.
   Labels are inserted with textContent, never innerHTML. */
(function () {
  const root = document.querySelector('.viz');
  if (!root) return;
  const tip = root.querySelector('.viz-tooltip');

  function fill(target) {
    tip.replaceChildren();
    const title = document.createElement('div');
    title.className = 'viz-tooltip-title';
    title.textContent = target.dataset.tipTitle || '';
    tip.appendChild(title);
    (target.dataset.tip || '').split(';').filter(Boolean).forEach(function (row) {
      const [label, value, color] = row.split('|');
      const line = document.createElement('div');
      line.className = 'viz-tooltip-row';
      const key = document.createElement('span');
      key.className = 'viz-tooltip-key';
      if (color) key.style.background = color; else key.classList.add('is-blank');
      const strong = document.createElement('strong');
      strong.textContent = value;
      const name = document.createElement('span');
      name.textContent = label;
      line.append(key, strong, name);
      tip.appendChild(line);
    });
  }

  function place(x, y) {
    const box = root.getBoundingClientRect();
    tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let left = x - box.left + 14, top = y - box.top - h - 12;
    if (left + w > box.width) left = x - box.left - w - 14;
    if (top < 0) top = y - box.top + 16;
    tip.style.transform = 'translate(' + Math.max(0, left) + 'px,' + top + 'px)';
  }

  function show(target, x, y) {
    root.querySelectorAll('.viz-hit.is-active').forEach(el => el.classList.remove('is-active'));
    target.classList.add('is-active');
    fill(target);
    place(x, y);
  }

  function hide(target) {
    target.classList.remove('is-active');
    tip.hidden = true;
  }

  root.querySelectorAll('.viz-hit').forEach(function (el) {
    el.addEventListener('pointermove', e => show(el, e.clientX, e.clientY));
    el.addEventListener('pointerleave', () => hide(el));
    el.addEventListener('focus', function () {
      const r = el.getBoundingClientRect();
      show(el, r.left + r.width / 2, r.top);
    });
    el.addEventListener('blur', () => hide(el));
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') tip.hidden = true; });
})();
