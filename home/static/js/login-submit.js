(() => {
 const form = document.getElementById('loginForm') || document.getElementById('adminLoginForm');
 const getField = id => document.getElementById(form.id === 'adminLoginForm' ? 'admin-' + id : id);
 const button = form.querySelector('[type="submit"]');
 const status = document.getElementById('login-status');
 let pending = false;
 let lockedUntil = 0, countdown;
 function showCooldown(seconds) {
  lockedUntil = Date.now() + seconds * 1000;
  clearInterval(countdown);
  function tick() {
   const remaining = Math.max(0, Math.ceil((lockedUntil - Date.now()) / 1000));
   button.disabled = remaining > 0;
   button.textContent = remaining ? `Try again in ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2,'0')}` : 'Sign In';
   if (!remaining) { clearInterval(countdown); status.textContent = ''; }
  }
  tick(); countdown = setInterval(tick, 1000);
 }
 ['username', 'password'].forEach(id => {
  const field = getField(id);
  field.addEventListener('input', () => {
   field.removeAttribute('aria-invalid');
   document.getElementById(id + '-error').textContent = '';
   if (Date.now() >= lockedUntil) status.textContent = '';
  });
 });
 form.addEventListener('submit', async event => {
  event.preventDefault();
  if (pending || Date.now() < lockedUntil) return;
  pending = true;
  button.disabled = true;
  button.innerHTML = '<span class="login-spinner" aria-hidden="true"></span> Signing in…';
  form.setAttribute('aria-busy', 'true');
  status.textContent = '';
  ['username','password'].forEach(id => {
   document.getElementById(id + '-error').textContent = '';
   getField(id).removeAttribute('aria-invalid');
  });
  try {
   const response = await fetch(form.action || location.href, {
    method:'POST', body:new FormData(form), headers:{Accept:'application/json'}, credentials:'same-origin'
   });
   const data = await response.json();
   if (response.ok && data.redirect) { location.assign(data.redirect); return; }
   if (Array.isArray(data.clear_fields)) {
    data.clear_fields.filter(id => ['username','password'].includes(id)).forEach(id => {
     const field = getField(id);
     field.value = ''; field.setAttribute('aria-invalid','true');
    });
    status.textContent = data.error || 'Invalid username or password.';
    getField('username').focus();
   } else if (['username','password'].includes(data.field)) {
    const field = getField(data.field);
    field.value = ''; field.setAttribute('aria-invalid','true');
    document.getElementById(data.field + '-error').textContent = data.error;
    field.focus();
   } else { status.textContent = data.error || 'Unable to sign in. Please try again.'; }
   if (response.status === 429 && data.retry_after) showCooldown(data.retry_after);
   if (data.warning) status.textContent = data.warning;
  } catch (_) { status.textContent = 'Unable to connect. Please try again.'; }
  pending = false;
  if (Date.now() >= lockedUntil) { button.disabled = false; button.textContent = 'Sign In'; }
  form.removeAttribute('aria-busy');
 });
})();
