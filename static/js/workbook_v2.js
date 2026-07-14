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

// ── Field keyboard handling ─────────────────────────────────────
document.addEventListener('keydown', function (e) {
  var inp = e.target;
  if (!inp.classList.contains('v2-field-input')) return;
  if (e.key === 'Escape') {
    inp.value = inp.defaultValue;
    inp.blur();
    e.preventDefault();
  } else if (e.key === 'Enter') {
    var form = inp.closest('form');
    if (form) { form.requestSubmit(); }
    e.preventDefault();
  }
});
