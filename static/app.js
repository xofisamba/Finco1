/* Finco One — Workspace Tabs Functional Fix — phase9_5_workspace_tabs_functional_fix */

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

  // Update URL hash for bookmarkability
  if (history.pushState) {
    history.pushState(null, '', '#' + tabId);
  }

  // Scroll workspace top into view
  var workspace = document.getElementById('workspace-content');
  if (workspace) {
    workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Scroll active tab into view in ribbon
  if (activeBtn) {
    activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }

  // Dispatch custom event
  document.dispatchEvent(new CustomEvent('tabChanged', { detail: { tab: tabId } }));
}

/* Activate a tab by its data-tab attribute value */
function activateTab(tabId) {
  switchTab(tabId);
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

/* ── DOM Initialisation ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

  /* ── Tab click handlers (data-tab based, CSP-safe) ── */
  document.querySelectorAll('.ws-tab[data-tab]').forEach(function(tabBtn) {
    tabBtn.addEventListener('click', function() {
      var tabId = tabBtn.getAttribute('data-tab');
      if (tabId) switchTab(tabId);
    });
  });

  /* ── Restore tab from URL hash ── */
  var hash = window.location.hash.replace('#', '');
  if (hash) {
    var hashTab = document.querySelector('.ws-tab[data-tab="' + hash + '"]');
    if (hashTab) {
      /* Defer so panels are already in DOM */
      setTimeout(function() { switchTab(hash); }, 0);
    }
  } else {
    /* Ensure overview is active by default */
    var defaultTab = document.querySelector('.ws-tab[data-tab="overview"]');
    var defaultPanel = document.getElementById('panel-overview');
    if (defaultTab && !defaultTab.classList.contains('active')) {
      defaultTab.classList.add('active');
    }
    if (defaultPanel && !defaultPanel.classList.contains('active')) {
      defaultPanel.classList.add('active');
    }
    /* Hide all other panels */
    document.querySelectorAll('.tab-panel').forEach(function(p) {
      if (p.id !== 'panel-overview') p.classList.remove('active');
    });
  }

  /* ── Hash change listener ── */
  window.addEventListener('hashchange', function() {
    var h = window.location.hash.replace('#', '');
    if (h && h !== activeTab) switchTab(h);
  });

  /* ── Sidebar nav links ── */
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

  /* ── New Project button ── */
  var addBtn = document.getElementById('ps-add-btn');
  if (addBtn) {
    addBtn.addEventListener('click', function () {
      alert('New Project — coming in a future phase.');
    });
  }

  /* ── Run Model button ── */
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

  /* ── Save / Load buttons ── */
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

  /* ── Duplicate scenario button ── */
  var dupBtn = document.querySelector('.ps-action-btn:nth-child(2)');
  if (dupBtn) {
    dupBtn.addEventListener('click', function () {
      alert('Duplicate Scenario — coming in a future phase.');
    });
  }
});