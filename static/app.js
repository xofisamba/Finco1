/* Finco One — Sidebar Navigation Fix — phase9_5_nav_fix */

/* ── Tab Switching (workspace tabs) ───────────────────────────────────── */
var activeTab = 'overview';

function switchTab(tabId) {
  if (!tabId) return;
  activeTab = tabId;

  // Update tab button states
  document.querySelectorAll('.ws-tab').forEach(function(btn) {
    btn.classList.remove('active');
  });
  var activeBtn = document.getElementById('tab-' + tabId);
  if (activeBtn) activeBtn.classList.add('active');

  // Show/hide panels
  document.querySelectorAll('.tab-panel').forEach(function(panel) {
    panel.classList.remove('active');
  });
  var activePanel = document.getElementById('panel-' + tabId);
  if (activePanel) activePanel.classList.add('active');

  // Scroll active tab into view
  if (activeBtn) {
    activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }
}

/* ── Project Switching (sidebar project cards) ────────────────────────── */
function switchProject(projectId) {
  // Deactivate all cards
  document.querySelectorAll('.ps-card').forEach(function(card) {
    card.classList.remove('active');
    var statusDot = card.querySelector('.ps-card-status');
    if (statusDot) {
      statusDot.textContent = '';
      statusDot.classList.remove('ps-card-status--active');
    }
  });

  // Activate selected card
  var activeCard = document.getElementById('ps-' + projectId);
  if (activeCard) {
    activeCard.classList.add('active');
    var statusDot = activeCard.querySelector('.ps-card-status');
    if (statusDot) {
      statusDot.textContent = '●';
      statusDot.classList.add('ps-card-status--active');
    }
  }

  // Dispatch custom event for workspace tabs to listen to
  document.dispatchEvent(new CustomEvent('projectChanged', { detail: { project: projectId } }));
}

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

  /* New Project button */
  var addBtn = document.getElementById('ps-add-btn');
  if (addBtn) {
    addBtn.addEventListener('click', function () {
      alert('New Project — coming in a future phase.');
    });
  }

  /* Run Model button */
  var runBtn = document.getElementById('btn-run-model');
  if (runBtn) {
    runBtn.addEventListener('click', function () {
      var form = document.getElementById('main-form');
      if (form) {
        var runEvent = new CustomEvent('runModelRequested', { bubbles: true });
        form.dispatchEvent(runEvent);
      }
    });
  }

  /* Save / Load buttons */
  var saveBtn = document.getElementById('btn-save');
  if (saveBtn) {
    saveBtn.addEventListener('click', function () {
      var form = document.getElementById('main-form');
      if (form) {
        var saveEvent = new CustomEvent('saveRequested', { bubbles: true });
        form.dispatchEvent(saveEvent);
      }
    });
  }

  var loadBtn = document.getElementById('btn-load');
  if (loadBtn) {
    loadBtn.addEventListener('click', function () {
      alert('Load — coming in a future phase.');
    });
  }

  /* Duplicate scenario button */
  var dupBtn = document.querySelector('.ps-action-btn:nth-child(2)');
  if (dupBtn) {
    dupBtn.addEventListener('click', function () {
      alert('Duplicate Scenario — coming in a future phase.');
    });
  }
});