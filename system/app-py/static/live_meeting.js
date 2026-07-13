/**
 * live_meeting.js — Real-time meeting assistant
 * Uses the Web Speech API (Chrome/Edge) for transcription.
 * Sends segments to /api/meeting/live-segment for cross-pollination.
 */

// Detection: check server transcription mode
let _serverStatus = null;
async function _checkServerWhisper() {
  if (_serverStatus !== null) return _serverStatus.available;
  try {
    const r = await fetch('/api/transcription/status');
    _serverStatus = await r.json();
  } catch (e) {
    _serverStatus = { available: false };
  }
  return _serverStatus.available === true;
}
function _serverMode()          { return _serverStatus?.mode || 'browser'; }
function _serverDiarize()       { return _serverStatus?.diarization === true; }
function _serverVoiceProfiles() { return _serverStatus?.voice_profiles === true; }

class LiveMeetingSession {
  constructor() {
    this.speakers = [];
    this.speakerColors = {};
    this.currentSpeakerIndex = 0;
    this.segments = [];          // {speaker, text, ts, idx}
    this.interimText = '';
    this.pendingText = '';
    this.wordCount = 0;
    this.recognition = null;     // Web Speech API
    this.mediaRecorder = null;   // MediaRecorder for server Whisper
    this.audioChunks = [];
    this.useServerWhisper = false;
    this.serverBackend = 'auto';   // 'auto' | 'voxtral'
    this.running = false;
    this.paused = false;
    this.startTime = null;
    this.timerInterval = null;
    this.chunkInterval = null;
    this.lang = 'en-US';
    this.title = '';
    this.connectionHistory = [];  // all connections ever surfaced
  }

  // -----------------------------------------------------------------------
  // Setup
  // -----------------------------------------------------------------------

  init(title, speakerNames, lang) {
    this.title = title;
    this.lang = lang || 'en-US';
    const palette = [
      'var(--m-accent)',
      'var(--m-ochre)',
      'var(--m-ok)',
      '#a78bfa',
      'var(--m-info, #60a5fa)',
    ];
    this.speakers = speakerNames.filter(s => s.trim());
    if (!this.speakers.length) this.speakers = ['Speaker'];
    this.speakers.forEach((name, i) => {
      this.speakerColors[name] = palette[i % palette.length];
    });
    this.currentSpeakerIndex = 0;
  }

  get currentSpeaker() {
    return this.speakers[this.currentSpeakerIndex] || 'Speaker';
  }

  // -----------------------------------------------------------------------
  // Recording control
  // -----------------------------------------------------------------------

  async startWithMode(serverWhisper) {
    this.useServerWhisper = serverWhisper;
    this.running = true;
    this.paused = false;
    this.startTime = Date.now();
    this._startTimer();

    if (serverWhisper) {
      await this._startServerWhisper();
    } else {
      this._startBrowserSpeech();
    }

    const modeLabel = serverWhisper ? 'WHISPER' : 'LISTENING';
    this._setStatus(modeLabel);
    return true;
  }

  start() {
    this._startBrowserSpeech();
    this.running = true;
    this.paused = false;
    this.startTime = Date.now();
    this._startTimer();
    this._setStatus('LISTENING');
    return true;
  }

  _startBrowserSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      if (window.showToast) {
        showToast("Live transcription needs Chrome or Edge — Firefox doesn't have the browser feature I use. Paste a transcript instead?");
      } else {
        console.warn('Live transcription requires Chrome or Edge.');
      }
      return false;
    }

    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = this.lang;
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (e) => this._onResult(e);
    this.recognition.onerror = (e) => {
      if (e.error === 'not-allowed') {
        if (window.showToast) {
          showToast("I need microphone access. Click the camera/mic icon in your browser's address bar, set it to Allow, then try Start listening again.");
        }
        this.stop();
      }
    };
    this.recognition.onend = () => {
      if (this.running && !this.paused) {
        try { this.recognition.start(); } catch (e) { /* already starting */ }
      }
    };

    this.recognition.start();
    return true;
  }

  async _startServerWhisper() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      if (window.showToast) {
        showToast("I need microphone access. Click the camera/mic icon in your browser's address bar, set it to Allow, then try Start listening again.");
      }
      this.stop();
      return;
    }

    this._scheduleChunk(stream);
  }

  _scheduleChunk(stream) {
    if (!this.running || this.paused) return;

    const chunks = [];
    const mr = new MediaRecorder(stream, { mimeType: this._bestMime() });
    this.mediaRecorder = mr;

    mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    mr.onstop = async () => {
      if (!this.running) return;
      const blob = new Blob(chunks, { type: mr.mimeType });
      if (blob.size > 1000) {
        await this._sendChunk(blob, mr.mimeType);
      }
      if (this.running && !this.paused) {
        this._scheduleChunk(stream);
      }
    };

    mr.start();
    this._setInterimWhisper('recording');
    // Record 3.5-second chunks — GPU transcribes each in <0.5s
    this.chunkInterval = setTimeout(() => {
      if (mr.state === 'recording') mr.stop();
    }, 3500);
  }

  _bestMime() {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
  }

  async _sendChunk(blob, mimeType) {
    this._setInterimWhisper('transcribing');
    const fd = new FormData();
    const ext = mimeType.includes('ogg') ? '.ogg' : mimeType.includes('mp4') ? '.mp4' : '.webm';
    fd.append('audio', blob, `chunk${ext}`);
    fd.append('language', this.lang.split('-')[0]);
    fd.append('speaker', this.currentSpeaker);
    fd.append('diarize', (_serverDiarize() || this.serverBackend === 'voxtral') ? 'true' : 'false');
    fd.append('backend', this.serverBackend);
    try {
      const r = await fetch('/api/transcription/chunk', { method: 'POST', body: fd });
      const data = await r.json();
      this._setInterimWhisper('');
      if (data.segments && data.segments.length && _serverDiarize()) {
        // WhisperX diarization: group consecutive same-speaker segments
        this._addDiarizedSegments(data.segments);
      } else if (data.text && data.text.trim()) {
        this._addServerText(
          data.text.trim(),
          data.speaker || this.currentSpeaker,
          data.segments?.[0]?.speaker_confidence
        );
      }
    } catch (e) {
      this._setInterimWhisper('');
    }
  }

  _addDiarizedSegments(segments) {
    // Group segments by speaker, committing each speaker turn as a separate transcript entry
    let currentSpk = null, currentTexts = [];
    const flush = () => {
      if (!currentTexts.length) return;
      const text = currentTexts.join(' ').trim();
      // Map WhisperX SPEAKER_00/01 labels to configured names by index
      const spkIdx = parseInt((currentSpk || 'SPEAKER_00').replace(/\D/g,'')) || 0;
      const spkName = this.speakers[spkIdx % this.speakers.length] || currentSpk || 'Speaker';
      this.pendingText = text;
      this.wordCount = text.split(/\s+/).length;
      // Temporarily override current speaker for commit
      const savedIdx = this.currentSpeakerIndex;
      this.currentSpeakerIndex = spkIdx % this.speakers.length;
      this._commitPending();
      this.currentSpeakerIndex = savedIdx;
      currentTexts = [];
    };
    for (const seg of segments) {
      const spk = seg.speaker || 'SPEAKER_00';
      if (spk !== currentSpk) { flush(); currentSpk = spk; }
      if (seg.text && seg.text.trim()) currentTexts.push(seg.text.trim());
    }
    flush();
  }

  _setInterimWhisper(state) {
    const el = document.getElementById('lm-interim');
    if (!el) return;
    if (state === 'recording') {
      el.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;color:var(--m-muted);font-family:var(--m-sans);font-size:12px;">
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--m-alert);animation:lm-pulse 1s infinite;"></span>
        Recording… transcript appears every few seconds
      </span>`;
    } else if (state === 'transcribing') {
      el.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;color:var(--m-accent);font-family:var(--m-sans);font-size:12px;">
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--m-accent);animation:lm-pulse 0.5s infinite;"></span>
        Transcribing…
      </span>`;
    } else {
      el.innerHTML = '';
    }
  }

  _addServerText(text, speaker, confidence) {
    // If server identified a different speaker than currently active, switch to them
    if (speaker && speaker !== 'Speaker' && speaker !== this.currentSpeaker) {
      const idx = this.speakers.indexOf(speaker);
      if (idx !== -1) {
        this._commitPending();
        this.currentSpeakerIndex = idx;
        this._updateSpeakerButtons();
        this._autoIdentified = { speaker, confidence };
      }
    }
    this.pendingText += (this.pendingText ? ' ' : '') + text;
    this.wordCount += text.split(/\s+/).length;
    this._commitPending();
  }

  pause() {
    if (!this.running) return;
    this.paused = true;
    if (this.recognition) this.recognition.stop();
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') this.mediaRecorder.stop();
    if (this.chunkInterval) { clearTimeout(this.chunkInterval); this.chunkInterval = null; }
    this._setStatus('PAUSED');
    this._commitPending();
  }

  resume() {
    if (!this.paused) return;
    this.paused = false;
    if (this.useServerWhisper) {
      navigator.mediaDevices.getUserMedia({ audio: true }).then(s => this._scheduleChunk(s));
    } else {
      this.recognition.start();
    }
    this._setStatus(this.useServerWhisper ? 'WHISPER' : 'LISTENING');
  }

  stop() {
    this.running = false;
    this.paused = false;
    if (this.recognition) this.recognition.stop();
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') this.mediaRecorder.stop();
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.chunkInterval) { clearTimeout(this.chunkInterval); this.chunkInterval = null; }
    this._commitPending();
    this._setStatus('STOPPED');
  }

  switchSpeaker(idx) {
    this._commitPending();
    this.currentSpeakerIndex = idx;
    this._updateSpeakerButtons();
    this._setStatus(this.running && !this.paused ? 'LISTENING' : 'PAUSED');
  }

  // -----------------------------------------------------------------------
  // Internal
  // -----------------------------------------------------------------------

  _onResult(e) {
    let interimChunk = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) {
        this.pendingText += (this.pendingText ? ' ' : '') + t.trim();
        this.wordCount += t.trim().split(/\s+/).length;
        this.interimText = '';
        // Commit after ~30 words or long sentence
        if (this.wordCount >= 30 || /[.!?]$/.test(t.trim())) {
          this._commitPending();
        }
      } else {
        interimChunk += t;
      }
    }
    this.interimText = interimChunk;
    this._renderInterim();
  }

  _commitPending() {
    const text = this.pendingText.trim();
    if (!text) return;
    const seg = {
      speaker: this.currentSpeaker,
      text,
      ts: this._elapsed(),
      idx: this.segments.length,
      autoIdentified: this._autoIdentified?.speaker === this.currentSpeaker
        ? this._autoIdentified.confidence
        : null,
    };
    this._autoIdentified = null;
    this.segments.push(seg);
    this.pendingText = '';
    this.wordCount = 0;
    this._renderSegment(seg);
    this._pollConnections(text, seg.idx);
  }

  _renderInterim() {
    const el = document.getElementById('lm-interim');
    if (!el) return;
    if (this.interimText) {
      const col = this.speakerColors[this.currentSpeaker] || 'var(--m-muted)';
      el.innerHTML = `<span style="color:${col};font-family:var(--m-mono);font-size:10px;letter-spacing:0.1em;">${this.currentSpeaker.toUpperCase()}</span> <span style="color:var(--m-muted);font-style:italic;">${this.interimText}…</span>`;
    } else {
      el.innerHTML = '';
    }
  }

  _renderSegment(seg) {
    const body = document.getElementById('lm-transcript-body');
    if (!body) return;
    const col = this.speakerColors[seg.speaker] || 'var(--m-muted)';
    const autoTag = seg.autoIdentified
      ? `<span style="font-family:var(--m-mono);font-size:8px;letter-spacing:0.1em;color:var(--m-ok);margin-left:4px;" title="Auto-identified (${Math.round((seg.autoIdentified)*100)}% confidence)">▲ AUTO</span>`
      : '';
    const div = document.createElement('div');
    div.id = `lm-seg-${seg.idx}`;
    div.style.cssText = 'margin-bottom:14px;';
    div.innerHTML = `
      <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:3px;">
        <span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.14em;color:${col};font-weight:600;">${seg.speaker.toUpperCase()}</span>
        ${autoTag}
        <span style="font-family:var(--m-mono);font-size:9px;color:var(--m-muted);">${seg.ts}</span>
      </div>
      <div style="font-family:var(--m-sans);font-size:14px;color:var(--m-ink);line-height:1.65;">${this._esc(seg.text)}</div>`;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    this._renderInterim();
  }

  _pollConnections(text, segIdx) {
    const fd = new FormData();
    fd.append('text', text);
    fd.append('seg_idx', segIdx);
    fetch('/api/meeting/live-segment', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(data => {
        if (data.connections && data.connections.length) {
          data.connections.forEach(c => {
            if (!this.connectionHistory.find(h => h.title === c.title)) {
              this.connectionHistory.push(c);
              this._addConnectionRow(c, segIdx);
            }
          });
        }
      })
      .catch(() => {});
  }

  _addConnectionRow(c, segIdx) {
    const panel = document.getElementById('lm-connections-body');
    if (!panel) return;
    const colors = {
      library: 'var(--m-accent)',
      meeting: 'var(--m-ochre)',
      news: 'var(--m-ok)',
      idea: 'var(--m-muted)',
    };
    const col = colors[c.source] || 'var(--m-muted)';
    const div = document.createElement('div');
    div.style.cssText = 'display:flex;align-items:baseline;gap:8px;padding:6px 0;border-bottom:1px solid var(--m-rule-soft);';
    div.innerHTML = `
      <span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;color:${col};flex-shrink:0;width:48px;">${(c.source||'').toUpperCase()}</span>
      <div>
        <div style="font-family:var(--m-display);font-size:13px;color:var(--m-ink);line-height:1.3;">${this._esc((c.title||'').slice(0,75))}</div>
        <div style="font-family:var(--m-mono);font-size:9px;color:var(--m-muted);margin-top:2px;">at ${this._elapsed()}</div>
      </div>`;
    panel.insertBefore(div, panel.firstChild);
  }

  // -----------------------------------------------------------------------
  // Timer + status
  // -----------------------------------------------------------------------

  _startTimer() {
    this.timerInterval = setInterval(() => {
      const el = document.getElementById('lm-timer');
      if (el) el.textContent = this._elapsed();
    }, 1000);
  }

  _elapsed() {
    if (!this.startTime) return '00:00';
    const s = Math.floor((Date.now() - this.startTime) / 1000);
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    return `${m}:${(s % 60).toString().padStart(2, '0')}`;
  }

  _setStatus(txt) {
    const el = document.getElementById('lm-status');
    if (!el) return;
    const isLive = txt === 'LISTENING';
    el.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${isLive ? 'var(--m-alert)' : 'var(--m-muted)'};margin-right:6px;${isLive ? 'animation:lm-pulse 1.4s ease infinite;' : ''}"></span>${txt}`;
  }

  _updateSpeakerButtons() {
    this.speakers.forEach((name, i) => {
      const btn = document.getElementById(`lm-spk-${i}`);
      if (!btn) return;
      const active = i === this.currentSpeakerIndex;
      const col = this.speakerColors[name];
      btn.style.borderColor = active ? col : 'transparent';
      btn.style.color = active ? col : 'var(--m-muted)';
      btn.style.background = active ? 'var(--m-surface-2)' : 'transparent';
    });
  }

  // -----------------------------------------------------------------------
  // Report
  // -----------------------------------------------------------------------

  getTranscriptText() {
    return this.segments.map(s => `[${s.speaker}] (${s.ts}) ${s.text}`).join('\n\n');
  }

  getDuration() {
    return this._elapsed();
  }

  getParticipants() {
    // unique speakers that actually spoke
    const spoke = [...new Set(this.segments.map(s => s.speaker))];
    return spoke.join(', ');
  }

  generateReport() {
    const fd = new FormData();
    fd.append('transcript', this.getTranscriptText());
    fd.append('title', this.title);
    fd.append('participants', this.getParticipants());
    fd.append('duration', this.getDuration());
    fd.append('connections', JSON.stringify(this.connectionHistory));
    return fetch('/api/meeting/generate-report', { method: 'POST', body: fd })
      .then(r => r.text());
  }

  _esc(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

// -----------------------------------------------------------------------
// Global session instance + UI wiring
// -----------------------------------------------------------------------

let lm = null;

function startLiveMeetingSetup() {
  htmx.ajax('GET', '/api/partial/meetings/live-setup', {
    target: '#meeting-import-container',
    swap: 'innerHTML',
  });
}

async function beginLiveMeeting() {
  const titleEl   = document.getElementById('lm-setup-title');
  const langEl    = document.getElementById('lm-setup-lang');
  const modeSelEl = document.getElementById('lm-setup-mode');
  const speakerEls = document.querySelectorAll('.lm-setup-speaker');

  const title    = titleEl    ? titleEl.value.trim()  || 'Meeting' : 'Meeting';
  const lang     = langEl     ? langEl.value           : 'en-US';
  const chosenMode = modeSelEl ? modeSelEl.value       : 'server';
  const speakers = [...speakerEls].map(e => e.value.trim()).filter(Boolean);
  if (!speakers.length) {
    if (window.showToast) showToast('Add at least one participant name before we start.');
    return;
  }

  // Determine transcription backend
  let serverWhisper = false;
  let backendName = 'auto';
  if (chosenMode === 'voxtral') {
    // Voxtral cloud mode — uses Mistral API, always "server" capture
    serverWhisper = true;
    backendName = 'voxtral';
  } else if (chosenMode === 'server') {
    serverWhisper = await _checkServerWhisper();
    if (!serverWhisper) {
      console.warn('[live-meeting] Server Whisper unavailable, falling back to browser speech.');
    }
  }

  // Replace setup modal with the live session panel
  const html = await fetch(
    '/api/partial/meetings/live-session?' + new URLSearchParams({ title, speakers: speakers.join(',') })
  ).then(r => r.text());
  document.getElementById('meeting-import-container').innerHTML = html;

  // Show mode label in status bar
  const modeEl = document.getElementById('lm-mode');
  if (modeEl) {
    let label, col;
    if (backendName === 'voxtral') {
      label = 'Voxtral · cloud + diarization'; col = '#a78bfa';
    } else if (serverWhisper && _serverDiarize()) {
      label = 'WhisperX + diarization'; col = 'var(--m-ok)';
    } else if (serverWhisper && _serverVoiceProfiles()) {
      label = 'Whisper + voice ID'; col = 'var(--m-ok)';
    } else if (serverWhisper) {
      label = _serverMode() === 'whisperx' ? 'WhisperX' : 'Whisper · GPU'; col = 'var(--m-ok)';
    } else {
      label = 'Browser speech (instant)'; col = 'var(--m-muted)';
    }
    modeEl.textContent = label;
    modeEl.style.color = col;
  }

  // Init session
  lm = new LiveMeetingSession();
  lm.init(title, speakers, lang);
  lm.serverBackend = backendName;

  // Render speaker buttons
  const bar = document.getElementById('lm-speaker-bar');
  if (bar) {
    bar.innerHTML = speakers.map((name, i) => {
      const col = lm.speakerColors[name];
      const active = i === 0;
      return `<button id="lm-spk-${i}" onclick="lm.switchSpeaker(${i})"
        style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;padding:5px 12px;
        border:1px solid ${active ? col : 'transparent'};border-radius:3px;cursor:pointer;
        background:${active ? 'var(--m-surface-2)' : 'transparent'};
        color:${active ? col : 'var(--m-muted)'};">${name.toUpperCase()}</button>`;
    }).join('');
  }

  await lm.startWithMode(serverWhisper);
}

function toggleLmPause() {
  if (!lm) return;
  const btn = document.getElementById('lm-pause-btn');
  if (lm.paused) {
    lm.resume();
    if (btn) btn.textContent = 'PAUSE';
  } else {
    lm.pause();
    if (btn) btn.textContent = 'RESUME';
  }
}

function endLiveMeeting() {
  if (!lm) return;
  lm.stop();
  const controls = document.getElementById('lm-controls');
  if (controls) controls.innerHTML =
    '<button class="btn btn--primary btn--caps" onclick="generateMeetingReport()">Generate Report</button>' +
    '<button class="btn btn--ghost btn--caps" onclick="saveLiveSessionRaw()">Save Transcript Only</button>';
}

function generateMeetingReport() {
  if (!lm) return;
  const btn = event.target;
  btn.textContent = 'GENERATING…';
  btn.disabled = true;
  lm.generateReport().then(html => {
    const reportEl = document.getElementById('lm-report-panel');
    if (reportEl) {
      reportEl.innerHTML = html;
      reportEl.style.display = 'block';
      reportEl.scrollIntoView({ behavior: 'smooth' });
    }
    btn.textContent = 'REPORT READY';
  });
}

function saveLiveSessionRaw() {
  if (!lm || !lm.segments.length) return;
  const fd = new FormData();
  fd.append('title', lm.title);
  fd.append('meeting_date', new Date().toISOString().slice(0, 10));
  fd.append('attendees', lm.getParticipants());
  fd.append('duration_minutes', Math.ceil(parseFloat(lm.getDuration().replace(':', '.')) * 60 / 100) || '');
  fd.append('meeting_type', 'meeting');
  fd.append('transcript', lm.getTranscriptText());
  fetch('/api/meeting/import', { method: 'POST', body: fd })
    .then(r => r.text())
    .then(() => { if (window.showToast) showToast('Transcript saved to Meetings.'); });
}

function closeLiveSession() {
  if (lm) lm.stop();
  const el = document.getElementById('meeting-import-container');
  if (el) el.innerHTML = '';
}
