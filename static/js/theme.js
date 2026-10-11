/* Theme toggle. Dark mode is applied pre-paint by an inline script in base.html. */
function updateToggleIcon(theme) {
  var sun = document.querySelector('.icon-sun');
  var moon = document.querySelector('.icon-moon');
  if (sun) sun.style.display = theme === 'dark' ? 'inline' : 'none';
  if (moon) moon.style.display = theme === 'light' ? 'inline' : 'none';
}

function toggleTheme() {
  var root = document.documentElement;
  var current = root.getAttribute('data-theme');
  var next = current === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateToggleIcon(next);
}

document.addEventListener('DOMContentLoaded', function () {
  var theme = document.documentElement.getAttribute('data-theme') || 'light';
  updateToggleIcon(theme);
});
