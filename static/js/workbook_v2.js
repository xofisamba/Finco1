// ── Tab navigation ──────────────────────────────────────────────
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('#v2-sheet-tabs .v2-tab'));
  var panels = Array.prototype.slice.call(document.querySelectorAll('.v2-sheet-panel'));

  function activateTab(btn) {
    tabs.forEach(function(t) {
      t.setAttribute('aria-selected', 'false');
      t.setAttribute('tabindex', '-1');
    });
    panels.forEach(function(p) { p.hidden = true; });
    btn.setAttribute('aria-selected', 'true');
    btn.setAttribute('tabindex', '0');
    var panel = document.getElementById(btn.getAttribute('aria-controls'));
    if (panel) panel.hidden = false;
  }

  tabs.forEach(function(btn, idx) {
    btn.addEventListener('click', function() { activateTab(btn); btn.focus(); });
    btn.addEventListener('keydown', function(e) {
      var newIdx;
      if (e.key === 'ArrowRight') { newIdx = (idx + 1) % tabs.length; }
      else if (e.key === 'ArrowLeft') { newIdx = (idx + tabs.length - 1) % tabs.length; }
      else if (e.key === 'Enter' || e.key === ' ') { activateTab(btn); e.preventDefault(); return; }
      else { return; }
      e.preventDefault();
      activateTab(tabs[newIdx]);
      tabs[newIdx].focus();
    });
  });

  if (tabs.length > 0) {
    activateTab(tabs[0]);
  }

  document.addEventListener('htmx:afterSwap', function() {
    var selectedTab = tabs.find(function(t) {
      return t.getAttribute('aria-selected') === 'true';
    });
    if (selectedTab) {
      var panelId = selectedTab.getAttribute('aria-controls');
      var panel = document.getElementById(panelId);
      if (panel) panel.hidden = false;
    }
  });
})();

// ── Field editor: pending / saving / saved / error state machine ──────────
(function () {
  if (window.__v2FieldEditorInitialised) return;
  window.__v2FieldEditorInitialised = true;

  // --- Run queue state ---
  var _runQueued = false;
  var _pendingSaveForms = [];  // forms currently in-flight

  function _row(input) { return input.closest('.v2-field-row'); }

  window.v2MarkPending = function (input) {
    input.setAttribute('data-pending', 'true');
    var row = _row(input);
    if (row) { row.classList.add('v2-field-pending'); row.classList.remove('v2-field-saving', 'v2-field-error'); }
  };

  window.v2ClearPending = function (input) {
    input.setAttribute('data-pending', 'false');
    var row = _row(input);
    if (row) row.classList.remove('v2-field-pending');
  };

  function _markSaving(form) {
    var row = form.closest('.v2-field-row');
    if (row) { row.classList.add('v2-field-saving'); row.classList.remove('v2-field-pending', 'v2-field-error'); }
  }

  function _markSaved(form) {
    var row = form.closest('.v2-field-row');
    if (row) { row.classList.remove('v2-field-saving', 'v2-field-pending'); }
  }

  function _markError(form) {
    var row = form.closest('.v2-field-row');
    if (row) { row.classList.add('v2-field-error'); row.classList.remove('v2-field-saving', 'v2-field-pending'); }
  }

  function _hasPendingOrSaving() {
    return !!(
      document.querySelector('.v2-field-input[data-pending="true"]') ||
      document.querySelector('.v2-field-row.v2-field-saving')
    );
  }

  function _setRunBtnState(label, disabled) {
    var btns = document.querySelectorAll('.v2-run-btn');
    btns.forEach(function(btn) {
      btn.disabled = disabled;
      if (label) btn.textContent = label;
    });
  }

  function _submitAllPendingForms() {
    var pendingInputs = Array.prototype.slice.call(
      document.querySelectorAll('.v2-field-input[data-pending="true"]')
    );
    pendingInputs.forEach(function(inp) {
      var form = inp.closest('form');
      if (form && form.classList.contains('v2-field-form')) {
        _markSaving(form);
        v2ClearPending(inp);
        form.requestSubmit();
      }
    });
  }

  function _tryFireQueuedRun() {
    if (!_runQueued) return;
    if (_hasPendingOrSaving()) return;

    _runQueued = false;
    _setRunBtnState(null, false);

    // Read newest hash from Run form hidden input
    var runForm = document.querySelector('.v2-run-form');
    if (!runForm) return;

    // Submit run once via HTMX
    htmx.trigger(runForm, 'submit');
  }

  // input event marks field pending
  document.addEventListener('input', function (e) {
    var inp = e.target;
    if (!inp.classList.contains('v2-field-input')) return;
    v2MarkPending(inp);
  });

  window.v2FieldKeydown = function (event) {
    var input = event.target;
    if (event.key === 'Enter') {
      event.preventDefault();
      var form = input.closest('form');
      if (form) { _markSaving(form); v2ClearPending(input); form.requestSubmit(); }
    } else if (event.key === 'Escape') {
      event.preventDefault();
      var original = input.getAttribute('data-original-value');
      if (original !== null) input.value = original;
      v2ClearPending(input);
      input.blur();
    }
  };

  window.v2FieldBlur = function (event) {
    var input = event.target;
    if (input.getAttribute('data-pending') === 'true') {
      var form = input.closest('form');
      if (form) { _markSaving(form); v2ClearPending(input); form.requestSubmit(); }
    }
  };

  document.addEventListener('htmx:beforeRequest', function (event) {
    var form = event.detail.elt;
    if (!form || !form.classList || !form.classList.contains('v2-field-form')) return;
    _markSaving(form);
    var input = form.querySelector('.v2-field-input');
    if (input) v2ClearPending(input);
  });

  document.addEventListener('htmx:afterRequest', function (event) {
    var form = event.detail.elt;
    if (!form || !form.classList || !form.classList.contains('v2-field-form')) return;
    if (event.detail.successful) {
      _markSaved(form);
      // Update data-original-value to saved value
      var input = form.querySelector('.v2-field-input');
      if (input) {
        input.setAttribute('data-original-value', input.value);
      }
    } else {
      _markError(form);
      // Cancel queued run on save failure
      if (_runQueued) {
        _runQueued = false;
        _setRunBtnState(null, false);
      }
    }
  });

  // Listen for server save signals (HX-Trigger headers)
  document.addEventListener('workbook-field-saved', function (e) {
    var detail = e.detail || {};
    var newHash = detail.new_hash;
    if (newHash) {
      // Update all hash inputs in Run form and shell
      document.querySelectorAll('input[name="content_hash"]').forEach(function(inp) {
        inp.value = newHash;
      });
      var shell = document.getElementById('v2-workbook-shell');
      if (shell) shell.setAttribute('data-content-hash', newHash);
    }
    _tryFireQueuedRun();
  });

  document.addEventListener('workbook-field-error', function () {
    if (_runQueued) {
      _runQueued = false;
      _setRunBtnState(null, false);
    }
  });

  // Intercept Run submit: if pending/saving fields exist, queue run and save first
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.classList.contains('v2-run-form')) return;
    if (_hasPendingOrSaving()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      _runQueued = true;
      _setRunBtnState('Saving changes…', true);
      _submitAllPendingForms();
    }
  }, true);

  // Also intercept HTMX-driven Run requests
  document.addEventListener('htmx:confirm', function (event) {
    var elt = event.detail.elt;
    if (!elt || !elt.classList || !elt.classList.contains('v2-run-form')) return;
    if (_hasPendingOrSaving()) {
      event.preventDefault();
      _runQueued = true;
      _setRunBtnState('Saving changes…', true);
      _submitAllPendingForms();
    }
  });
}());

// ── FS UI state restore after HTMX swap ──────────────────────────────────
// The inline scripts in sheet_financial_statements.html define v2FsInnerTabSwitch
// and v2FsPeriodSwitch with sessionStorage persistence. After an HTMX swap that
// re-renders the FS partial we call them to restore the user's last selection.
document.addEventListener('htmx:afterSettle', function(e) {
  var elt = e.detail && e.detail.elt;
  // Only restore if the FS sheet was part of the swap target
  if (!elt) return;
  var fsPanel = elt.id === 'v2-sheet-financial-statements' ? elt :
                elt.querySelector && elt.querySelector('#v2-sheet-financial-statements');
  if (!fsPanel && !document.getElementById('v2-sheet-financial-statements')) return;
  try {
    var savedTab = sessionStorage.getItem('v2FsInnerTab');
    if (savedTab && typeof v2FsInnerTabSwitch === 'function') {
      v2FsInnerTabSwitch(savedTab);
    }
    var savedView = sessionStorage.getItem('v2FsPeriodView');
    if (savedView && typeof v2FsPeriodSwitch === 'function') {
      v2FsPeriodSwitch(savedView);
    }
  } catch(err) {}
});
