// Attach the admin Bearer key to every HTMX request.
document.body.addEventListener('htmx:configRequest', function (ev) {
  var key = localStorage.getItem('admin_bearer_key');
  if (key) ev.detail.headers['Authorization'] = 'Bearer ' + key;
});

// On 401/403 from any HTMX response, clear storage and redirect to login.
document.body.addEventListener('htmx:responseError', function (ev) {
  var status = ev.detail.xhr.status;
  if (status === 401 || status === 403) {
    localStorage.removeItem('admin_bearer_key');
    window.location.href = '/admin/login';
  }
});

// Restore stored theme on load (auto / light / dark).
(function () {
  var root = document.documentElement;
  var stored = localStorage.getItem('admin_theme');
  if (stored) root.setAttribute('data-theme', stored);
})();

// Theme toggle button cycles auto -> light -> dark -> auto.
document.addEventListener('click', function (ev) {
  if (!ev.target || ev.target.id !== 'theme-toggle') return;
  var root = document.documentElement;
  var current = root.getAttribute('data-theme') || 'auto';
  var next = current === 'auto' ? 'light' : current === 'light' ? 'dark' : 'auto';
  root.setAttribute('data-theme', next);
  localStorage.setItem('admin_theme', next);
});
