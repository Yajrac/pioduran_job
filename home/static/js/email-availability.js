(() => {
 const endpoint = document.currentScript.dataset.emailUrl;
 const field = document.getElementById('email');
 const feedback = document.getElementById('email-feedback');
 let timer, revision = 0, checked = '', available = false;
 // "Did you mean ...?" hint for typos such as gmaiil.com -> gmail.com
 const hint = document.createElement('div');
 hint.className = 'email-suggestion'; hint.hidden = true; hint.setAttribute('role', 'status');
 hint.style.cssText = 'margin-top:6px;padding:8px 12px;border:1px solid #fde68a;border-radius:10px;background:#fffbeb;color:#92400e;font-size:13px;line-height:1.5';
 feedback.insertAdjacentElement('afterend', hint);
 function suggest(address) {
  hint.hidden = !address; hint.textContent = '';
  if (!address) return;
  hint.append('Did you mean ');
  const strong = document.createElement('strong'); strong.textContent = address; hint.append(strong, '? ');
  const use = document.createElement('button');
  use.type = 'button'; use.textContent = 'Use this';
  use.style.cssText = 'width:auto;min-height:0;height:auto;margin:0 0 0 4px;padding:2px 10px;border:1px solid #f59e0b;border-radius:8px;background:#fff;box-shadow:none;transform:none;color:#92400e;font:inherit;font-weight:700;cursor:pointer';
  use.addEventListener('click', () => { field.value = address; suggest(null); field.dispatchEvent(new Event('input', {bubbles:true})); field.focus(); });
  hint.append(use);
 }
 function paint(error, valid) {
  field.setCustomValidity(error);
  field.classList.toggle('field-invalid', Boolean(error));
  field.classList.toggle('field-valid', Boolean(valid));
  field.setAttribute('aria-invalid', String(Boolean(error)));
  feedback.textContent = error;
 }
 async function check() {
  const value = field.value.trim(), version = ++revision;
  if (!value || field.validity.typeMismatch) { paint('Enter a valid email address.',false); return; }
  paint('Checking email…', false);
  try {
   const response = await fetch(endpoint + '?email=' + encodeURIComponent(value), {cache:'no-store'});
   if (!response.ok) throw new Error();
   const data = await response.json();
   if (version !== revision || field.value.trim() !== value) return;
   checked = value; available = data.available; paint(data.error, available); suggest(data.suggestion);
  } catch (_) { if (version === revision) paint('Unable to check email. Please try again.',false); }
 }
 field.addEventListener('input', () => {
  clearTimeout(timer); ++revision; checked = ''; available = false;
  paint('', false); suggest(null); field.setCustomValidity('Please wait for the email check.');
  timer = setTimeout(check,350);
 });
 field.addEventListener('blur', () => { clearTimeout(timer); check(); });
 field.addEventListener('invalid', event => { event.preventDefault(); if (checked !== field.value.trim()) check(); });
 window.validateRegistrationEmail = () => {
  if (checked === field.value.trim() && available) return true;
  check(); field.focus(); return false;
 };
 field.form.addEventListener('submit', event => {
  if (checked !== field.value.trim() || !available) {
   event.preventDefault(); event.stopImmediatePropagation();
   const panel = field.closest('.form-step-panel');
   if (panel && typeof renderStepUI === 'function') {
    activeStep = Number(panel.id.split('-').pop()); renderStepUI();
   }
   check(); field.focus();
  }
 },true);
 if (field.value) check();
})();
