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
    // Honour ?sheet=<name> URL param so New Project lands on the correct tab.
    var sheetParam = new URLSearchParams(window.location.search).get('sheet');
    var initialTab = sheetParam
      ? tabs.find(function(t) { return t.id === 'tab-' + sheetParam; }) || tabs[0]
      : tabs[0];
    activateTab(initialTab);
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

// Scoped HTMX handling for controlled Slice 1 application errors.
(function () {
  var SLICE1_UPDATE_ENDPOINT = '/v2/workbook/inputs-slice1/update';
  var CONTROLLED_SWAP_STATUSES = { 409: true, 422: true };

  window.v2ShouldSwapSlice1ErrorResponse = function (event) {
    var detail = (event && event.detail) || {};
    var xhr = detail.xhr || {};
    var status = xhr.status;
    var requestPath = '';

    if (xhr.responseURL) {
      requestPath = xhr.responseURL;
    } else if (detail.pathInfo && detail.pathInfo.requestPath) {
      requestPath = detail.pathInfo.requestPath;
    } else if (detail.requestConfig && detail.requestConfig.path) {
      requestPath = detail.requestConfig.path;
    }

    return !!(
      CONTROLLED_SWAP_STATUSES[status] &&
      requestPath.indexOf(SLICE1_UPDATE_ENDPOINT) !== -1
    );
  };

  document.addEventListener('htmx:beforeSwap', function (event) {
    if (!window.v2ShouldSwapSlice1ErrorResponse(event)) return;
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  });
}());

// ── Field editor: pending / saving / saved / error state machine ──────────
(function () {
  if (window.__v2FieldEditorInitialised) return;
  window.__v2FieldEditorInitialised = true;

  // --- Run queue state ---
  var _runQueued = false;
  var _inFlightSaveCount = 0;  // explicit counter; HX-Trigger fires BEFORE htmx:afterRequest

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
    // HX-Trigger (workbook-field-saved) fires BEFORE htmx:afterRequest in HTMX 1.9.x,
    // so the form may still carry v2-field-saving when this is called from the
    // saved-event handler. The in-flight counter is the authoritative gate.
    if (_inFlightSaveCount > 0) return;
    if (_hasPendingOrSaving()) return;  // belt-and-suspenders for any race

    _runQueued = false;
    _setRunBtnState(null, false);

    var runForm = document.querySelector('.v2-run-form');
    if (!runForm) return;

    // Use htmx.ajax() directly so the request is always sent via HTMX with
    // HX-Request:true — regardless of whether the run form was replaced by an
    // OOB swap between the field-save response and this call (which would leave
    // requestSubmit() racing against HTMX re-initialising the new element).
    var action = runForm.getAttribute('action') || '/v2/workbook/run';
    var values = {};
    Array.prototype.forEach.call(runForm.querySelectorAll('input'), function(inp) {
      if (inp.name) values[inp.name] = inp.value;
    });
    htmx.ajax('POST', action, {
      source: runForm,
      target: 'body',
      swap: 'none',
      values: values
    });
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
    _inFlightSaveCount++;
    _markSaving(form);
    var input = form.querySelector('.v2-field-input');
    if (input) v2ClearPending(input);
  });

  document.addEventListener('htmx:afterRequest', function (event) {
    var form = event.detail.elt;
    // When hx-target outerHTML swap replaces the panel, elt may be the new target
    // element rather than the original form. Fall back to URL matching.
    var isFieldForm = form && form.classList && form.classList.contains('v2-field-form');
    if (!isFieldForm) {
      var xhr = event.detail.xhr;
      if (!xhr || xhr.responseURL.indexOf('/v2/workbook/update') === -1) return;
      // elt is not the field form — decrement counter and gate queued run by URL match
      _inFlightSaveCount = Math.max(0, _inFlightSaveCount - 1);
      if (event.detail.successful) {
        _tryFireQueuedRun();
      } else if (_runQueued) {
        _runQueued = false;
        _setRunBtnState(null, false);
      }
      return;
    }
    if (!form) return;
    // Always decrement — pairs with the increment in htmx:beforeRequest.
    _inFlightSaveCount = Math.max(0, _inFlightSaveCount - 1);
    if (event.detail.successful) {
      _markSaved(form);
      var input = form.querySelector('.v2-field-input');
      if (input) input.setAttribute('data-original-value', input.value);
      // Primary gate: try queued Run now that saving state AND counter are clear.
      // (workbook-field-saved may have already tried and been blocked by the counter.)
      _tryFireQueuedRun();
    } else {
      _markError(form);
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
