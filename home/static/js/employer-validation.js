(() => {
 const endpoint = document.currentScript.dataset.usernameUrl;
 const companyEndpoint = document.currentScript.dataset.companyUrl;
 const companyFields = {company_name:'company_name', contact_no:'contact_no'};
 const companyChecks = {};
 const companyTimers = {};
 const form = document.getElementById('registrationForm');
 const ids = ['username','email','password','confirm_password','company_name','permit_file','contact_no','company_logo','company_description'];
 const MAX_UPLOAD = 5 * 1024 * 1024;
 // Same format rules as the server (home/registration_validation.py).
 function usernameFormatError(value) {
  return /^[A-Za-z][A-Za-z0-9._]{3,29}$/.test(value) ? '' : 'Use 4 to 30 characters: start with a letter, then letters, numbers, dots or underscores.';
 }
 function companyNameError(value) {
  value = value.replace(/\s+/g, ' ').trim();
  if (!value) return 'Company name is required.';
  if (value.length < 2 || value.length > 150) return 'Company name must be 2 to 150 characters.';
  if (!/\p{L}/u.test(value)) return 'Company name must contain letters.';
  if (!/^[\p{L}\p{N}\p{M} .,&'()\/-]+$/u.test(value)) return "Use letters, numbers, spaces and . , & ' - ( ) / only.";
  return '';
 }
 function fileError(field) {
  const file = field.files && field.files[0];
  if (field.id === 'permit_file') {
   if (!file) return 'Upload your business permit.';
   if (!/\.(pdf|jpe?g|png)$/i.test(file.name)) return 'Upload the permit as a PDF, JPG or PNG file.';
   if (file.size > MAX_UPLOAD) return 'Business permit must not exceed 5 MB.';
  } else if (file) {
   if (!/\.(png|jpe?g|webp)$/i.test(file.name)) return 'Upload a PNG, JPEG, or WebP image.';
   if (file.size > MAX_UPLOAD) return 'Logo must not exceed 5 MB.';
  }
  return '';
 }
 function descriptionError(value) {
  const length = value.trim().length;
  if (length < 20) return 'Describe your company in at least 20 characters.';
  if (length > 1000) return 'Keep the description to 1000 characters or fewer.';
  return '';
 }
 const description = document.getElementById('company_description');
 const descriptionCount = document.getElementById('company_description-count');
 function updateCount() {
  const length = description.value.trim().length;
  descriptionCount.textContent = length < 20 ? `${length} / 1000 characters (at least 20).` : `${length} / 1000 characters.`;
 }
 description.addEventListener('input', updateCount);
 if (description.value) updateCount();
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
   else if (usernameFormatError(value)) error = usernameFormatError(value);
   else if (checked !== value || !available) { checkUsername(); return false; }
  } else if (id === 'permit_file' || id === 'company_logo') {
   error = fileError(field);
   paint(field, error, !error && Boolean(field.files && field.files.length));
   return !error;
  } else if (id === 'company_description') {
   error = descriptionError(field.value);
  } else if (id === 'confirm_password') {
   if (!field.value || field.value !== document.getElementById('password').value) error = 'Passwords do not match.';
  } else if (id === 'password') {
   if (!validatePasswordRules(field.value)) error = 'Password must meet all the listed security rules.';
  } else if (!value) error = 'This field is required.';
  else if (id === 'email' && field.validity.typeMismatch) error = 'Enter a valid email address.';
  else if (id === 'contact_no' && !/^09[0-9]{9}$/.test(value)) error = 'Enter an 11-digit mobile number starting with 09.';
  else if (id === 'company_name') error = companyNameError(value);
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
  const formatError = !value ? 'This field is required.'
   : id === 'contact_no' && !/^09[0-9]{9}$/.test(value) ? 'Enter an 11-digit mobile number starting with 09.'
   : id === 'company_name' ? companyNameError(value) : '';
  if (formatError) {
   delete companyChecks[id];
   paint(field, formatError, false);
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
  if (usernameFormatError(value)) { paint(field, usernameFormatError(value), false); return; }
  paint(field, 'Checking username…', false);
  try {
   const response = await fetch(endpoint + '?role=employer&username=' + encodeURIComponent(value), {cache:'no-store'});
   if (!response.ok) throw new Error();
   const data = await response.json();
   if (version !== revision || field.value.trim() !== value) return;
   checked = value; available = data.available; paint(field,data.error,available);
  } catch (_) { if (version === revision) paint(field,'Unable to check username. Please try again.',false); }
 }
 ids.forEach(id => {
  const field = document.getElementById(id);
  if (field.type === 'file') field.addEventListener('change', () => { touched.add(id); validate(id); });
  field.addEventListener('input', () => {
   if (field.type === 'file') return;
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
