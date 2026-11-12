(() => {
 const endpoint = document.currentScript.dataset.emailUrl;
 const field = document.getElementById('email');
 const feedback = document.getElementById('email-feedback');
 let timer, revision = 0, checked = '', available = false;
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
   checked = value; available = data.available; paint(data.error, available);
  } catch (_) { if (version === revision) paint('Unable to check email. Please try again.',false); }
 }
 field.addEventListener('input', () => {
  clearTimeout(timer); ++revision; checked = ''; available = false;
  paint('', false); field.setCustomValidity('Please wait for the email check.');
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
