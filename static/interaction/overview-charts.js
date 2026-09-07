/**
 * UI-3A Overview charts — vanilla SVG renderer.
 *
 * Scans for .v2-overview-chart elements after DOM load; reads their
 * data-chart-type and data-periods attributes (JSON arrays of period dicts
 * from the authoritative debt_schedule.periods payload); renders inline SVG.
 *
 * Chart types:
 *   debt-balance  — Senior balance (area) + annual DS (bar overlay)
 *   dscr          — DSCR polyline with optional target-DSCR reference line
 *
 * No external dependencies. No financial computation.
 * Values are read verbatim from the authoritative engine output.
 */
(function () {
  'use strict';

  // ── Palette ─────────────────────────────────────────────────────────── //
  const C = {
    balance:    '#1e40af',  // deep blue — debt balance area
    balanceFill:'#dbeafe',
    ds:         '#6366f1',  // indigo — debt service bars
    dscr:       '#0f766e',  // teal — DSCR line
    target:     '#dc2626',  // red  — target DSCR reference
    axis:       '#9ca3af',
    label:      '#6b7280',
    gridLine:   '#f3f4f6',
  };

  // ── SVG helpers ────────────────────────────────────────────────────── //
  const SVG_NS = 'http://www.w3.org/2000/svg';

  function el(tag, attrs) {
    const e = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
    return e;
  }

  function svgRoot(w, h) {
    return el('svg', {
      viewBox: `0 0 ${w} ${h}`,
      preserveAspectRatio: 'none',
      width: '100%',
      height: h,
      role: 'img',
      'aria-hidden': 'true',
    });
  }

  // ── Data helpers ────────────────────────────────────────────────────── //

  /**
   * Aggregate semestrial periods to annual by year string.
   * Returns { years: string[], groups: Object[] } where each group is the
   * last-period (for stock) or sum (for flow) of all periods in that year.
   */
  function toAnnual(periods) {
    const map = new Map(); // year → { balanceLast, dsSum, dscrLast, count }
    const yearOrder = [];
    for (const p of periods) {
      const yr = (p.date || '').slice(0, 4);
      if (!yr) continue;
      if (!map.has(yr)) { map.set(yr, { bal: null, ds: 0, dscr: null }); yearOrder.push(yr); }
      const g = map.get(yr);
      if (p.senior_balance_keur != null) g.bal = p.senior_balance_keur;
      if (p.senior_ds_keur      != null) g.ds  += p.senior_ds_keur;
      if (p.dscr                != null && p.is_operation) g.dscr = p.dscr;
    }
    return { years: yearOrder, groups: yearOrder.map(yr => map.get(yr)) };
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function scaleY(v, vMin, vMax, top, bottom) {
    if (vMax === vMin) return (top + bottom) / 2;
    return bottom - ((v - vMin) / (vMax - vMin)) * (bottom - top);
  }

  // ── Tooltip helper ─────────────────────────────────────────────────── //
  function makeTitle(text) {
    const t = document.createElementNS(SVG_NS, 'title');
    t.textContent = text;
    return t;
  }

  // ── Debt Balance + DS chart ─────────────────────────────────────────── //
  function renderDebtBalance(container, periods) {
    const { years, groups } = toAnnual(periods);
    if (!years.length) { container.textContent = 'No debt schedule data.'; return; }

    const W = 620, H = 160, PAD = { t: 12, r: 8, b: 28, l: 52 };
    const plotW = W - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    const n = years.length;

    const balVals = groups.map(g => g.bal ?? 0);
    const dsVals  = groups.map(g => g.ds  ?? 0);
    const balMax  = Math.max(...balVals, 1);
    const dsMax   = Math.max(...dsVals, 1);
    const scale   = Math.max(balMax, dsMax * 4);  // DS bars share axis, scaled up

    const svg = svgRoot(W, H);
    const barW = Math.max(2, (plotW / n) - 2);

    // Grid lines (3)
    for (let i = 0; i <= 3; i++) {
      const y = PAD.t + (plotH / 3) * i;
      const g = el('line', { x1: PAD.l, y1: y, x2: W - PAD.r, y2: y, stroke: C.gridLine, 'stroke-width': 1 });
      svg.appendChild(g);
    }

    // Balance area
    const pts = groups.map((g, i) => {
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const y = scaleY(g.bal ?? 0, 0, scale, PAD.t, PAD.t + plotH);
      return `${x},${y}`;
    });
    const areaPath = [
      `M ${PAD.l},${PAD.t + plotH}`,
      ...groups.map((g, i) => {
        const x = PAD.l + (i / (n - 1 || 1)) * plotW;
        const y = scaleY(g.bal ?? 0, 0, scale, PAD.t, PAD.t + plotH);
        return `L ${x},${y}`;
      }),
      `L ${W - PAD.r},${PAD.t + plotH} Z`,
    ].join(' ');
    svg.appendChild(el('path', { d: areaPath, fill: C.balanceFill, stroke: 'none' }));
    svg.appendChild(el('polyline', { points: pts.join(' '), fill: 'none', stroke: C.balance, 'stroke-width': 1.5 }));

    // DS bars
    groups.forEach((g, i) => {
      const dsH = ((g.ds ?? 0) / scale) * plotH;
      const x   = PAD.l + (i / (n - 1 || 1)) * plotW - barW / 2;
      const y   = PAD.t + plotH - dsH;
      const rect = el('rect', {
        x, y, width: barW, height: Math.max(1, dsH),
        fill: C.ds, opacity: 0.65,
      });
      rect.appendChild(makeTitle(`${years[i]}: DS = ${(g.ds ?? 0).toFixed(0)} kEUR`));
      svg.appendChild(rect);
    });

    // Balance line points with tooltips
    groups.forEach((g, i) => {
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const y = scaleY(g.bal ?? 0, 0, scale, PAD.t, PAD.t + plotH);
      const c = el('circle', { cx: x, cy: y, r: 2.5, fill: C.balance });
      c.appendChild(makeTitle(`${years[i]}: Balance = ${(g.bal ?? 0).toFixed(0)} kEUR`));
      svg.appendChild(c);
    });

    // X-axis labels (every 5 years)
    const step = Math.max(1, Math.floor(n / 8));
    years.forEach((yr, i) => {
      if (i % step !== 0 && i !== n - 1) return;
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const t = el('text', { x, y: H - 6, 'text-anchor': 'middle', fill: C.label, 'font-size': 9 });
      t.textContent = yr;
      svg.appendChild(t);
    });

    // Y-axis label
    const yLbl = el('text', { x: 4, y: PAD.t + plotH / 2, fill: C.label, 'font-size': 9,
                               transform: `rotate(-90 4 ${PAD.t + plotH / 2})`, 'text-anchor': 'middle' });
    yLbl.textContent = 'kEUR';
    svg.appendChild(yLbl);

    // Legend
    const lgx = PAD.l + 4;
    const lgy = PAD.t + 4;
    svg.appendChild(el('rect', { x: lgx, y: lgy, width: 10, height: 4, fill: C.balanceFill, stroke: C.balance, 'stroke-width': 0.8 }));
    const lt1 = el('text', { x: lgx + 13, y: lgy + 4, fill: C.label, 'font-size': 8.5 }); lt1.textContent = 'Balance'; svg.appendChild(lt1);
    svg.appendChild(el('rect', { x: lgx + 58, y: lgy, width: 10, height: 4, fill: C.ds, opacity: 0.65 }));
    const lt2 = el('text', { x: lgx + 71, y: lgy + 4, fill: C.label, 'font-size': 8.5 }); lt2.textContent = 'Annual DS'; svg.appendChild(lt2);

    container.appendChild(svg);
  }

  // ── DSCR Profile chart ─────────────────────────────────────────────── //
  function renderDscr(container, periods, targetStr) {
    const opPeriods = periods.filter(p => p.is_operation && p.dscr != null);
    if (!opPeriods.length) { container.textContent = 'No DSCR data.'; return; }

    const W = 620, H = 140, PAD = { t: 12, r: 8, b: 28, l: 44 };
    const plotW = W - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    const n = opPeriods.length;

    const target = targetStr ? parseFloat(targetStr) : null;
    const vals   = opPeriods.map(p => p.dscr);
    const vMin   = Math.max(0, Math.min(...vals, target ?? Infinity) - 0.2);
    const vMax   = Math.max(...vals, target ?? 0) + 0.2;

    const svg = svgRoot(W, H);

    // Grid
    for (let i = 0; i <= 4; i++) {
      const y = PAD.t + (plotH / 4) * i;
      svg.appendChild(el('line', { x1: PAD.l, y1: y, x2: W - PAD.r, y2: y, stroke: C.gridLine, 'stroke-width': 1 }));
    }

    // Target line
    if (target != null) {
      const ty = scaleY(target, vMin, vMax, PAD.t, PAD.t + plotH);
      svg.appendChild(el('line', { x1: PAD.l, y1: ty, x2: W - PAD.r, y2: ty,
                                    stroke: C.target, 'stroke-width': 1, 'stroke-dasharray': '4 3' }));
      const tl = el('text', { x: W - PAD.r + 2, y: ty + 3, fill: C.target, 'font-size': 8 });
      tl.textContent = `${target.toFixed(2)}x`;
      svg.appendChild(tl);
    }

    // DSCR area fill
    const ptsFill = [
      `${PAD.l},${PAD.t + plotH}`,
      ...opPeriods.map((p, i) => {
        const x = PAD.l + (i / (n - 1 || 1)) * plotW;
        const y = scaleY(p.dscr, vMin, vMax, PAD.t, PAD.t + plotH);
        return `${x},${y}`;
      }),
      `${PAD.l + plotW},${PAD.t + plotH}`,
    ].join(' ');
    svg.appendChild(el('polygon', { points: ptsFill, fill: '#ccfbf1', stroke: 'none', opacity: 0.7 }));

    // DSCR polyline
    const pts = opPeriods.map((p, i) => {
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const y = scaleY(p.dscr, vMin, vMax, PAD.t, PAD.t + plotH);
      return `${x},${y}`;
    });
    svg.appendChild(el('polyline', { points: pts.join(' '), fill: 'none', stroke: C.dscr, 'stroke-width': 1.5 }));

    // Point tooltips (every 4th)
    opPeriods.forEach((p, i) => {
      if (i % 4 !== 0 && i !== n - 1) return;
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const y = scaleY(p.dscr, vMin, vMax, PAD.t, PAD.t + plotH);
      const c = el('circle', { cx: x, cy: y, r: 2.5, fill: C.dscr });
      c.appendChild(makeTitle(`${(p.date || '').slice(0, 7)}: DSCR = ${p.dscr.toFixed(2)}x`));
      svg.appendChild(c);
    });

    // X-axis: operation years (by period index)
    const step = Math.max(1, Math.floor(n / 8));
    opPeriods.forEach((p, i) => {
      if (i % (step * 2) !== 0 && i !== n - 1) return;
      const x = PAD.l + (i / (n - 1 || 1)) * plotW;
      const t = el('text', { x, y: H - 6, 'text-anchor': 'middle', fill: C.label, 'font-size': 9 });
      t.textContent = (p.date || '').slice(0, 4);
      svg.appendChild(t);
    });

    // Y-axis label
    const yLbl = el('text', { x: 6, y: PAD.t + plotH / 2, fill: C.label, 'font-size': 9,
                               transform: `rotate(-90 6 ${PAD.t + plotH / 2})`, 'text-anchor': 'middle' });
    yLbl.textContent = 'DSCR';
    svg.appendChild(yLbl);

    // Legend
    const lgx = PAD.l + 4, lgy = PAD.t + 4;
    svg.appendChild(el('line', { x1: lgx, y1: lgy + 2, x2: lgx + 12, y2: lgy + 2, stroke: C.dscr, 'stroke-width': 1.5 }));
    const lt = el('text', { x: lgx + 15, y: lgy + 5, fill: C.label, 'font-size': 8.5 }); lt.textContent = 'DSCR'; svg.appendChild(lt);
    if (target != null) {
      svg.appendChild(el('line', { x1: lgx + 48, y1: lgy + 2, x2: lgx + 60, y2: lgy + 2, stroke: C.target, 'stroke-width': 1, 'stroke-dasharray': '4 3' }));
      const lt2 = el('text', { x: lgx + 63, y: lgy + 5, fill: C.label, 'font-size': 8.5 }); lt2.textContent = 'Target'; svg.appendChild(lt2);
    }

    container.appendChild(svg);
  }

  // ── Tab navigation from Overview links ─────────────────────────────── //
  function initNavLinks() {
    document.querySelectorAll('[data-goto-tab]').forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        var targetTab = link.dataset.gotoTab;
        var btn = document.getElementById('tab-' + targetTab);
        if (btn) btn.click();
      });
    });
  }

  // ── Entry point ─────────────────────────────────────────────────────── //
  function init() {
    document.querySelectorAll('.v2-overview-chart').forEach(function (el) {
      const type    = el.dataset.chartType;
      const raw     = el.dataset.periods;
      const target  = el.dataset.target;
      if (!raw) return;
      let periods;
      try { periods = JSON.parse(raw); } catch (e) { return; }
      if (!Array.isArray(periods) || !periods.length) return;

      if (type === 'debt-balance') renderDebtBalance(el, periods);
      else if (type === 'dscr')    renderDscr(el, periods, target);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); initNavLinks(); });
  } else {
    init();
    initNavLinks();
  }
  // Re-run after HTMX swaps (in case overview panel is lazy-loaded later)
  document.addEventListener('htmx:afterSwap', init);
})();
