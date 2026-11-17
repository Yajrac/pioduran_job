/* Show / hide for any password field: <button data-toggle-password="FIELD_ID"> */
(() => {
  const eye = '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>';
  const eyeOff = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
  document.querySelectorAll('[data-toggle-password]').forEach(button => {
    const input = document.getElementById(button.dataset.togglePassword);
    const icon = button.querySelector('svg');
    if (!input || !icon) return;
    button.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      icon.innerHTML = show ? eyeOff : eye;
      const label = show ? 'Hide password' : 'Show password';
      button.setAttribute('aria-label', label);
      button.setAttribute('title', label);
      button.setAttribute('aria-pressed', String(show));
    });
  });
})();
