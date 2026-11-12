(() => {
 const endpoint = document.currentScript.dataset.usernameUrl;
 const companyEndpoint = document.currentScript.dataset.companyUrl;
 const companyFields = {company_name:'company_name', permit_no:'business_permit_no', contact_no:'contact_no'};
 const companyChecks = {};
 const companyTimers = {};
 const form = document.getElementById('registrationForm');
 const ids = ['username','email','password','confirm_password','company_name','permit_no','contact_no'];
 const touched = new Set();
 const attemptedSteps = new Set();
 let checked = '', available = false, revision = 0, timer;
 function paint(field, error, valid) {
  field.setCustomValidity(error);
  field.setAttribute('aria-invalid', String(Boolean(error)));
  field.classList.toggle('field-invalid', Boolean(error));
  field.classList.toggle('field-valid', Boolean(valid));
  document.getElementById(field.id + '-feedback').textContent = error;
 }
 function validate(id) {
  if (id === 'email' && window.validateRegistrationEmail) return window.validateRegistrationEmail();
  const field = document.getElementById(id), value = field.value.trim();
  let error = '';
  if (id === 'username') {
   if (!value) error = 'Username is required.';
   else if (checked !== value || !available) { checkUsername(); return false; }
  } else if (id === 'confirm_password') {
   if (!field.value || field.value !== document.getElementById('password').value) error = 'Passwords do not match.';
  } else if (id === 'password') {
   if (!validatePasswordRules(field.value)) error = 'Password must meet all the listed security rules.';
  } else if (!value) error = 'This field is required.';
  else if (id === 'email' && field.validity.typeMismatch) error = 'Enter a valid email address.';
  else if (id === 'contact_no' && !/^09[0-9]{9}$/.test(value)) error = 'Enter an 11-digit mobile number starting with 09.';
  if (!error && companyFields[id]) {
   const result = companyChecks[id];
   if (!result || result.value !== value) { checkCompany(id); return false; }
   error = result.error;
  }
  paint(field, error, !error && Boolean(value));
  return !error;
 }
 async function checkCompany(id) {
  const field = document.getElementById(id), value = field.value.trim();
  clearTimeout(companyTimers[id]);
  if (!value || (id === 'contact_no' && !/^09[0-9]{9}$/.test(value))) {
   delete companyChecks[id];
   paint(field, !value ? 'This field is required.' : 'Enter an 11-digit mobile number starting with 09.', false);
   return;
  }
  const check = {value, error:'Checking availability...', pending:true};
  companyChecks[id] = check;
  paint(field, check.error, false);
  try {
   const query = new URLSearchParams({field:companyFields[id], value});
   const response = await fetch(companyEndpoint + '?' + query, {cache:'no-store'});
   if (!response.ok) throw new Error();
   const data = await response.json();
   if (companyChecks[id] !== check || field.value.trim() !== value) return;
   check.error = data.error;
   check.pending = false;
   paint(field, data.error, data.available);
  } catch (_) {
   if (companyChecks[id] === check && field.value.trim() === value) {
    delete companyChecks[id];
    paint(field, 'Unable to check availability. Please try again.', false);
   }
  }
 }
 async function checkUsername() {
  const field = document.getElementById('username'), value = field.value.trim(), version = ++revision;
  if (!value) { paint(field,'Username is required.',false); return; }
  paint(field, 'Checking username…', false);
  try {
   const response = await fetch(endpoint + '?username=' + encodeURIComponent(value), {cache:'no-store'});
   if (!response.ok) throw new Error();
   const data = await response.json();
   if (version !== revision || field.value.trim() !== value) return;
   checked = value; available = data.available; paint(field,data.error,available);
  } catch (_) { if (version === revision) paint(field,'Unable to check username. Please try again.',false); }
 }
 ids.forEach(id => {
  const field = document.getElementById(id);
  field.addEventListener('input', () => {
   touched.add(id);
   if (companyFields[id]) {
    clearTimeout(companyTimers[id]);
    delete companyChecks[id];
    paint(field, '', false);
    field.setCustomValidity('Please wait for the availability check.');
    companyTimers[id] = setTimeout(() => validate(id), 350);
    return;
   }
   if (id === 'username') {
    clearTimeout(timer); ++revision; checked = ''; available = false;
    paint(field,'',false); field.setCustomValidity('Please wait for the username check.');
    timer = setTimeout(checkUsername,350);
   } else {
    validate(id);
    if (id === 'password' && document.getElementById('confirm_password').value) validate('confirm_password');
   }
  });
  field.addEventListener('blur', () => {
   if (touched.has(id) || field.value.trim()) validate(id);
  });
  field.addEventListener('invalid', event => {
   event.preventDefault();
   const step = ids.indexOf(id) < 4 ? 1 : 2;
   if (touched.has(id) || attemptedSteps.has(step)) validate(id);
  });
 });
 window.validateEmployerStep = step => {
  attemptedSteps.add(step);
  const fields = step === 1 ? ids.slice(0,4) : ids.slice(4);
  const invalid = fields.filter(id => !validate(id));
  if (invalid.length) document.getElementById(invalid[0]).focus();
  return !invalid.length;
 };
 let submitting = false;
 const submitButton = document.getElementById('btnSubmit');
 const originalSubmitContent = submitButton.innerHTML;
 form.addEventListener('submit', event => {
  if (submitting) {
   event.preventDefault(); event.stopImmediatePropagation();
   return;
  }
  for (const step of [1,2]) {
   if (!window.validateEmployerStep(step)) {
    event.preventDefault(); event.stopImmediatePropagation();
    activeStep = step; renderStepUI();
    form.querySelector(`#step-panel-${step} [aria-invalid="true"]`)?.focus();
    return;
   }
  }
  submitting = true;
  submitButton.disabled = true;
  submitButton.setAttribute('aria-busy', 'true');
  submitButton.innerHTML = '<span class="registration-submit-spinner" aria-hidden="true"></span><span role="status">Submitting...</span>';
 },true);
 window.addEventListener('pageshow', () => {
  submitting = false;
  submitButton.disabled = false;
  submitButton.removeAttribute('aria-busy');
  submitButton.innerHTML = originalSubmitContent;
 });
 // Validate on interaction or an explicit step/submission attempt, not page load.
})();
