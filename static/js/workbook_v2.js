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

  // Initialize: first tab active, rest -1
  if (tabs.length > 0) {
    activateTab(tabs[0]);
  }

  // After HTMX settles, ensure the currently selected tab's panel remains visible
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

  // input event (fires on every keystroke) marks the field pending.
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
      // Keep saving state active; clear pending only — HTMX afterRequest clears saving.
      if (form) { _markSaving(form); v2ClearPending(input); form.requestSubmit(); }
    }
  };

  // Transition to saving state just before HTMX fires the field form request.
  document.addEventListener('htmx:beforeRequest', function (event) {
    var form = event.detail.elt;
    if (!form || !form.classList || !form.classList.contains('v2-field-form')) return;
    _markSaving(form);
    var input = form.querySelector('.v2-field-input');
    if (input) v2ClearPending(input);
  });

  // Clear saving state after request completes (success or error).
  document.addEventListener('htmx:afterRequest', function (event) {
    var form = event.detail.elt;
    if (!form || !form.classList || !form.classList.contains('v2-field-form')) return;
    if (event.detail.successful) {
      _markSaved(form);
    } else {
      _markError(form);
    }
  });

  // Block the Run form (class="v2-run-form") when any field is pending or saving.
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.classList.contains('v2-run-form')) return;
    var pending = document.querySelector('.v2-field-input[data-pending="true"]');
    var saving  = document.querySelector('.v2-field-row.v2-field-saving');
    if (pending || saving) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (pending) pending.focus();
    }
  }, true);

  // Also intercept HTMX-driven Run requests.
  document.addEventListener('htmx:confirm', function (event) {
    var elt = event.detail.elt;
    if (!elt || !elt.classList || !elt.classList.contains('v2-run-form')) return;
    var pending = document.querySelector('.v2-field-input[data-pending="true"]');
    var saving  = document.querySelector('.v2-field-row.v2-field-saving');
    if (pending || saving) {
      event.preventDefault();
      if (pending) pending.focus();
    }
  });
}());
