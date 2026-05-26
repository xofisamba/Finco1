/* Finco One workspace interactions */

var activeTab = 'overview';
var draftPersistTimer = null;

function showNewProjectPanel() {
  // Hide all panels, show the new project panel in main workspace
  document.querySelectorAll('.tab-panel').forEach(function(p) {
    p.classList.remove('active');
    if (p.id !== 'panel-new-project') p.style.display = 'none';
  });
  var np = document.getElementById('panel-new-project');
  if (np) {
    np.style.display = 'block';
    np.classList.add('active');
  }
  document.querySelectorAll('.ws-tab').forEach(function(t) { t.classList.remove('active'); });
  var workspace = document.getElementById('workspace-content');
  if (workspace) workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeNewProjectPanel() {
  var np = document.getElementById('panel-new-project');
  if (np) {
    np.style.display = 'none';
    np.classList.remove('active');
  }
  // Restore overview tab
  switchTab('overview');
}

function duplicateCurrentScenario() {
  var currentId = document.getElementById('current_saved_scenario_id');
  if (!currentId || !currentId.value) {
    alert('Load a saved scenario first.');
    return;
  }
  if (window.htmx) {
    window.htmx.ajax('POST', '/scenarios/' + currentId.value + '/duplicate', {
      target: '#saved-scenario-panel',
      swap: 'outerHTML'
    });
  }
}

function setButtonDisabledState(id, disabled) {
  var btn = document.getElementById(id);
  if (!btn) return;
  btn.disabled = !!disabled;
  btn.setAttribute('aria-disabled', disabled ? 'true' : 'false');
}

function setActionReason(id, reason) {
  var btn = document.getElementById(id);
  if (!btn) return;
  if (reason) {
    btn.setAttribute('title', reason);
    btn.setAttribute('data-disabled-reason', reason);
  } else {
    btn.removeAttribute('title');
    btn.removeAttribute('data-disabled-reason');
  }
}

function updateReviewerActionHelp(meta) {
  var helper = document.getElementById('reviewer-action-help');
  if (!helper) return;
  var dirtyMessage = helper.getAttribute('data-dirty-message') || '';
  var cleanMessage = helper.getAttribute('data-clean-message') || '';
  helper.textContent = meta && meta.dirty ? dirtyMessage : cleanMessage;
}

function updateExportLineageGuidance(meta) {
  var helper = document.getElementById('reviewer-export-lineage-help');
  if (helper) {
    var dirtyMessage = helper.getAttribute('data-dirty-message') || '';
    var cleanMessage = helper.getAttribute('data-clean-message') || '';
    helper.textContent = meta && meta.dirty ? dirtyMessage : cleanMessage;
  }

  var lineageNote = document.getElementById('export-lineage-guidance');
  if (lineageNote) {
    lineageNote.textContent = meta && meta.dirty
      ? 'Unsaved draft edits are active. Runtime-backed exports remain tied to the last clean backend snapshot until you save and run again.'
      : 'Draft and saved state are aligned. Runtime-backed exports reflect the last clean backend runtime boundary shown in the workspace.';
  }

  var lineageChip = document.getElementById('export-lineage-dirty-chip');
  if (lineageChip && meta && meta.dirty_label) {
    lineageChip.textContent = meta.dirty_label;
  }
}

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
  if (window.syncEditableGridMirrors) {
    window.syncEditableGridMirrors();
  }
};

window.syncEditableGridMirrors = function() {
  document.querySelectorAll('[data-grid-source]').forEach(function(input) {
    var sourceId = input.getAttribute('data-grid-source');
    if (!sourceId) return;
    var source = document.getElementById(sourceId);
    if (!source) return;
    if (document.activeElement !== input) {
      input.value = source.value || '';
    }
  });
};

window.applyWorkspaceStateMeta = function(meta) {
  if (!meta) return;
  var currentId = document.getElementById('current_saved_scenario_id');
  if (currentId && typeof meta.active_scenario_id !== 'undefined') currentId.value = meta.active_scenario_id || '';
  var dirty = document.getElementById('workspace_dirty_state');
  if (dirty && typeof meta.dirty !== 'undefined') dirty.value = meta.dirty ? '1' : '0';
  var runtimeId = document.getElementById('last_runtime_snapshot_id');
  if (runtimeId && typeof meta.last_runtime_snapshot_id !== 'undefined') runtimeId.value = meta.last_runtime_snapshot_id || '';

  var activeName = document.getElementById('workspace-active-scenario-name');
  if (activeName && typeof meta.active_scenario_name !== 'undefined') {
    activeName.textContent = meta.active_scenario_name || 'Workspace Base';
  }
  var dirtyLabel = document.getElementById('workspace-dirty-label');
  if (dirtyLabel && meta.dirty_label) dirtyLabel.textContent = meta.dirty_label;
  var runtimeLabel = document.getElementById('workspace-runtime-origin-label');
  if (runtimeLabel && meta.last_runtime_origin_label) runtimeLabel.textContent = meta.last_runtime_origin_label;
  var runtimeChip = document.getElementById('workspace-runtime-snapshot-id');
  if (runtimeChip) runtimeChip.textContent = meta.last_runtime_snapshot_id || 'No runtime snapshot';
  var stripActive = document.getElementById('workspace-strip-active-scenario');
  if (stripActive && typeof meta.active_scenario_name !== 'undefined') stripActive.textContent = meta.active_scenario_name || 'Workspace Base';
  var stripDirty = document.getElementById('workspace-strip-dirty');
  if (stripDirty && meta.dirty_label) stripDirty.textContent = meta.dirty_label;
  var stripOrigin = document.getElementById('workspace-strip-runtime-origin');
  if (stripOrigin && meta.last_runtime_origin_label) stripOrigin.textContent = meta.last_runtime_origin_label;
  var stripSnap = document.getElementById('workspace-strip-runtime-snapshot');
  if (stripSnap) stripSnap.textContent = meta.last_runtime_snapshot_id || 'Not yet run';
  var banner = document.getElementById('workspace-unsaved-banner');
  if (banner) banner.classList.toggle('is-hidden', !meta.dirty);
  var bannerActive = document.getElementById('workspace-banner-active-scenario');
  if (bannerActive && typeof meta.active_scenario_name !== 'undefined') bannerActive.textContent = meta.active_scenario_name || 'Workspace Base';
  var bannerOrigin = document.getElementById('workspace-banner-runtime-origin');
  if (bannerOrigin && meta.last_runtime_origin_label) bannerOrigin.textContent = meta.last_runtime_origin_label;

  var dirtyReason = 'Disabled because unsaved draft edits exist. Save or revert first.';
  ['btn-run-model-sidebar', 'btn-compare-draft', 'btn-save-run'].forEach(function(id) {
    setButtonDisabledState(id, !!meta.dirty);
    setActionReason(id, meta.dirty ? dirtyReason : '');
  });
  updateReviewerActionHelp(meta);
  updateExportLineageGuidance(meta);
};

window.refreshScenarioWorkspace = function(projectId) {
  if (!projectId || !window.htmx) return;
  window.htmx.ajax('GET', '/scenarios?project=' + encodeURIComponent(projectId), {
    target: '#saved-scenario-panel',
    swap: 'outerHTML'
  });
};

function queueWorkspaceDraftPersist() {
  var form = document.getElementById('main-form');
  if (!form) return;
  if (draftPersistTimer) window.clearTimeout(draftPersistTimer);
  draftPersistTimer = window.setTimeout(function() {
    var payload = new URLSearchParams(new FormData(form));
    fetch('/scenarios/state/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: payload.toString(),
      credentials: 'same-origin'
    })
      .then(function(resp) { return resp.ok ? resp.json() : null; })
      .then(function(data) {
        if (data && window.applyWorkspaceStateMeta) {
          window.applyWorkspaceStateMeta(data);
        }
        if (window.syncEditableGridMirrors) {
          window.syncEditableGridMirrors();
        }
      })
      .catch(function() {
        // Best-effort draft persistence only; keep the workspace usable if this fails.
      });
  }, 350);
}

function bindDraftPersistenceFields(root) {
  var scope = root || document;
  var mainForm = document.getElementById('main-form');
  if (!mainForm || !mainForm.contains(scope) && scope !== document) return;
  mainForm.querySelectorAll('input, select, textarea').forEach(function(field) {
    if (field.type === 'hidden' || field.dataset.draftBound === '1') return;
    field.dataset.draftBound = '1';
    field.addEventListener('input', queueWorkspaceDraftPersist);
    field.addEventListener('change', queueWorkspaceDraftPersist);
  });
}

function bindEditableGridInputs(root) {
  var scope = root || document;
  scope.querySelectorAll('[data-grid-source]').forEach(function(input) {
    if (input.dataset.gridBound === '1') return;
    input.dataset.gridBound = '1';
    input.addEventListener('input', function() {
      var source = document.getElementById(input.getAttribute('data-grid-source'));
      if (!source) return;
      source.value = input.value;
      source.dispatchEvent(new Event('input', { bubbles: true }));
    });
    input.addEventListener('change', function() {
      var source = document.getElementById(input.getAttribute('data-grid-source'));
      if (!source) return;
      source.value = input.value;
      source.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
}

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

  var sidebarRunBtn = document.getElementById('btn-run-model-sidebar');
  if (sidebarRunBtn) {
    sidebarRunBtn.addEventListener('click', function() {
      var realRunBtn = document.getElementById('btn-run-model');
      if (realRunBtn) realRunBtn.click();
    });
  }

  var saveBtn = document.getElementById('btn-save');
  if (saveBtn) {
    saveBtn.addEventListener('click', function() {
      var form = document.getElementById('main-form');
      if (form) form.dispatchEvent(new CustomEvent('saveRequested', { bubbles: true }));
    });
  }

  if (window.syncEditableGridMirrors) {
    window.syncEditableGridMirrors();
  }

  var discardBtn = document.getElementById('btn-discard-edits');
  if (discardBtn) {
    discardBtn.addEventListener('click', function() {
      var form = document.getElementById('main-form');
      if (!form) return;
      var payload = new URLSearchParams(new FormData(form));
      fetch('/scenarios/state/discard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
        body: payload.toString(),
        credentials: 'same-origin'
      })
        .then(function(resp) { return resp.ok ? resp.json() : null; })
        .then(function(data) {
          if (!data) return;
          if (data.snapshot && window.applyScenarioSnapshot) {
            window.applyScenarioSnapshot(data.snapshot, data.active_scenario_id || '');
          }
          if (window.applyWorkspaceStateMeta) {
            window.applyWorkspaceStateMeta(data);
          }
          var activeProject = document.getElementById('active_project');
          if (activeProject && window.refreshScenarioWorkspace) {
            window.refreshScenarioWorkspace(activeProject.value);
          }
        })
        .catch(function() {
          alert('Could not discard edits right now.');
        });
    });
  }

  // duplicateCurrentScenario() is called via onclick on the button (defined at top of file)

  bindDraftPersistenceFields(document);
  bindEditableGridInputs(document);

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

document.addEventListener('htmx:afterSwap', function(evt) {
  var target = evt && evt.target ? evt.target : document;
  bindDraftPersistenceFields(target);
  bindEditableGridInputs(target);
  if (window.syncEditableGridMirrors) {
    window.syncEditableGridMirrors();
  }
  // Show panel-new-project after HTMX swaps content into it
  var panel = document.getElementById('panel-new-project');
  if (panel && panel.style.display === 'none' && panel.querySelector('form')) {
    panel.style.display = 'block';
    panel.classList.add('active');
  }
});
