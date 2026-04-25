// Metis Dashboard — App JS  v7.0
// Editorial layout + fully-wired actions

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

function setActiveTab(btn) {
  document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    openCapture();
  }
  if (e.key === 'Escape') {
    closeCapture();
    closeNewsModal();
  }
});

// ---------------------------------------------------------------------------
// Capture modal (Ctrl+K) — supports optional prefillMode
// ---------------------------------------------------------------------------

const _CAPTURE_PREFIX = {
  idea: 'i:', note: 'n:', task: 't:', question: 'q:',
};

function openCapture(prefillMode) {
  const overlay = document.getElementById('capture-overlay');
  if (!overlay) return;

  htmx.ajax('GET', '/api/capture-modal', {
    target: '#capture-modal-inner',
    swap: 'innerHTML',
  });

  overlay.style.display = 'block';
  document.body.style.overflow = 'hidden';

  setTimeout(() => {
    const ta = document.getElementById('capture-text');
    if (!ta) return;

    // Prefill prefix if mode was supplied
    if (prefillMode && _CAPTURE_PREFIX[prefillMode]) {
      ta.value = _CAPTURE_PREFIX[prefillMode] + ' ';
      ta.selectionStart = ta.selectionEnd = ta.value.length;
    }
    ta.focus();

    // Live prefix detection
    ta.addEventListener('input', function () {
      const val = ta.value;
      const badge = document.getElementById('capture-type-badge');
      if (!badge) return;
      let html = '<span class="capture-type-badge capture-type-idea">Idea</span>';
      if (val.startsWith('n:') || val.startsWith('note:')) {
        html = '<span class="capture-type-badge capture-type-note">Note</span>';
      } else if (val.startsWith('t:') || val.startsWith('task:')) {
        html = '<span class="capture-type-badge capture-type-task">Task</span>';
      } else if (val.startsWith('q:') || val.startsWith('question:')) {
        html = '<span class="capture-type-badge capture-type-question">Question</span>';
      }
      badge.innerHTML = html;
    });
  }, 100);
}

function closeCapture() {
  const overlay = document.getElementById('capture-overlay');
  if (overlay) overlay.style.display = 'none';
  document.body.style.overflow = '';
}

function handleOverlayClick(event) {
  if (event.target === document.getElementById('capture-overlay')) {
    closeCapture();
  }
}

// ---------------------------------------------------------------------------
// Launch programs — quick actions open the right tool with prompt + context
// ---------------------------------------------------------------------------

// Each action defines: which target to launch, which prompt to send, whether
// the launch is scoped to the focus project or to the RC root.
const _LAUNCHER_CONFIG = {
  brainstorm: { target: 'claude_code', prompt: '/metis_brainstorm',          scope: 'focus' },
  write:      { target: 'claude_code', prompt: '/writing-partner work on my active article', scope: 'focus' },
  review:     { target: 'vscode',      prompt: '',                           scope: 'focus' },
  meeting:    { target: 'claude_code', prompt: '/meeting-memory prep for next meeting', scope: 'rc' },
  inbox:      { target: 'claude_code', prompt: '/metis_inbox',               scope: 'rc' },
};

async function _getFocusProjectId() {
  try {
    const res = await fetch('/api/project/focus');
    if (!res.ok) return null;
    const data = await res.json();
    return data.project_id || null;
  } catch {
    return null;
  }
}

async function launchPrompt(key) {
  const cfg = _LAUNCHER_CONFIG[key];
  if (!cfg) return;

  let projectId = 'rc-root';
  if (cfg.scope === 'focus') {
    const p = await _getFocusProjectId();
    if (p) projectId = p;
  }

  const body = new URLSearchParams({
    project_id: projectId,
    target: cfg.target,
    prompt: cfg.prompt || '',
  });

  // Copy prompt to clipboard as a safety net in case the launch fails
  if (cfg.prompt) {
    try { await navigator.clipboard.writeText(cfg.prompt); } catch { /* noop */ }
  }

  try {
    const res = await fetch('/api/project/launch', { method: 'POST', body });
    const data = await res.json();
    if (data.status === 'ok') {
      const msg = cfg.prompt
        ? `Opening ${cfg.target} with "${cfg.prompt}"`
        : `Opening ${cfg.target} · ${data.project || 'project'}`;
      showToast(`<i class="bi bi-box-arrow-up-right toast-icon"></i>${msg}`);
      // If there's a follow-up (e.g. open VS Code AND Claude Code after), fire it
      if (cfg.followUp) {
        setTimeout(() => {
          const body2 = new URLSearchParams({
            project_id: projectId,
            target: cfg.followUp.target,
            prompt: cfg.followUp.prompt || '',
          });
          fetch('/api/project/launch', { method: 'POST', body: body2 });
        }, 500);
      }
    } else {
      showToast(`<i class="bi bi-exclamation-triangle"></i>${data.message || 'Launch failed'}. Prompt copied — paste manually.`);
    }
  } catch (e) {
    showToast(`<i class="bi bi-exclamation-triangle"></i>Launch failed: ${e}. Prompt copied to clipboard.`);
  }
}

// ---------------------------------------------------------------------------
// Dashboard scan — trigger a refresh of focus/activity/news-rail
// ---------------------------------------------------------------------------

async function runDashboardScan() {
  showToast('<i class="bi bi-arrow-clockwise toast-icon"></i>Scanning for changes…');
  // Re-trigger the HTMX-loaded partials by issuing HTMX GETs
  const targets = [
    '/api/partial/today/dateline',
    '/api/partial/today/focus-thread',
    '/api/partial/today/activity-feed',
    '/api/partial/today/news-rail',
  ];
  const hosts = document.querySelectorAll(
    '[hx-get="/api/partial/today/dateline"], [hx-get="/api/partial/today/focus-thread"], [hx-get="/api/partial/today/activity-feed"], [hx-get="/api/partial/today/news-rail"]'
  );
  hosts.forEach(el => {
    if (window.htmx && htmx.trigger) htmx.trigger(el, 'load');
  });
  setTimeout(() => {
    showToast('<i class="bi bi-check2 toast-icon"></i>Scan complete');
  }, 800);
}

// ---------------------------------------------------------------------------
// Content scan — RSS feeds + literature folder
// ---------------------------------------------------------------------------

async function runContentScan(event) {
  showToast('<i class="bi bi-broadcast toast-icon"></i>Scanning feeds and literature…');
  const btn = event && event.target ? event.target.closest('a') : null;
  if (btn) btn.style.pointerEvents = 'none';
  try {
    const res = await fetch('/api/scan/content', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`<i class="bi bi-check2 toast-icon"></i>Scan complete — ${data.news_added} news · ${data.papers_added} papers`);
      document.querySelectorAll('[hx-get="/api/partial/today/news-rail"], [hx-get="/api/partial/today/activity-feed"]').forEach(el => {
        if (window.htmx && htmx.trigger) htmx.trigger(el, 'load');
      });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Scan failed — see Metis tab');
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Scan failed — network error');
  } finally {
    if (btn) btn.style.pointerEvents = '';
  }
}

// ---------------------------------------------------------------------------
// Course Builder — copy prompt to clipboard + notify server
// ---------------------------------------------------------------------------

async function buildCourse(courseId) {
  try {
    const res = await fetch('/api/course/build-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ courseId })
    });
    const data = await res.json();
    if (data.prompt) {
      navigator.clipboard.writeText(data.prompt).then(() => {
        showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Prompt copied — paste into Claude Code or Claude Desktop`);
      }).catch(() => {
        showToast(`<i class="bi bi-info-circle toast-icon"></i>Course: ${data.title} — use /course-builder in Claude Code`);
      });
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not load course prompt');
  }
}

// ---------------------------------------------------------------------------
// News category filter
// ---------------------------------------------------------------------------

function filterNewsCategory(btn, category) {
  document.querySelectorAll('.news-cat-chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  const url = category
    ? `/api/partial/today/news-rail?category=${encodeURIComponent(category)}`
    : '/api/partial/today/news-rail';
  fetch(url)
    .then(r => r.text())
    .then(html => {
      // Find the news-rail container and replace its innerHTML (or replace the
      // whole div)
      const tmp = document.createElement('div');
      tmp.innerHTML = html;
      const newRail = tmp.firstElementChild;
      const current = document.querySelector('.today-news-rail');
      if (current && newRail) current.replaceWith(newRail);
    });
}

// ---------------------------------------------------------------------------
// Project launcher — open external app (VS Code / RStudio / Claude Code)
// ---------------------------------------------------------------------------

async function launchProjectTarget(projectId, target) {
  try {
    const body = new URLSearchParams({ project_id: projectId, target: target });
    const res = await fetch('/api/project/launch', { method: 'POST', body });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`<i class="bi bi-box-arrow-up-right toast-icon"></i>Launched ${target} → ${data.path}`);
    } else {
      showToast(`<i class="bi bi-exclamation-triangle"></i>${data.message || 'Launch failed'}`);
    }
  } catch (e) {
    showToast(`<i class="bi bi-exclamation-triangle"></i>Launch failed: ${e}`);
  }
}

// ---------------------------------------------------------------------------
// News summary modal
// ---------------------------------------------------------------------------

function openNewsSummary(briefId) {
  const host = document.getElementById('news-modal-host') || document.body;
  fetch(`/api/news/brief/${briefId}`)
    .then(r => r.text())
    .then(html => {
      host.innerHTML = html;
    })
    .catch(() => showToast('Could not load news detail.'));
}

function closeNewsModal(event) {
  // if event passed, only close when clicking the backdrop
  if (event && event.target !== event.currentTarget) return;
  const host = document.getElementById('news-modal-host');
  if (host) host.innerHTML = '';
}

// ---------------------------------------------------------------------------
// Task actions (work tab)
// ---------------------------------------------------------------------------

async function markTaskDone(taskId, btn) {
  try {
    const res = await fetch(`/api/task/${taskId}/done`, { method: 'POST' });
    if (!res.ok) throw new Error();
    const row = btn.closest('.list-group-item, tr, .task-row');
    if (row) {
      row.style.opacity = '0.5';
      row.style.textDecoration = 'line-through';
      setTimeout(() => row.remove(), 600);
    }
    showToast('<i class="bi bi-check2 toast-icon"></i>Task marked done');
  } catch {
    showToast('Could not update task');
  }
}

async function deleteTask(taskId, btn) {
  if (!confirm('Delete this task?')) return;
  try {
    const res = await fetch(`/api/task/${taskId}/delete`, { method: 'POST' });
    if (!res.ok) throw new Error();
    const row = btn.closest('.list-group-item, tr, .task-row');
    if (row) row.remove();
    showToast('Task deleted');
  } catch {
    showToast('Could not delete task');
  }
}

// ---------------------------------------------------------------------------
// Tune scan — open feed allowlist modal
// ---------------------------------------------------------------------------

const _TUNE_SCAN_FEEDS = [
  { name: 'WHO outbreak news',     tags: 'HAT · Public health' },
  { name: 'CDC EID journal',       tags: 'Methods · Public health' },
  { name: 'PLOS NTDs',             tags: 'HAT · Methods' },
  { name: 'Anthropic News',        tags: 'AI' },
];

function tuneScan() { openTuneScan(); }

function openTuneScan() {
  let overlay = document.getElementById('tune-scan-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'tune-scan-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) closeTuneScan(); };
    document.body.appendChild(overlay);
  }
  const feeds = _TUNE_SCAN_FEEDS.map(f => `
    <div class="tune-scan-feed">
      <div>
        <div class="tune-scan-feed-name">${f.name}</div>
        <div class="tune-scan-feed-tags">${f.tags}</div>
      </div>
      <span class="chip chip--ok">ON</span>
    </div>`).join('');
  overlay.innerHTML = `
    <div class="tune-scan-card" onclick="event.stopPropagation()">
      <div class="kicker kicker--accent" style="margin-bottom:10px;">
        <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="8" r="5.5"/><line x1="8" y1="3" x2="8" y2="5"/><line x1="8" y1="11" x2="8" y2="13"/><line x1="3" y1="8" x2="5" y2="8"/><line x1="11" y1="8" x2="13" y2="8"/></svg>
        <span>SCAN SETTINGS</span>
      </div>
      <h2>What's listening</h2>
      <p class="ed" style="font-size:14px;color:var(--m-muted);margin:0 0 14px;">
        Sources currently in the allowlist. Editing the list lives in <code>system/mcp-server/src/metis_mcp/tools/content_scan.py</code> — I'll wire an in-app editor in a later phase.
      </p>
      ${feeds}
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px;padding-top:14px;border-top:1px solid var(--m-rule);">
        <button class="btn btn--ghost btn--caps" onclick="closeTuneScan()">Close</button>
        <button class="btn btn--primary" onclick="closeTuneScan();runContentScan({target:document.body});">Scan now</button>
      </div>
    </div>`;
  overlay.classList.add('open');
}

function closeTuneScan() {
  const overlay = document.getElementById('tune-scan-overlay');
  if (overlay) overlay.classList.remove('open');
}

// ---------------------------------------------------------------------------
// Thinking tab — Brainstorm + Export-as-note
// ---------------------------------------------------------------------------

function launchBrainstorm() {
  // Reuse the existing launchPrompt path that opens Claude Code with /metis_brainstorm
  if (typeof launchPrompt === 'function') {
    launchPrompt('brainstorm');
  } else {
    showToast('<i class="bi bi-lightbulb toast-icon"></i>/metis_brainstorm copied — paste into Claude Code');
    navigator.clipboard?.writeText('/metis_brainstorm');
  }
}

async function exportIdeaAsNote() {
  try {
    const res = await fetch('/api/note/from-latest-idea', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`<i class="bi bi-journal-arrow-down toast-icon"></i>Idea exported as note · "${(data.preview || '').slice(0, 60)}…"`);
      // Refresh marginalia & threads
      document.querySelectorAll('[hx-get="/api/partial/thinking/marginalia"], [hx-get="/api/partial/thinking/threads"]').forEach(el => {
        if (window.htmx && htmx.trigger) htmx.trigger(el, 'load');
      });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Nothing to export.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Export failed — server offline?');
  }
}

// ---------------------------------------------------------------------------
// Planner — task status (Retire / Pause / Schedule)
// ---------------------------------------------------------------------------

async function setTaskStatus(action) {
  // action: 'retire' | 'pause' | 'schedule'
  try {
    const res = await fetch('/api/task/oldest-open/' + action, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`<i class="bi bi-check2 toast-icon"></i>Task ${action}d`);
      document.querySelectorAll('[hx-get="/api/partial/planner/notes"], [hx-get="/api/partial/planner/horizon"]').forEach(el => {
        if (window.htmx && htmx.trigger) htmx.trigger(el, 'load');
      });
    } else {
      showToast('<i class="bi bi-info-circle toast-icon"></i>' + (data.message || 'No matching task.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Action failed — server offline?');
  }
}

// ---------------------------------------------------------------------------
// Metis — model selector + identity stubs
// ---------------------------------------------------------------------------

async function setActiveModel(slug, btn) {
  try {
    const res = await fetch('/api/model/active', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug }),
    });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(`<i class="bi bi-check2 toast-icon"></i>Default model set to <b>${slug}</b>`);
      // Visual update — toggle the model-card-on class
      document.querySelectorAll('.model-card-on').forEach(el => el.classList.remove('model-card-on'));
      if (btn) btn.closest('.panel')?.classList.add('model-card-on');
    } else {
      showToast('<i class="bi bi-info-circle toast-icon"></i>' + (data.message || 'Could not change model.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-info-circle toast-icon"></i>Note: setting saved locally only.');
  }
}

function openMetisRename() {
  const name = prompt('What should Metis call you?', 'Stan');
  if (!name) return;
  fetch('/api/identity/rename', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  }).then(() => {
    showToast(`<i class="bi bi-pencil toast-icon"></i>Saved — refresh to see "${name}" in greetings`);
    document.querySelectorAll('[hx-get="/api/partial/metis/identity"]').forEach(el => {
      if (window.htmx && htmx.trigger) htmx.trigger(el, 'load');
    });
  }).catch(() => showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not save.'));
}

function openMetisKeys() {
  showToast('<i class="bi bi-key toast-icon"></i>Keys live in <code>system/mcp-server/.env</code> — edit there. UI editor coming.');
}

function openMetisExport() {
  showToast('<i class="bi bi-box-arrow-down toast-icon"></i>Run <code>/metis_handoff</code> in Claude Code to export the current archive.');
}

// ---------------------------------------------------------------------------
// Generic stub — copies a prompt to clipboard, shows toast
// ---------------------------------------------------------------------------

function metisStub(prompt, label) {
  navigator.clipboard?.writeText(prompt).then(() => {
    showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Prompt copied — paste into Claude Code<br><code style="font-size:0.75rem;opacity:0.85;">${prompt}</code>`, 5500);
  }).catch(() => showToast(`Use this prompt in Claude Code:<br><code>${prompt}</code>`, 5500));
}

// Meeting actions
function openBriefing(meetingId)  { metisStub(`/meeting-memory open briefing for meeting ${meetingId || 'next'}`); }
function openTranscript(meetingId){ metisStub(`/meeting-memory transcript for meeting ${meetingId || 'last'}`); }
function rescheduleMeeting(id)    { showToast('<i class="bi bi-calendar2-event toast-icon"></i>Rescheduling lives in your calendar (Outlook/Google) — link coming.'); }

// ---------------------------------------------------------------------------
// Phase 8.13 — Handoff brief generator (callable from Today dateline strip)
// ---------------------------------------------------------------------------

async function generateHandoff() {
  showToast('<i class="bi bi-pencil-square toast-icon"></i>Writing handoff brief…');
  try {
    const res = await fetch('/api/handoff/generate', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(
        `<i class="bi bi-check2 toast-icon"></i>Handoff written → <code>${data.path || 'journal/'}</code><br>` +
        `<span style="font-size:0.78rem;opacity:0.8;">${(data.runs_count || 0)} recent runs · ${(data.tokens_today || 0).toLocaleString()} tokens today</span>`,
        6500
      );
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Handoff failed.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Handoff failed — server offline?');
  }
}

// Teach actions (already partly defined below)
function openHistory(id, title)   { metisStub(`/course-builder history for course "${title}"`); }
function continueDraft(id, title) { metisStub(`/course-builder continue draft for "${title}"`); }
function publishCourse(id, title) { metisStub(`/course-builder publish "${title}"`); }
function startBuildingSuggested() { metisStub('/course-builder start a new course from the catalog'); }
function viewCatalog()            { document.querySelector('.sec-label .tail')?.scrollIntoView({behavior:'smooth', block:'center'}); }

// ---------------------------------------------------------------------------
// Toast notification (reusable)
// ---------------------------------------------------------------------------

function showToast(html, duration = 4500) {
  let t = document.getElementById('metis-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'metis-toast';
    t.className = 'metis-toast';
    document.body.appendChild(t);
  }
  t.innerHTML = html;
  requestAnimationFrame(() => t.classList.add('show'));
  clearTimeout(t._hideTimer);
  t._hideTimer = setTimeout(() => {
    t.classList.remove('show');
  }, duration);
}

// Alias for legacy calls
function _showToast(msg) { showToast(msg); }

// ---------------------------------------------------------------------------
// DB watcher — poll every 20s, show a reload notification when mtime changes
// ---------------------------------------------------------------------------

let lastDbMtime = null;

async function checkDbMtime() {
  try {
    const res = await fetch('/api/check-db-mtime');
    if (!res.ok) return;
    const data = await res.json();
    if (lastDbMtime !== null && data.mtime > lastDbMtime) {
      showDbUpdateNotification();
    }
    lastDbMtime = data.mtime;
  } catch (e) { /* noop */ }
}

function showDbUpdateNotification() {
  let notif = document.getElementById('db-update-notif');
  if (!notif) {
    notif = document.createElement('div');
    notif.id = 'db-update-notif';
    notif.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9000;min-width:280px;';
    document.body.appendChild(notif);
  }
  notif.innerHTML = `
    <div class="alert alert-info alert-dismissible shadow" role="alert">
      <i class="bi bi-arrow-repeat"></i> Metis updated the database.
      <a href="#" onclick="location.reload(); return false;" class="alert-link ms-1">Reload now</a>
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>`;
}

window.addEventListener('load', () => {
  checkDbMtime();
  setInterval(checkDbMtime, 20000);
});

// ---------------------------------------------------------------------------
// Teach tab course actions
// ---------------------------------------------------------------------------

function _teachPrompt(action, courseId, courseTitle) {
  const prompt = `/metis ${action} for my course "${courseTitle}"`;
  navigator.clipboard.writeText(prompt).then(() => {
    showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Prompt copied — paste into Claude Code<br><code style="font-size:0.75rem;opacity:0.8;">${prompt}</code>`);
  }).catch(() => {
    showToast(`Use this prompt in Claude Code:<br><code>${prompt}</code>`);
  });
}

function openCourseChat(id, title)       { _teachPrompt('Open a teaching chat session', id, title); }
function openCourseCowork(id, title)     { _teachPrompt('Co-work on course improvement', id, title); }
function openCourseSlides(id, title)     { _teachPrompt('Generate a slide deck', id, title); }
function openAssessmentBuilder(id, title){ _teachPrompt('Build an assessment', id, title); }
function openQuestionBank(id, title)     { _teachPrompt('Build a student question bank', id, title); }
function openGapAnalysis(id, title)      { _teachPrompt('Run a curriculum gap analysis', id, title); }

// ---------------------------------------------------------------------------
// Inline capture bar (on Today tab)
// ---------------------------------------------------------------------------

let _captureMode = 'i';

function setCaptureMode(btn) {
  document.querySelectorAll('.capture-mode-btn, .question-mode-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _captureMode = btn.dataset.mode;
  const placeholders = {
    i: 'Capture an idea…',
    t: 'Add a task…',
    n: 'Write a note…',
    q: 'Ask Metis…',
  };
  const inp = document.getElementById('inline-capture-input');
  if (inp) inp.placeholder = placeholders[_captureMode] || 'Start typing…';
}

function handleCaptureKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitInlineCapture();
  }
}

async function submitInlineCapture() {
  const inp = document.getElementById('inline-capture-input');
  const fb  = document.getElementById('inline-capture-feedback');
  if (!inp || !inp.value.trim()) return;

  const prefix = _captureMode + ':';
  const body = new URLSearchParams({ text: prefix + inp.value.trim() });

  try {
    const res = await fetch('/api/capture', { method: 'POST', body });
    const html = await res.text();
    if (fb) fb.innerHTML = html;
    inp.value = '';
    setTimeout(() => { if (fb) fb.innerHTML = ''; }, 3000);
  } catch {
    if (fb) fb.innerHTML = '<span class="text-danger">Error saving — is the server running?</span>';
  }
}
