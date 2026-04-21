// Metis Dashboard — App JS
// Ctrl+K / Cmd+K global capture shortcut

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    openCapture();
  }
  if (e.key === 'Escape') {
    closeCapture();
  }
});

/**
 * Open the capture overlay and load the modal via HTMX.
 */
function openCapture() {
  const overlay = document.getElementById('capture-overlay');
  const inner = document.getElementById('capture-modal-inner');
  if (!overlay) return;

  // Load modal via HTMX
  htmx.ajax('GET', '/api/capture-modal', {
    target: '#capture-modal-inner',
    swap: 'innerHTML',
  });

  overlay.style.display = 'block';
  document.body.style.overflow = 'hidden';

  // Focus textarea after brief delay for HTMX load
  setTimeout(() => {
    const ta = document.getElementById('capture-text');
    if (!ta) return;

    ta.focus();

    // Live prefix detection — update the type badge while typing
    ta.addEventListener('input', function () {
      const val = ta.value;
      const badge = document.getElementById('capture-type-badge');
      if (!badge) return;

      if (val.startsWith('i:') || val.startsWith('idea:')) {
        badge.innerHTML = '<span class="badge bg-primary">Idea</span>';
      } else if (val.startsWith('n:') || val.startsWith('note:')) {
        badge.innerHTML = '<span class="badge bg-info text-dark">Note</span>';
      } else if (val.startsWith('t:') || val.startsWith('task:')) {
        badge.innerHTML = '<span class="badge bg-warning text-dark">Task</span>';
      } else if (val.startsWith('q:') || val.startsWith('question:')) {
        badge.innerHTML = '<span class="badge bg-secondary">Question</span>';
      } else {
        badge.innerHTML = '<span class="badge bg-primary">Idea</span>';
      }
    });
  }, 100);
}

/**
 * Close the capture overlay.
 */
function closeCapture() {
  const overlay = document.getElementById('capture-overlay');
  if (overlay) overlay.style.display = 'none';
  document.body.style.overflow = '';
}

/**
 * Click on the dark backdrop (not the modal card itself) → close.
 */
function handleOverlayClick(event) {
  // Only close if the click target IS the overlay backdrop, not a child
  if (event.target === document.getElementById('capture-overlay')) {
    closeCapture();
  }
}

// ---------------------------------------------------------------------------
// DB watcher — poll every 20 s, show a reload notification when mtime changes
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
  } catch (e) {
    // ignore network errors silently
  }
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

// Start polling after the page fully loads
window.addEventListener('load', () => {
  checkDbMtime();
  setInterval(checkDbMtime, 20000);
});

// ---------------------------------------------------------------------------
// Teach tab course action helpers
// Each generates a Claude Code prompt and copies it to clipboard.
// ---------------------------------------------------------------------------

function _teachPrompt(action, courseId, courseTitle) {
  const prompt = `/metis ${action} for my course "${courseTitle}"`;
  navigator.clipboard.writeText(prompt).then(() => {
    _showToast(`Prompt copied — paste into Claude Code: ${prompt}`);
  }).catch(() => {
    _showToast(`Use this prompt in Claude Code:\n${prompt}`);
  });
}

function _showToast(msg) {
  let t = document.getElementById('teach-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'teach-toast';
    t.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9000;min-width:320px;';
    document.body.appendChild(t);
  }
  t.innerHTML = `<div class="alert alert-info alert-dismissible shadow" role="alert">
    <i class="bi bi-clipboard-check me-2"></i>${msg}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>`;
}

function openCourseChat(id, title) {
  _teachPrompt('Open a teaching chat session', id, title);
}
function openCourseCowork(id, title) {
  _teachPrompt('Co-work on course improvement', id, title);
}
function openCourseSlides(id, title) {
  _teachPrompt('Generate a slide deck', id, title);
}
function openAssessmentBuilder(id, title) {
  _teachPrompt('Build an assessment', id, title);
}
function openQuestionBank(id, title) {
  _teachPrompt('Build a student question bank', id, title);
}
function openGapAnalysis(id, title) {
  _teachPrompt('Run a curriculum gap analysis', id, title);
}
