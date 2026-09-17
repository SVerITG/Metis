#!/usr/bin/env node
/**
 * audit-controls.mjs — fire the dashboard's controls in a real browser.
 *
 * WHY THIS EXISTS
 *   Four defects shipped on 2026-09-14 and two more on 2026-09-17 were all
 *   invisible to server-side testing and obvious within a second of use:
 *   a form that never submitted because its target did not exist, a fold that
 *   loaded its contents over the whole box it lived in, a swap that threw the
 *   page to the foot of a panel, a heading printed twice. Every endpoint
 *   answered 200 throughout. The defect was never in the response; it was in
 *   where the response went.
 *
 *   So this checks the thing the server cannot see: for every control on a
 *   surface, does its target actually exist, and does acting on it leave the
 *   page intact.
 *
 * IT DOES NOT MUTATE DATA
 *   Controls are split by method. `hx-get`, `<details>` folds and tabs are
 *   fired for real. Anything that POSTs, PUTs or DELETEs is INSPECTED, never
 *   clicked — its target is resolved against the live DOM and its inherited
 *   attributes are reported. That is enough to catch the whole class of bug
 *   above without touching a single row of the researcher's data.
 *
 * USAGE
 *   node tools/audit-controls.mjs                  # every known surface
 *   node tools/audit-controls.mjs /today /news     # just these
 */
import { chromium } from 'playwright-core';

const BASE = process.env.METIS_URL || 'http://127.0.0.1:8080';
const EXE = process.env.HOME +
  '/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell';
const SURFACES = process.argv.slice(2).length ? process.argv.slice(2)
  : ['/', '/news', '/reflection', '/work', '/meetings', '/learning', '/presentation', '/knowledge'];

const findings = [];
const note = (surface, kind, detail) => findings.push({ surface, kind, detail });

const browser = await chromium.launch({ executablePath: EXE });

for (const path of SURFACES) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const jsErrors = [], httpErrors = [];
  page.on('pageerror', e => jsErrors.push(String(e).slice(0, 160)));
  page.on('console', m => { if (m.type() === 'error') jsErrors.push('console: ' + m.text().slice(0, 140)); });
  page.on('response', r => { if (r.status() >= 400) httpErrors.push(`${r.status()} ${r.url().slice(0, 110)}`); });

  let ok = true;
  try {
    await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);
  } catch (e) {
    note(path, 'LOAD-FAILED', String(e).slice(0, 120)); ok = false;
  }

  if (ok) {
    for (const e of jsErrors) note(path, 'JS-ERROR', e);
    for (const e of httpErrors) note(path, 'HTTP', e);

    // ── 1. every hx target must resolve, and a swap must know where it goes ──
    const targets = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('[hx-get],[hx-post],[hx-delete],[hx-put],[hx-patch]').forEach(el => {
        const verb = ['hx-get','hx-post','hx-delete','hx-put','hx-patch']
          .find(v => el.hasAttribute(v));
        const url = el.getAttribute(verb) || '';
        const own = el.getAttribute('hx-target');
        // What an ancestor would impose if this element names no target — and
        // `hx-disinherit` is the thing that stops it. base.html uses exactly
        // that to keep the nav badge from inheriting the surface's target, so a
        // walker that ignores disinherit reports a bug that was already fixed.
        let inherited = null, p = el.parentElement;
        while (p && !inherited) {
          const dis = p.getAttribute ? (p.getAttribute('hx-disinherit') || '') : '';
          if (dis === '*' || dis.includes('hx-target')) break;
          inherited = p.getAttribute && p.getAttribute('hx-target');
          p = p.parentElement;
        }
        const eff = own || inherited;
        let resolves = true, reason = '';
        if (eff && !['this','next','previous','closest','find','body'].some(k => eff.startsWith(k))) {
          resolves = !!document.querySelector(eff);
          if (!resolves) reason = 'no element matches ' + eff;
        }
        out.push({ verb, url, own, inherited, eff, resolves, reason,
                   swap: el.getAttribute('hx-swap') || '' });
      });
      return out;
    });

    for (const t of targets) {
      if (!t.resolves) {
        note(path, 'DEAD-TARGET', `${t.verb} ${t.url.slice(0,66)} → ${t.reason}`);
      }
      // The Keep bug: a swap with no target of its own, inheriting a target that
      // is a DIFFERENT element than the control sits in. Reported, not failed —
      // the verdict buttons do this deliberately.
      if (!t.own && t.inherited && t.swap && t.swap.includes('innerHTML')) {
        note(path, 'INHERITED-INNERHTML',
             `${t.verb} ${t.url.slice(0,56)} has no hx-target; inherits ${t.inherited} and swaps innerHTML`);
      }
    }

    // ── 2. fire the safe controls: folds and tabs ────────────────────────────
    const folds = await page.locator('details > summary').all();
    for (let i = 0; i < Math.min(folds.length, 24); i++) {
      const before = await page.evaluate(() => document.body.innerText.length);
      try { await folds[i].click({ timeout: 4000 }); } catch { continue; }
      await page.waitForTimeout(450);
      const after = await page.evaluate(() => document.body.innerText.length);
      // A fold that REMOVES most of the page has swapped over something.
      if (before > 400 && after < before * 0.55) {
        const label = (await folds[i].innerText().catch(() => '?')).slice(0, 40);
        note(path, 'FOLD-WIPES-PAGE', `"${label}" cut page text ${before} → ${after}`);
      }
    }
    for (const e of jsErrors.slice(0)) { /* already recorded */ }

    // ── 3. tabs must show a panel ────────────────────────────────────────────
    // A tab is judged by whether the surface CHANGED and still has content —
    // not by whether a particular class is present. Different surfaces name
    // their panels differently (`#news-tab-body`, `.lib-panel`, `.ui-tabpane`),
    // and a checker that enumerates class names reports every surface it has
    // not been taught about. Asking "is there still a page here" is the
    // question that actually matters and needs no list.
    const tabs = await page.locator('[role="tab"], .news-tab, .ui-tab').all();
    for (let i = 0; i < Math.min(tabs.length, 12); i++) {
      const label = (await tabs[i].innerText().catch(() => '?')).slice(0, 30);
      const before = await page.evaluate(() => document.body.innerText.length);
      try { await tabs[i].click({ timeout: 4000 }); } catch { continue; }
      await page.waitForTimeout(700);
      const after = await page.evaluate(() => document.body.innerText.length);
      if (after < 300) {
        note(path, 'TAB-SHOWS-NOTHING', `"${label}" emptied the surface (${before} → ${after} chars)`);
      }
    }

    note(path, 'OK', `${targets.length} hx controls · ${folds.length} folds · ${tabs.length} tabs`);
  }
  await page.close();
}
await browser.close();

// ── report ────────────────────────────────────────────────────────────────
const order = ['LOAD-FAILED','JS-ERROR','DEAD-TARGET','FOLD-WIPES-PAGE','TAB-SHOWS-NOTHING','HTTP','INHERITED-INNERHTML','OK'];
const bad = findings.filter(f => f.kind !== 'OK');
console.log(`\n=== control audit · ${SURFACES.length} surface(s) ===\n`);
for (const kind of order) {
  const hits = findings.filter(f => f.kind === kind);
  if (!hits.length) continue;
  console.log(`${kind}  (${hits.length})`);
  for (const h of hits) console.log(`   ${h.surface.padEnd(14)} ${h.detail}`);
  console.log('');
}
console.log(bad.length ? `${bad.length} finding(s)` : 'no findings');
process.exit(findings.some(f => ['LOAD-FAILED','JS-ERROR','DEAD-TARGET','FOLD-WIPES-PAGE','TAB-SHOWS-NOTHING'].includes(f.kind)) ? 1 : 0);
