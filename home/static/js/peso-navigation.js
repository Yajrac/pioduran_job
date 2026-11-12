(() => {
 const toggle = document.getElementById('pesoMenuToggle');
 const close = document.getElementById('pesoMenuClose');
 const sidebar = document.getElementById('pesoSidebar');
 const main = document.querySelector('.main-content');
 const mobile = matchMedia('(max-width:768px)');
 let opened = false;
 function setOpen(value) {
  opened = value && mobile.matches;
  document.body.classList.toggle('peso-menu-open', opened);
  toggle.setAttribute('aria-expanded',String(opened));
  toggle.disabled = opened;
  sidebar.inert = mobile.matches && !opened;
  main.inert = opened;
  if (opened) close.focus();
 }
 toggle.addEventListener('click', () => setOpen(true));
 close.addEventListener('click', () => { setOpen(false); toggle.focus(); });
 sidebar.addEventListener('click', event => { if (event.target.closest('a')) setOpen(false); });
 document.addEventListener('keydown', event => {
  if (!opened) return;
  if (event.key === 'Escape') { setOpen(false); toggle.focus(); }
  if (event.key === 'Tab') {
   const items = sidebar.querySelectorAll('button,a[href]');
   const first = items[0], last = items[items.length-1];
   if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
   else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
 });
 mobile.addEventListener('change', () => setOpen(false));
 setOpen(false);
})();
