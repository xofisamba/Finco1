/* Finco One — Sidebar Navigation Fix — phase9_5_nav_fix */

document.addEventListener('DOMContentLoaded', function () {

  /* Sidebar nav links — open matching details section + scroll on click */
  document.querySelectorAll('.sidebar-nav-link').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var href = link.getAttribute('href');
      if (!href || !href.startsWith('#')) return;

      var id = href.substring(1);
      if (!id || id === 'dashboard' || id === 'audit') return;

      /* Update active nav state */
      document.querySelectorAll('.sidebar-nav-link').forEach(function (l) {
        l.classList.remove('active');
      });
      link.classList.add('active');

      /* Open target <details> if it's closed */
      var target = document.getElementById(id);
      if (target && target.tagName === 'DETAILS' && !target.hasAttribute('open')) {
        target.setAttribute('open', '');
      }

      /* Scroll target into view */
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});