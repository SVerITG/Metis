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
// Scheduler — trigger a job manually from the automation panel
// ---------------------------------------------------------------------------

async function triggerJob(jobId) {
  showToast('<i class="bi bi-broadcast toast-icon"></i>Running ' + jobId + '...');
  try {
    const res = await fetch('/api/scheduler/jobs/' + jobId + '/run', { method: 'POST' });
    const data = await res.json();
    showToast('<i class="bi bi-check2 toast-icon"></i>' + (data.message || 'Job triggered'));
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Trigger failed');
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
      await navigator.clipboard.writeText(data.prompt).catch(() => {});
      await _launchClaudeDesktop();
      showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Claude Desktop opening — prompt copied for <strong>${data.title || courseId}</strong>`);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not load course prompt');
  }
}

// ---------------------------------------------------------------------------
// Course Ideas — build via Claude Desktop
// ---------------------------------------------------------------------------

async function _fetchBuildIdeaPrompt(slug, title, adaptive, topicHint, researchQuestion) {
  const res = await fetch('/api/course/build-idea', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slug, title, adaptive: !!adaptive, topicHint: topicHint || '', researchQuestion: researchQuestion || '' })
  });
  return await res.json();
}

async function _launchClaudeDesktop() {
  await fetch('/api/launch/claude-desktop', { method: 'POST' }).catch(() => {});
}

async function buildCourseIdea(slug, title) {
  try {
    const data = await _fetchBuildIdeaPrompt(slug, title, false, '');
    if (data.prompt) {
      await navigator.clipboard.writeText(data.prompt).catch(() => {});
      await _launchClaudeDesktop();
      showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Claude Desktop opening — paste prompt to build <strong>${data.title}</strong>`);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not prepare course prompt');
  }
}

async function buildAdaptiveCourse(topicSlug, topicTitle) {
  try {
    const data = await _fetchBuildIdeaPrompt('statistics-adaptive', topicTitle, true, topicTitle, '');
    if (data.prompt) {
      await navigator.clipboard.writeText(data.prompt).catch(() => {});
      await _launchClaudeDesktop();
      showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Claude Desktop opening — paste prompt to start adaptive course on <strong>${topicTitle}</strong>`);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not prepare adaptive course prompt');
  }
}

function toggleQuestionPanel(btn, slug, title) {
  const card = btn.closest('.course-card');
  if (!card) return;
  const panel = card.querySelector('.course-question-panel');
  if (!panel) return;
  const visible = panel.style.display !== 'none';
  panel.style.display = visible ? 'none' : 'block';
  if (!visible) panel.querySelector('textarea')?.focus();
}

async function launchWithQuestion(btn, slug, title) {
  const panel = btn.closest('.course-question-panel');
  const question = panel?.querySelector('.question-input')?.value?.trim() || '';
  if (!question) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Please enter a research question first');
    return;
  }
  try {
    const data = await _fetchBuildIdeaPrompt(slug, title, true, title, question);
    if (data.prompt) {
      await navigator.clipboard.writeText(data.prompt).catch(() => {});
      await _launchClaudeDesktop();
      showToast(`<i class="bi bi-clipboard-check toast-icon"></i>Claude Desktop opening — prompt includes your research question`);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not prepare course prompt');
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
// Project detail overlay — full project panel with all tasks + history
// ---------------------------------------------------------------------------

function openProjectDetail(projectId) {
  const existing = document.getElementById('proj-detail-overlay');
  if (existing) existing.remove();
  htmx.ajax('GET', '/api/partial/work/project-detail/' + projectId, {
    target: document.body,
    swap: 'beforeend',
  });
}

function closeProjectDetail() {
  const el = document.getElementById('proj-detail-overlay');
  if (el) el.remove();
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeProjectDetail();
});

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
    } else if (data.status === 'starting') {
      showToast(`<i class="bi bi-hourglass-split toast-icon"></i>${data.message || 'Starting…'}`);
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

async function markProjectTaskDone(taskId, projectId) {
  try {
    const res = await fetch(`/api/task/${taskId}/done`, { method: 'POST' });
    if (!res.ok) throw new Error();
    await _refreshProjectTasks(projectId);
    showToast('Task done ✓');
  } catch {
    showToast('Could not update task');
  }
}

async function submitQuickTask(projectId) {
  const titleEl = document.getElementById(`task-title-${projectId}`);
  const catEl   = document.getElementById(`task-cat-${projectId}`);
  const title   = titleEl ? titleEl.value.trim() : '';
  if (!title) { if (titleEl) titleEl.focus(); return; }
  const category = catEl ? catEl.value : 'general';
  try {
    const res = await fetch('/api/task/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, title, category }),
    });
    if (!res.ok) throw new Error();
    const html = await res.text();
    const target = document.getElementById(`proj-tasks-${projectId}`);
    if (target) target.innerHTML = html;
    if (titleEl) titleEl.value = '';
    document.getElementById(`task-add-${projectId}`).style.display = 'none';
    showToast('Task added');
  } catch {
    showToast('Could not add task');
  }
}

async function _refreshProjectTasks(projectId) {
  const res = await fetch(`/api/partial/work/project-tasks/${projectId}`);
  if (!res.ok) return;
  const html = await res.text();
  const target = document.getElementById(`proj-tasks-${projectId}`);
  if (target) target.innerHTML = html;
}

async function miniTaskStar(taskId, projectId, btn) {
  const res = await fetch(`/api/task/${taskId}/star`, { method: 'POST' });
  const data = await res.json();
  const starColor = data.starred ? 'var(--m-ochre-deep,#b36a1d)' : 'var(--m-muted)';
  if (btn) { btn.style.color = starColor; btn.style.opacity = data.starred ? '1' : '0.4'; btn.title = data.starred ? 'Unstar' : 'Star (appears in Today)'; }
  showToast(data.starred ? 'Task starred — will appear in Today' : 'Task unstarred');
}

async function miniTaskDelete(taskId, projectId) {
  if (!confirm('Delete this task?')) return;
  await fetch(`/api/task/${taskId}/delete`, { method: 'POST' });
  await _refreshProjectTasks(projectId);
}

async function toggleProjectNotes(projectId) {
  const panel = document.getElementById(`proj-notes-${projectId}`);
  if (!panel) return;
  if (panel.style.display !== 'none') {
    panel.style.display = 'none';
    return;
  }
  if (!panel.dataset.loaded) {
    const res = await fetch(`/api/project/${projectId}/notes`);
    panel.innerHTML = await res.text();
    panel.dataset.loaded = '1';
  }
  panel.style.display = '';
}

async function saveProjectNotes(projectId) {
  const area = document.getElementById(`notes-area-${projectId}`);
  if (!area) return;
  try {
    await fetch(`/api/project/${projectId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: area.value }),
    });
    const indicator = document.getElementById(`notes-saved-${projectId}`);
    if (indicator) { indicator.textContent = 'SAVED'; setTimeout(() => indicator.textContent = '', 2000); }
  } catch {
    showToast('Could not save notes');
  }
}

// ---------------------------------------------------------------------------
// Add Project modal
// ---------------------------------------------------------------------------

function openAddProjectModal() {
  const overlay = document.getElementById('add-project-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';
  npGoStep1();
  setTimeout(() => document.getElementById('np-path')?.focus(), 80);
}

function closeAddProjectModal() {
  const overlay = document.getElementById('add-project-overlay');
  if (overlay) overlay.style.display = 'none';
}

function npGoStep1() {
  document.getElementById('np-step-1').style.display = '';
  document.getElementById('np-step-2').style.display = 'none';
  document.getElementById('np-step-title').textContent = 'Add Project — Where is it?';
  document.getElementById('np-step-dot-1').style.background = 'var(--m-accent)';
  document.getElementById('np-step-dot-2').style.background = 'var(--m-rule)';
}

function npGoStep2() {
  const title = (document.getElementById('np-title')?.value || '').trim();
  if (!title) { document.getElementById('np-title').focus(); return; }
  document.getElementById('np-step-1').style.display = 'none';
  document.getElementById('np-step-2').style.display = '';
  document.getElementById('np-step-title').textContent = 'Add Project — Tell me more';
  document.getElementById('np-step-dot-1').style.background = 'var(--m-rule)';
  document.getElementById('np-step-dot-2').style.background = 'var(--m-accent)';
  setTimeout(() => document.getElementById('np-desc')?.focus(), 80);
}

function npAutoTitle() {
  const path = (document.getElementById('np-path')?.value || '').trim();
  if (!path) return;
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  const last = parts[parts.length - 1] || '';
  const titleEl = document.getElementById('np-title');
  if (titleEl && !titleEl.value) {
    titleEl.value = last.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}

async function submitAddProject() {
  const title = (document.getElementById('np-title')?.value || '').trim();
  if (!title) { npGoStep1(); document.getElementById('np-title').focus(); return; }
  const launcher = document.querySelector('input[name="np-launcher"]:checked')?.value || 'vscode';
  const typeMap = {
    vscode:   ['vscode', 'claude_code', 'claude_desktop', 'explorer'],
    rstudio:  ['rstudio', 'claude_code', 'claude_desktop', 'explorer'],
    explorer: ['explorer', 'claude_code', 'claude_desktop'],
    none:     ['claude_code', 'claude_desktop'],
  };
  const payload = {
    title,
    description:   document.getElementById('np-desc')?.value || '',
    external_path: document.getElementById('np-path')?.value || '',
    github_url:    document.getElementById('np-github')?.value || '',
    launcher_type: launcher,
    launchers:     typeMap[launcher] || typeMap.vscode,
  };
  try {
    const res = await fetch('/api/project/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.status !== 'ok') throw new Error(data.message);

    // Seed tasks from textarea
    const taskLines = (document.getElementById('np-tasks')?.value || '')
      .split('\n').map(l => l.trim()).filter(Boolean);
    for (const line of taskLines) {
      await fetch('/api/task/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: line, project_id: data.project_id }),
      }).catch(() => {});
    }

    closeAddProjectModal();
    htmx.ajax('GET', '/api/partial/work/projects', { target: '#projects-zone', swap: 'innerHTML' });
    showToast(`Project "${data.title}" created`);
    ['np-title','np-desc','np-path','np-tasks','np-github'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
    });
  } catch(e) {
    showToast('Could not create project: ' + (e.message || 'unknown error'));
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
  const name = prompt('What should Metis call you?', '');
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
// Identity edit modal — name, role, interests, news topics
// ---------------------------------------------------------------------------

function _readIdentityFromCard() {
  const card = document.getElementById('metis-identity-card');
  const data = { name: '', role: '', interests: [], news_topics: [] };
  if (!card) return data;
  const nm = card.querySelector('.metis-id-name');
  if (nm) data.name = nm.textContent.trim();
  const sub = card.querySelector('.metis-id-sub');
  if (sub) data.role = sub.textContent.trim();
  const blocks = card.querySelectorAll('.metis-id-block');
  if (blocks.length >= 1) {
    data.interests = Array.from(blocks[0].querySelectorAll('.metis-tag:not(.metis-tag--empty)'))
      .map(function (t) { return t.textContent.trim(); });
  }
  if (blocks.length >= 2) {
    data.news_topics = Array.from(blocks[1].querySelectorAll('.metis-tag:not(.metis-tag--empty)'))
      .map(function (t) { return t.textContent.trim(); });
  }
  return data;
}

function openMetisIdentityEdit() {
  const ov = document.getElementById('metis-identity-overlay');
  if (!ov) return;
  const cur = _readIdentityFromCard();
  const f = function (id) { return document.getElementById(id); };
  if (f('me-name'))      f('me-name').value = cur.name || '';
  if (f('me-role'))      f('me-role').value = cur.role || '';
  if (f('me-interests')) f('me-interests').value = (cur.interests || []).join(', ');
  if (f('me-news'))      f('me-news').value = (cur.news_topics || []).join(', ');
  ov.dataset.open = 'true';
  setTimeout(function () { f('me-name')?.focus(); }, 60);
}

function closeMetisIdentityEdit() {
  const ov = document.getElementById('metis-identity-overlay');
  if (ov) ov.dataset.open = 'false';
}

async function saveMetisIdentity() {
  const f = function (id) { return document.getElementById(id); };
  const payload = {
    name:        (f('me-name')?.value || '').trim(),
    role:        (f('me-role')?.value || '').trim(),
    interests:   (f('me-interests')?.value || '').trim(),
    news_topics: (f('me-news')?.value || '').trim(),
  };
  try {
    const res = await fetch('/api/identity/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast('<i class="bi bi-check2 toast-icon"></i>Identity saved.');
      closeMetisIdentityEdit();
      // Reload the identity card
      const card = document.getElementById('metis-identity-card')?.parentElement;
      if (card && window.htmx) htmx.ajax('GET', '/api/partial/metis/identity', { target: card, swap: 'innerHTML' });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Could not save.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not save identity.');
  }
}

// Close on Escape
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    const ov = document.getElementById('metis-identity-overlay');
    if (ov && ov.dataset.open === 'true') closeMetisIdentityEdit();
  }
});

// ---------------------------------------------------------------------------
// Memory filter chips + archive setting
// ---------------------------------------------------------------------------

function filterMemoryStream(type, btn) {
  // Toggle chip active state
  document.querySelectorAll('#mem-filter-strip .mem-filter').forEach(function (el) {
    el.dataset.active = (el === btn) ? 'true' : 'false';
  });
  // Update tail label
  const tail = document.getElementById('memory-stream-tail');
  if (tail) tail.textContent = (type === 'all') ? 'RECENT FIRST' : type.toUpperCase() + ' ONLY';
  // Reload the memory stream with the filter
  const target = document.getElementById('metis-memory-stream-body');
  if (target && window.htmx) {
    const url = '/api/partial/metis/memory-stream' + (type !== 'all' ? ('?type=' + encodeURIComponent(type)) : '');
    htmx.ajax('GET', url, { target: target, swap: 'innerHTML' });
  }
}

async function saveMemoryArchive(value) {
  try {
    const res = await fetch('/api/settings/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ archive_days: parseInt(value, 10) }),
    });
    const data = await res.json();
    if (data.status === 'ok') {
      const label = (parseInt(value, 10) === 0) ? 'never archive' : (value + ' days');
      showToast('<i class="bi bi-archive toast-icon"></i>Archive setting saved — ' + label + '.');
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Could not save.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Could not save archive setting.');
  }
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

// Schedule daily morning brief via Windows Task Scheduler (one-off setup).
async function scheduleMorningBrief() {
  const proceed = window.confirm(
    'Schedule a daily 7:00 AM scan?\n\n' +
    'This registers two Windows Task Scheduler entries:\n' +
    '  • Metis_NewsRadar — runs the news scan\n' +
    '  • Metis_LibrarianScan — runs the literature scan\n\n' +
    'You can change the time later via Task Scheduler. ' +
    'You can also run /schedule from Claude Code for more control.'
  );
  if (!proceed) return;
  showToast('<i class="bi bi-clock-history toast-icon"></i>Registering schedule…');
  try {
    const res = await fetch('/api/schedule/register-morning', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(
        '<i class="bi bi-check2 toast-icon"></i>' +
        (data.message || 'Morning brief scheduled. First run tomorrow at 7:00.'),
        6500
      );
    } else {
      showToast(
        '<i class="bi bi-exclamation-circle toast-icon"></i>' +
        (data.message || 'Could not register schedule. Try /schedule from Claude Code.'),
        7000
      );
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Schedule failed — server offline?');
  }
}

// Run the metis_doctor self-test and surface results.
async function runMetisDoctor() {
  showToast('<i class="bi bi-stethoscope toast-icon"></i>Running diagnostics…');
  try {
    const res = await fetch('/api/doctor');
    const data = await res.json();
    if (data.status !== 'ok' && data.status !== 'warn' && data.status !== 'fail') {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Doctor failed: ' + (data.message || 'unknown error'));
      return;
    }
    const lines = (data.checks || []).map(function (c) {
      const icon = c.ok ? '✓' : (c.severity === 'warn' ? '⚠' : '✗');
      return icon + ' ' + c.name + (c.detail ? ' — ' + c.detail : '');
    });
    const summary =
      'Metis Doctor — ' + (data.status || '?').toUpperCase() + '\n\n' +
      lines.join('\n') +
      '\n\n' + (data.summary || '');
    window.alert(summary);
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Doctor unreachable.');
  }
}

// ---------------------------------------------------------------------------
// Self-improvement loop (Phase 9b)
// ---------------------------------------------------------------------------

async function draftImprovement(slug) {
  if (!slug) return;
  showToast('<i class="bi bi-lightbulb toast-icon"></i>Drafting self-improvement notes for <code>' + slug + '</code>…');
  try {
    const res = await fetch('/api/improvement/draft/' + encodeURIComponent(slug), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days: 14 }),
    });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast('<i class="bi bi-check2 toast-icon"></i>Draft #' + data.proposal_id + ' queued for ' + slug + '. Review below.', 5500);
      htmx.trigger('#metis-improvement-body', 'refresh-improvement');
      const el = document.getElementById('metis-improvement-body');
      if (el) htmx.ajax('GET', '/api/partial/metis/improvement', { target: el, swap: 'innerHTML' });
    } else {
      showToast('<i class="bi bi-info-circle toast-icon"></i>' + (data.message || 'No reflexions yet.'), 5000);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Draft failed.');
  }
}

async function promoteProposal(pid) {
  if (!pid) return;
  try {
    const res = await fetch('/api/improvement/promote/' + pid, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast('<i class="bi bi-arrow-up-circle toast-icon"></i>Proposal #' + pid + ' promoted to pending.');
      const el = document.getElementById('metis-improvement-body');
      if (el) htmx.ajax('GET', '/api/partial/metis/improvement', { target: el, swap: 'innerHTML' });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Could not promote.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Promotion failed.');
  }
}

// Show the diff for a proposal in a modal-like prompt, then optionally apply.
async function previewProposal(pid) {
  if (!pid) return;
  try {
    const res = await fetch('/api/improvement/preview/' + pid);
    const data = await res.json();
    if (data.status !== 'ok') {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Could not load preview.'));
      return;
    }
    const summary =
      'Proposal #' + data.proposal_id + ' for "' + data.agent_slug + '"\n' +
      'Status: ' + data.proposal_status + '\n' +
      '+' + data.added_lines + ' / -' + data.removed_lines + ' lines\n\n' +
      (data.rationale ? 'Rationale:\n' + data.rationale + '\n\n' : '') +
      'Diff (truncated to 4000 chars):\n\n' +
      (data.diff || '(empty)').slice(0, 4000) + '\n\n' +
      'Apply this change to the agent\'s skill.md? (OK = apply, Cancel = keep as-is)';
    if (window.confirm(summary)) {
      applyProposal(pid);
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Preview failed.');
  }
}

// Apply: actually writes proposed_content to the agent's skill.md (with backup).
async function applyProposal(pid) {
  if (!pid) return;
  try {
    const res = await fetch('/api/improvement/apply/' + pid, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(
        '<i class="bi bi-check-circle toast-icon"></i>Applied to <code>' +
        data.agent_slug + '/skill.md</code>. Backup at <code>' +
        (data.backup_path || '').split('/').pop() + '</code>.',
        6000
      );
      const el = document.getElementById('metis-improvement-body');
      if (el) htmx.ajax('GET', '/api/partial/metis/improvement', { target: el, swap: 'innerHTML' });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Apply failed.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Apply failed.');
  }
}

async function rejectProposal(pid) {
  if (!pid) return;
  const note = window.prompt('Reason for rejecting #' + pid + '? (optional)') || '';
  try {
    const res = await fetch('/api/improvement/reject/' + pid, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast('<i class="bi bi-x-circle toast-icon"></i>Proposal #' + pid + ' rejected.');
      const el = document.getElementById('metis-improvement-body');
      if (el) htmx.ajax('GET', '/api/partial/metis/improvement', { target: el, swap: 'innerHTML' });
    } else {
      showToast('<i class="bi bi-exclamation-circle toast-icon"></i>' + (data.message || 'Could not reject.'));
    }
  } catch (e) {
    showToast('<i class="bi bi-exclamation-circle toast-icon"></i>Rejection failed.');
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
// Each button copies a ready-to-paste Claude Code prompt to the clipboard.
// ---------------------------------------------------------------------------

function _copyAndToast(prompt) {
  navigator.clipboard.writeText(prompt).then(() => {
    showToast(
      '<i class="bi bi-clipboard-check toast-icon"></i>Prompt copied — paste into Claude Code'
    );
  }).catch(() => {
    showToast('Use this prompt in Claude Code:<br><code>' + prompt.slice(0, 80) + '…</code>');
  });
}

function openCourseSlides(id, title) {
  _copyAndToast(
    `/presentation-maker\nCreate a lecture slide deck for my course: "${title}"\n\n` +
    `Please ask me which module or lecture topic to create slides for, then produce a ` +
    `complete deck with: title slide, learning objectives, content slides with speaker notes, ` +
    `activity/discussion prompts, and a summary slide.`
  );
}

function openTeachingBrief(id, title) {
  _copyAndToast(
    `/presentation-maker\nTeaching brief for a lecture in "${title}".\n\n` +
    `Produce a one-page lecture guide for me as the instructor:\n` +
    `- Learning objectives (3-5, Bloom taxonomy level)\n` +
    `- Key concepts with 2-sentence explanation each\n` +
    `- Suggested in-class activity or discussion question\n` +
    `- Common student misconceptions to address\n` +
    `- 3 exam-ready assessment questions with answer key`
  );
}

function openAssessmentBuilder(id, title) {
  _copyAndToast(
    `/course-builder\nBuild an exam or assessment for my course "${title}".\n\n` +
    `Ask me: difficulty level, question types (MCQ/short answer/essay), ` +
    `Bloom taxonomy target, number of questions, and which topic to focus on. ` +
    `Then generate the full assessment with a marking guide.`
  );
}

function openQuestionBank(id, title) {
  _copyAndToast(
    `/course-builder\nBuild a student question bank for "${title}".\n\n` +
    `Generate 20 practice questions organised by:\n` +
    `- Difficulty: easy (recall) / medium (application) / hard (analysis)\n` +
    `- Include model answers and common errors to watch for.\n` +
    `Ask me which topic area to focus on first.`
  );
}

function openGapAnalysis(id, title) {
  _copyAndToast(
    `/librarian\nRun a curriculum gap analysis for my course "${title}".\n\n` +
    `Review the current learning objectives and identify:\n` +
    `1. Missing foundational concepts students likely need\n` +
    `2. Recent high-impact literature (last 3 years) not yet covered\n` +
    `3. Competency gaps vs current field or professional standards\n` +
    `Suggest specific additions with justification and estimated teaching time.`
  );
}

function openCourseChat(id, title) {
  _copyAndToast(
    `/metis\nI want to work on my teaching for the course "${title}". ` +
    `Help me with: improving slide content, discussing pedagogy, updating material ` +
    `for a specific lecture, or thinking through how to explain a difficult concept.`
  );
}

// ---------------------------------------------------------------------------
// Spaced repetition — mark card reviewed (SM-2)
// ---------------------------------------------------------------------------

function srReview(srId, quality, btn) {
  btn.disabled = true;
  fetch('/api/learning/review/' + srId, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quality: quality })
  }).then(function (r) {
    if (r.ok) return r.text();
    throw new Error('review failed');
  }).then(function (html) {
    // Replace the whole due-today partial
    const container = document.getElementById('sr-due-list');
    if (container) {
      const parent = container.closest('[id]') || container.parentElement;
      parent.outerHTML = html;
    }
    showToast('<i class="bi bi-check-circle toast-icon"></i>Card reviewed — next review scheduled.');
  }).catch(function () {
    btn.disabled = false;
    showToast('Could not save review. Try again.');
  });
}

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

// ---------------------------------------------------------------------------
// Project cards — drag-to-reorder (live snap) + collapse/expand
// ---------------------------------------------------------------------------

let _dragSrc      = null;
let _dragLastOver = null;   // tracks last card entered, prevents repeated DOM moves

function _saveProjectOrder() {
  const cards = document.querySelectorAll('#project-grid .project-card[data-project-id]');
  const order = Array.from(cards).map(c => c.dataset.projectId);
  fetch('/api/project/reorder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order }),
  });
}

function _restoreProjectStates() {
  document.querySelectorAll('#project-grid .project-card[data-project-id]').forEach(card => {
    const pid  = card.dataset.projectId;
    const body = card.querySelector('.proj-body');
    const btn  = card.querySelector('.proj-collapse-btn');
    if (!body || !btn) return;
    if (localStorage.getItem(`proj-collapsed-${pid}`) === '1') {
      body.style.display = 'none';
      btn.textContent = '+';
    }
  });
}

function initProjectCards() {
  const grid = document.getElementById('project-grid');
  if (!grid) return;

  _restoreProjectStates();

  // Use event delegation on the grid so we don't have to re-bind after DOM moves
  grid.addEventListener('dragstart', e => {
    const card = e.target.closest('.project-card[data-project-id]');
    if (!card) return;
    _dragSrc      = card;
    _dragLastOver = null;
    e.dataTransfer.effectAllowed = 'move';
    // Delay opacity so browser can still snapshot the drag image
    requestAnimationFrame(() => { if (_dragSrc) _dragSrc.style.opacity = '0.35'; });
  });

  grid.addEventListener('dragenter', e => {
    e.preventDefault();
    const card = e.target.closest('.project-card[data-project-id]');
    if (!card || card === _dragSrc || card === _dragLastOver) return;
    _dragLastOver = card;

    // Determine insert position: before or after the hovered card
    const rect = card.getBoundingClientRect();
    const after = e.clientY > rect.top + rect.height / 2;
    if (after) {
      grid.insertBefore(_dragSrc, card.nextSibling);
    } else {
      grid.insertBefore(_dragSrc, card);
    }
  });

  grid.addEventListener('dragover', e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  });

  grid.addEventListener('drop', e => {
    e.preventDefault();
    // DOM is already in the correct order from dragenter — nothing to do
  });

  grid.addEventListener('dragend', () => {
    if (_dragSrc) _dragSrc.style.opacity = '';
    _dragSrc      = null;
    _dragLastOver = null;
    _saveProjectOrder();
  });
}

function toggleProjectCollapse(projectId) {
  const card = document.querySelector(`#project-grid .project-card[data-project-id="${projectId}"]`);
  if (!card) return;
  const body = card.querySelector('.proj-body');
  const btn  = card.querySelector('.proj-collapse-btn');
  if (!body) return;
  const collapsed = body.style.display === 'none';
  body.style.display = collapsed ? '' : 'none';
  if (btn) btn.textContent = collapsed ? '−' : '+';
  if (collapsed) {
    localStorage.removeItem(`proj-collapsed-${projectId}`);
  } else {
    localStorage.setItem(`proj-collapsed-${projectId}`, '1');
  }
}

async function untrackProject(projectId, title) {
  if (!confirm(`Hide "${title}" from your dashboard?\n\nIt won't be deleted — you can show it again at the bottom of the Work tab.`)) return;
  const card = document.querySelector(`#project-grid .project-card[data-project-id="${projectId}"]`);
  if (card) { card.style.opacity = '0.3'; card.style.pointerEvents = 'none'; }
  await fetch(`/api/project/untrack/${projectId}`, { method: 'POST' });
  htmx.ajax('GET', '/api/partial/work/projects', { target: '#projects-zone', swap: 'innerHTML' });
}

async function retrackProject(projectId) {
  await fetch(`/api/project/track/${projectId}`, { method: 'POST' });
  htmx.ajax('GET', '/api/partial/work/projects', { target: '#projects-zone', swap: 'innerHTML' });
}

// Re-init after HTMX settles (outerHTML swaps replace the element)
document.addEventListener('htmx:afterSettle', () => {
  if (document.getElementById('project-grid')) initProjectCards();
});

document.addEventListener('DOMContentLoaded', initProjectCards);

// ─── Library browser ───────────────────────────────────────────────────

function setLibCollection(col) {
  const hiddenEl = document.getElementById('lib-col-hidden');
  if (hiddenEl) hiddenEl.value = col;
  document.querySelectorAll('.lib-chip[data-col]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.col === col);
  });
  _refreshLibTable();
}

function setLibType(type) {
  const hiddenEl = document.getElementById('lib-type-hidden');
  if (hiddenEl) hiddenEl.value = type;
  document.querySelectorAll('.lib-type-btn[data-type]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === type);
  });
  _refreshLibTable();
}

function _refreshLibTable() {
  // Sync select values into hidden fields before submitting
  const sortSel = document.getElementById('lib-sort');
  const siSel   = document.getElementById('lib-search-in');
  const yfInput = document.getElementById('lib-year-from');
  const ytInput = document.getElementById('lib-year-to');
  if (sortSel) { const h = document.getElementById('lib-sort-hidden'); if (h) h.value = sortSel.value; }
  if (siSel)   { const h = document.getElementById('lib-si-hidden');   if (h) h.value = siSel.value; }
  if (yfInput) { const h = document.getElementById('lib-yf-hidden');   if (h) h.value = yfInput.value; }
  if (ytInput) { const h = document.getElementById('lib-yt-hidden');   if (h) h.value = ytInput.value; }

  const q         = (document.getElementById('lib-q')         || {}).value || '';
  const author    = (document.getElementById('lib-author')     || {}).value || '';
  const col       = (document.getElementById('lib-col-hidden') || {}).value || '';
  const type      = (document.getElementById('lib-type-hidden')|| {}).value || '';
  const sort      = (document.getElementById('lib-sort-hidden')|| {}).value || 'newest';
  const searchIn  = (document.getElementById('lib-si-hidden')  || {}).value || 'all';
  const yearFrom  = (document.getElementById('lib-yf-hidden')  || {}).value || '';
  const yearTo    = (document.getElementById('lib-yt-hidden')  || {}).value || '';
  const journalQ  = (document.getElementById('lib-journal')    || {}).value || '';

  htmx.ajax('GET', '/api/partial/knowledge/library-table', {
    target: '#lib-table-area',
    swap:   'outerHTML',
    values: {
      q, author, collection: col, item_type: type,
      sort, search_in: searchIn,
      year_from: yearFrom, year_to: yearTo,
      journal_q: journalQ,
    },
  });
}

function clearLibFilters() {
  ['lib-q','lib-author','lib-journal','lib-year-from','lib-year-to'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['lib-col-hidden','lib-type-hidden','lib-yf-hidden','lib-yt-hidden'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const sortEl = document.getElementById('lib-sort');
  if (sortEl) sortEl.value = 'newest';
  const siEl = document.getElementById('lib-search-in');
  if (siEl) siEl.value = 'all';
  document.querySelectorAll('.lib-chip[data-col]').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.col === ''));
  document.querySelectorAll('.lib-type-btn[data-type]').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.type === ''));
  _refreshLibTable();
}

function toggleAbstract(id) {
  const el = document.getElementById('abs-' + id);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function runMetisUpdate() {
  const btn = document.getElementById('update-btn');
  const spin = document.getElementById('update-spinner');
  if (btn) { btn.style.display = 'none'; }
  if (spin) { spin.style.display = 'inline'; }
  try {
    const res = await fetch('/api/scan/content', { method: 'POST' });
    const data = await res.json();
    const msg = data.summary || [
      data.news_added   != null ? `${data.news_added} news`    : null,
      data.papers_added != null ? `${data.papers_added} papers` : null,
      data.zotero_added != null ? `${data.zotero_added} Zotero` : null,
    ].filter(Boolean).join(' · ') || 'Update complete.';
    showToast(msg);
    // Refresh today scan panel if visible
    const todayScan = document.getElementById('today-scan');
    if (todayScan) {
      htmx.ajax('GET', '/api/partial/today/scan', { target: '#today-scan', swap: 'outerHTML' });
    }
    // Refresh lib table if Library tab visible
    const libTable = document.getElementById('lib-table-area');
    if (libTable) {
      htmx.ajax('GET', '/api/partial/knowledge/sync-status', { target: '#lib-sync-bar', swap: 'outerHTML' });
    }
  } catch (e) {
    showToast('Update failed: ' + e.message);
  } finally {
    if (btn) { btn.style.display = ''; }
    if (spin) { spin.style.display = 'none'; }
  }
}

async function syncZoteroLibrary() {
  const btn = document.getElementById('zotero-sync-btn');
  if (btn) { btn.textContent = 'SYNCING…'; btn.disabled = true; }
  try {
    const res = await fetch('/api/knowledge/sync-zotero', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
      showToast(data.message || 'Zotero sync complete.');
      // Refresh the sync status bar and library table
      htmx.ajax('GET', '/api/partial/knowledge/sync-status',  { target: '#lib-sync-bar',    swap: 'outerHTML' });
      htmx.ajax('GET', '/api/partial/knowledge/library-table', { target: '#lib-table-area', swap: 'outerHTML' });
    } else {
      showToast('Sync failed: ' + (data.message || 'unknown error'));
    }
  } catch (e) {
    showToast('Sync error: ' + e.message);
  } finally {
    if (btn) { btn.textContent = 'SYNC NOW'; btn.disabled = false; }
  }
}

// ─── Integration — Claude Code mode toggle ────────────────────────────────

function setClaudeCodeMode(mode) {
  var label = mode === 'background' ? 'background layer (always-on)' : 'invoke mode (/metis per message)';
  if (!confirm('Switch Claude Code to ' + label + '?\n\nThis will rewrite ~/.claude/CLAUDE.md.')) return;
  fetch('/api/settings/claude-code-mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: mode })
  })
  .then(function (r) { return r.json(); })
  .then(function (d) {
    if (d.status === 'ok') {
      htmx.ajax('GET', '/api/partial/metis/integration', { target: '#metis-integration-body', swap: 'innerHTML' });
      showToast(mode === 'background' ? 'Background layer activated — restart Claude Code to apply.' : 'Reverted to invoke mode.');
    } else {
      showToast('Error: ' + (d.message || 'Could not update CLAUDE.md.'));
    }
  })
  .catch(function () { showToast('Could not reach the dashboard — is it running?'); });
}

function copyDesktopPrompt() {
  var el = document.getElementById('desktop-prompt-text');
  if (!el) return;
  var text = el.textContent || el.innerText;
  navigator.clipboard.writeText(text).then(function () {
    showToast('System prompt copied — paste it into your Claude Desktop project instructions.');
  }).catch(function () {
    showToast('Copy failed — select the text manually and use Ctrl+C.');
  });
}

// ─── API key management ───────────────────────────────────────────────────

function openApiKeyReplace(name, label) {
  var overlay = document.getElementById('api-key-modal-overlay');
  if (!overlay) return;
  document.getElementById('akm-title').textContent = label || name || 'New key';
  document.getElementById('akm-key-name').value = name || '';
  document.getElementById('akm-key-name-display').value = name || '';
  document.getElementById('akm-key-name-display').readOnly = !!name;
  document.getElementById('akm-key-name-display').style.opacity = name ? '0.6' : '1';
  document.getElementById('akm-key-value').value = '';
  overlay.dataset.open = 'true';
  setTimeout(function () {
    var target = name ? document.getElementById('akm-key-value') : document.getElementById('akm-key-name-display');
    if (target) target.focus();
  }, 80);
}

function closeApiKeyModal() {
  var overlay = document.getElementById('api-key-modal-overlay');
  if (overlay) overlay.dataset.open = 'false';
}

function saveApiKey() {
  var nameInput = document.getElementById('akm-key-name');
  var nameDisplay = document.getElementById('akm-key-name-display');
  var name = (nameInput && nameInput.value.trim()) || (nameDisplay && nameDisplay.value.trim()) || '';
  var value = (document.getElementById('akm-key-value') || {}).value || '';
  name = name.trim().toUpperCase().replace(/\s+/g, '_');
  value = value.trim();
  if (!name) { showToast('Key name is required.'); return; }
  if (!value) { showToast('Key value is required.'); return; }
  fetch('/api/settings/api-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, value: value })
  })
  .then(function (r) { return r.json(); })
  .then(function (d) {
    if (d.status === 'ok') {
      closeApiKeyModal();
      htmx.ajax('GET', '/api/partial/metis/api-keys', { target: '#metis-api-keys-body', swap: 'innerHTML' });
      showToast('Key saved.');
    } else {
      showToast('Error: ' + (d.message || 'Could not save key.'));
    }
  })
  .catch(function () { showToast('Could not save key — network error.'); });
}

function removeApiKey(name) {
  if (!confirm('Remove ' + name + '? This cannot be undone.')) return;
  fetch('/api/settings/api-key/' + encodeURIComponent(name), { method: 'DELETE' })
  .then(function (r) { return r.json(); })
  .then(function (d) {
    if (d.status === 'ok') {
      htmx.ajax('GET', '/api/partial/metis/api-keys', { target: '#metis-api-keys-body', swap: 'innerHTML' });
      showToast('Key removed.');
    } else {
      showToast('Error: ' + (d.message || 'Could not remove key.'));
    }
  })
  .catch(function () { showToast('Could not remove key — network error.'); });
}

// ─── MCP status pill ───────────────────────────────────────────────────────
function _mcpSetOnline() {
  var dot = document.getElementById('mcp-dot');
  var btn = document.getElementById('mcp-reconnect-btn');
  var label = document.getElementById('mcp-label');
  if (dot) dot.style.background = '#34c759';
  if (btn) btn.style.display = 'none';
  if (label) { label.style.color = ''; label.title = 'Metis tools connected'; }
}

function _mcpSetOffline() {
  var dot = document.getElementById('mcp-dot');
  var btn = document.getElementById('mcp-reconnect-btn');
  var label = document.getElementById('mcp-label');
  if (dot) dot.style.background = '#ff9500';
  if (btn) btn.style.display = '';
  if (label) { label.style.color = '#ff9500'; label.title = 'Metis tools offline'; }
}

function mcpReconnect() {
  var btn = document.getElementById('mcp-reconnect-btn');
  if (btn) { btn.textContent = '…'; btn.disabled = true; }
  fetch('/api/mcp/reload', { method: 'POST' })
    .then(function (r) {
      if (r.ok) {
        _mcpSetOnline();
        showToast('Metis tools connected.');
      } else {
        // Reload failed — offer a full restart instead
        _mcpSetOffline();
        if (btn) { btn.textContent = 'Restart Metis'; btn.disabled = false; btn.onclick = mcpRestart; }
      }
    })
    .catch(function () {
      _mcpSetOffline();
      if (btn) { btn.textContent = 'Reconnect'; btn.disabled = false; }
    });
}

function mcpRestart() {
  var btn = document.getElementById('mcp-reconnect-btn');
  if (btn) { btn.textContent = 'Restarting…'; btn.disabled = true; }
  fetch('/api/restart', { method: 'POST' })
    .then(function () {
      // Poll /health until the server is back up, then reload the page
      var attempts = 0;
      var poll = setInterval(function () {
        attempts++;
        fetch('/health').then(function (r) {
          if (r.ok) {
            clearInterval(poll);
            window.location.reload();
          }
        }).catch(function () { /* still restarting */ });
        if (attempts > 30) { clearInterval(poll); if (btn) { btn.textContent = 'Reconnect'; btn.disabled = false; } }
      }, 500);
    })
    .catch(function () {
      if (btn) { btn.textContent = 'Reconnect'; btn.disabled = false; }
      showToast('Restart failed — please close and reopen Metis from the desktop shortcut.');
    });
}

(function () {
  fetch('/api/mcp/status')
    .then(function (r) { r.ok ? _mcpSetOnline() : _mcpSetOffline(); })
    .catch(function () { /* server not yet ready — leave grey */ });
})();

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    closeApiKeyModal();
  }
});
