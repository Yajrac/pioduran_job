(() => {
 const mobile = matchMedia('(max-width:768px)');
 let active = null;
 function close() {
  if (!active) return;
  active.menu.removeAttribute('style');
  active.menu.classList.remove('actions-open');
  active.marker.replaceWith(active.menu);
  active.button.setAttribute('aria-expanded','false');
  active = null;
 }
 document.querySelectorAll('.employer-actions-toggle').forEach(button => {
  button.addEventListener('click', () => {
   if (!mobile.matches) return;
   if (active?.button === button) { close(); return; }
   close();
   const menu = document.getElementById(button.getAttribute('aria-controls'));
   const marker = document.createComment('actions-menu');
   menu.replaceWith(marker); document.body.append(menu);
   menu.classList.add('actions-open');
   button.setAttribute('aria-expanded','true');
   const rect = button.getBoundingClientRect();
   menu.style.left = Math.max(8, Math.min(rect.right - 155, innerWidth - 163)) + 'px';
   const height = menu.getBoundingClientRect().height;
   menu.style.top = Math.max(8, rect.bottom + height + 8 > innerHeight ? rect.top - height - 6 : rect.bottom + 6) + 'px';
   active = {button, menu, marker};
  });
 });
 document.addEventListener('click', event => {
  if (active && !active.menu.contains(event.target) && !active.button.contains(event.target)) close();
 });
 document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && active) { const button = active.button; close(); button.focus(); }
 });
 window.addEventListener('resize',close);
 document.addEventListener('scroll', event => { if (active && !active.menu.contains(event.target)) close(); },true);
})();
