/* Finco One workspace interactions */

var activeTab = 'overview';

function switchTab(tabId) {
  if (!tabId) return;
  activeTab = tabId;

  document.querySelectorAll('.ws-tab').forEach(function(btn) {
    btn.classList.remove('active');
  });
  var activeBtn = document.getElementById('tab-' + tabId);
  if (activeBtn) activeBtn.classList.add('active');

  document.querySelectorAll('.tab-panel').forEach(function(panel) {
    panel.classList.remove('active');
  });
  var activePanel = document.getElementById('panel-' + tabId);
  if (activePanel) activePanel.classList.add('active');

  if (history.pushState) {
    history.pushState(null, '', '#' + tabId);
  }

  var workspace = document.getElementById('workspace-content');
  if (workspace) workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (activeBtn) activeBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });

  document.dispatchEvent(new CustomEvent('tabChanged', { detail: { tab: tabId } }));
}

function activateTab(tabId) {
  switchTab(tabId);
}

function switchProject(projectId) {
  document.querySelectorAll('.ps-card').forEach(function(card) {
    card.classList.remove('active');
    var statusDot = card.querySelector('.ps-card-status');
    if (statusDot) {
      statusDot.textContent = '';
      statusDot.classList.remove('ps-card-status--active');
    }
  });

  var activeCard = document.getElementById('ps-' + projectId);
  if (activeCard) {
    activeCard.classList.add('active');
    var statusDot = activeCard.querySelector('.ps-card-status');
    if (statusDot) {
      statusDot.textContent = '●';
      statusDot.classList.add('ps-card-status--active');
    }
  }

  document.dispatchEvent(new CustomEvent('projectChanged', { detail: { project: projectId } }));
}

window.applyScenarioSnapshot = function(snapshot, scenarioId) {
  if (!snapshot) return;
  Object.keys(snapshot).forEach(function(key) {
    var field = document.getElementById(key) || document.querySelector('[name="' + key + '"]');
    if (field) field.value = snapshot[key];
  });
  var currentId = document.getElementById('current_saved_scenario_id');
  if (currentId) currentId.value = scenarioId || '';
};

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.ws-tab[data-tab]').forEach(function(tabBtn) {
    tabBtn.addEventListener('click', function() {
      var tabId = tabBtn.getAttribute('data-tab');
      if (tabId) switchTab(tabId);
    });
  });

  var hash = window.location.hash.replace('#', '');
  if (hash) {
    var hashTab = document.querySelector('.ws-tab[data-tab="' + hash + '"]');
    if (hashTab) setTimeout(function() { switchTab(hash); }, 0);
  } else {
    var defaultTab = document.querySelector('.ws-tab[data-tab="overview"]');
    var defaultPanel = document.getElementById('panel-overview');
    if (defaultTab) defaultTab.classList.add('active');
    if (defaultPanel) defaultPanel.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(function(panel) {
      if (panel.id !== 'panel-overview') panel.classList.remove('active');
    });
  }

  window.addEventListener('hashchange', function() {
    var currentHash = window.location.hash.replace('#', '');
    if (currentHash && currentHash !== activeTab) switchTab(currentHash);
  });

  document.querySelectorAll('.sidebar-nav-link').forEach(function(link) {
    link.addEventListener('click', function() {
      var href = link.getAttribute('href');
      if (!href || !href.startsWith('#')) return;
      var id = href.substring(1);
      if (!id || id === 'dashboard' || id === 'audit') return;

      document.querySelectorAll('.sidebar-nav-link').forEach(function(other) {
        other.classList.remove('active');
      });
      link.classList.add('active');

      var target = document.getElementById(id);
      if (target && target.tagName === 'DETAILS' && !target.hasAttribute('open')) {
        target.setAttribute('open', '');
      }
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  var runBtn = document.getElementById('btn-run-model');
  if (runBtn) {
    runBtn.addEventListener('click', function() {
      var form = document.getElementById('main-form');
      if (form) form.dispatchEvent(new CustomEvent('runModelRequested', { bubbles: true }));
    });
  }

  var saveBtn = document.getElementById('btn-save');
  if (saveBtn) {
    saveBtn.addEventListener('click', function() {
      var form = document.getElementById('main-form');
      if (form) form.dispatchEvent(new CustomEvent('saveRequested', { bubbles: true }));
    });
  }

  var duplicateBtn = document.getElementById('btn-duplicate-scenario');
  if (duplicateBtn) {
    duplicateBtn.addEventListener('click', function() {
      var currentId = document.getElementById('current_saved_scenario_id');
      if (!currentId || !currentId.value || !window.htmx) {
        alert('Select a saved scenario first by loading it from the saved list.');
        return;
      }
      window.htmx.ajax('POST', '/scenarios/' + currentId.value + '/duplicate', {
        target: '#saved-scenario-panel',
        swap: 'outerHTML'
      });
    });
  }

  document.querySelectorAll('.input-group-summary').forEach(function(summary) {
    summary.addEventListener('click', function() {
      var group = summary.parentElement;
      if (group.hasAttribute('open')) {
        group.removeAttribute('open');
      } else {
        group.setAttribute('open', '');
      }
    });
  });
});
