// Metis Today — UI kit components (single-file, global scope under Babel)
// Uses window.React globals; exported to window at end of file.

const { useState } = React;

/* ------------------------- TopNav ------------------------- */
function TopNav({ active = "today", onTab }) {
  const tabs = [
    ["today", "bi-sun", "Today"],
    ["knowledge", "bi-book", "Knowledge"],
    ["thinking", "bi-lightbulb", "Thinking"],
    ["planner", "bi-calendar3", "Planner"],
    ["work", "bi-briefcase", "Work"],
    ["meetings", "bi-camera-video", "Meetings"],
    ["learning", "bi-mortarboard", "Learning"],
    ["metis", "bi-robot", "Metis"],
  ];
  return (
    <div className="mk-nav">
      <span className="mk-brand"><i className="bi bi-cpu-fill" style={{ color: "#0071e3" }} />Metis</span>
      <div className="mk-tabs">
        {tabs.map(([id, ic, label]) => (
          <button
            key={id}
            className={"mk-tab " + (active === id ? "active" : "")}
            onClick={() => onTab && onTab(id)}
          >
            <i className={"bi " + ic} /> {label}
          </button>
        ))}
      </div>
      <div className="mk-nav-right">
        <button className="mk-capture"><i className="bi bi-plus-lg" /> Capture</button>
        <span className="mk-trust"><i className="bi bi-shield-check" style={{ color: "#30a46c" }} /> Local-first</span>
      </div>
    </div>
  );
}

/* ------------------------- Morning Brief ------------------------- */
function MorningBrief() {
  return (
    <div className="mk-brief">
      <div className="mk-brief-greet">Good morning, Sander.</div>
      <div className="mk-brief-date">Tuesday 21 April 2026</div>
      <div className="mk-brief-chips">
        <span className="mk-chip ok"><i className="bi bi-check-circle" /> News Radar ran at 07:02</span>
        <span className="mk-chip ok"><i className="bi bi-check-circle" /> Librarian tagged 3 papers</span>
        <span className="mk-chip warn"><i className="bi bi-exclamation-circle" /> 2 tasks overdue</span>
      </div>
      <div className="mk-paper">
        <div className="mk-paper-lab">Today's paper</div>
        Büscher et al. — <em>Passive surveillance sensitivity in post-elimination HAT foci</em>, Lancet Glob Health, April 2026. Relevant to Article 1.
      </div>
    </div>
  );
}

/* ------------------------- Value boxes ------------------------- */
function ValueBoxStrip() {
  const boxes = [
    ["Runs today", "23", "9 agents"],
    ["Tokens today", "412k", "€2.71"],
    ["Open tasks", "8", "2 overdue"],
    ["Active projects", "3", "PhD · HAT · MLM"],
  ];
  return (
    <div className="mk-vbs">
      {boxes.map(([l, v, s]) => (
        <div key={l} className="mk-vb">
          <div className="mk-vb-lab">{l}</div>
          <div className="mk-vb-val">{v}</div>
          <div className="mk-vb-sub">{s}</div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------- Recent agent runs ------------------------- */
const AGENT_RUNS = [
  { time: "14:03", agent: "librarian", model: "sonnet", text: "Tagged 3 papers on passive detection", tokens: "12k" },
  { time: "11:47", agent: "epidemiologist", model: "opus", text: "Reviewed Article 1 design, suggested sensitivity analysis", tokens: "8.2k" },
  { time: "09:22", agent: "writing-partner", model: "sonnet", text: "Re-drafted Discussion section, softened claims", tokens: "14k" },
  { time: "07:02", agent: "news-radar", model: "haiku", text: "Morning brief generated — 2 items flagged HIGH", tokens: "3.1k" },
];
const MODEL_CLASS = { haiku: "h", sonnet: "s", opus: "o" };

function RecentRuns() {
  return (
    <div className="mk-card">
      <div className="mk-card-head">
        <span><i className="bi bi-clock-history" /> Recent agent runs</span>
        <span className="mk-muted">Today</span>
      </div>
      <div className="mk-card-body">
        {AGENT_RUNS.map((r, i) => (
          <div key={i} className="mk-run">
            <span className="mk-run-time">{r.time}</span>
            <span className={"mk-agent-badge " + MODEL_CLASS[r.model]}>{r.agent}</span>
            <span className="mk-run-text">{r.text}</span>
            <span className="mk-run-tokens">{r.tokens}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------- Inbox ------------------------- */
function InboxCard() {
  const [items, setItems] = useState([
    { id: 1, from: "librarian", text: "New paper matches Article 1: Büscher 2026", sig: "HIGH" },
    { id: 2, from: "news-radar", text: "WHO HAT dashboard update — Q1 2026 data", sig: "MEDIUM" },
    { id: 3, from: "data-guardian", text: "Backup ran clean (14 GB, 02:11)", sig: "LOW" },
  ]);
  const sigClass = { HIGH: "sig-high", MEDIUM: "sig-med", LOW: "sig-low" };
  return (
    <div className="mk-card">
      <div className="mk-card-head">
        <span><i className="bi bi-inbox" /> Agent inbox</span>
        <span className="mk-muted">{items.length} unread</span>
      </div>
      <div className="mk-card-body">
        {items.map(it => (
          <div key={it.id} className="mk-inbox-row">
            <span className={sigClass[it.sig]}>{it.sig}</span>
            <span className="mk-inbox-from">{it.from}</span>
            <span className="mk-inbox-text">{it.text}</span>
            <button className="mk-btn-xs" onClick={() => setItems(items.filter(x => x.id !== it.id))}>Dismiss</button>
          </div>
        ))}
        {items.length === 0 && <div className="mk-empty">Inbox clear.</div>}
      </div>
    </div>
  );
}

/* ------------------------- Capture bar ------------------------- */
function CaptureBar({ onCapture }) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState("idea");
  const modes = [
    ["idea", "bi-lightbulb", "Idea"],
    ["task", "bi-check2-square", "Task"],
    ["note", "bi-journal-text", "Note"],
    ["ask", "bi-robot", "Ask Metis"],
  ];
  const submit = () => {
    if (!text.trim()) return;
    onCapture && onCapture({ mode, text });
    setText("");
  };
  return (
    <div className="mk-capture-bar">
      <div className="mk-capture-modes">
        {modes.map(([id, ic, lab]) => (
          <button
            key={id}
            className={"mk-mode " + (mode === id ? "active" : "")}
            onClick={() => setMode(id)}
          >
            <i className={"bi " + ic} /> {lab}
          </button>
        ))}
      </div>
      <div className="mk-capture-input">
        <textarea
          rows={2}
          placeholder={
            mode === "ask"
              ? "/metis Review my Article 1 draft for methodology"
              : "Type your " + mode + "…"
          }
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
          }}
        />
        <div className="mk-capture-foot">
          <span className="mk-muted">⌘↵ to capture · routed to {mode === "ask" ? "Metis" : "Today"}</span>
          <button className="mk-btn-primary" onClick={submit}><i className="bi bi-plus-lg" /> Capture</button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------- Kanban ------------------------- */
const KANBAN_INITIAL = {
  someday: [
    { id: "s1", title: "WHO African trypanosomiasis guideline refresh", tag: "HAT · backlog" },
    { id: "s2", title: "R package: hatmap", tag: "tooling" },
    { id: "s3", title: "Reflective piece: AI in field epi", tag: "writing" },
  ],
  incubating: [
    { id: "i1", title: "Article 2 outline", tag: "PhD · needs methods section" },
    { id: "i2", title: "MLM Course — module 4 exercises", tag: "teaching" },
  ],
  active: [
    { id: "a1", title: "HAT Dashboard v1.1", tag: "→ finalize server layer", blocked: true },
    { id: "a2", title: "MLM Course module 3", tag: "→ record demo video" },
  ],
};
const KANBAN_COLS = [
  ["someday", "Someday", "bi-moon-stars"],
  ["incubating", "Incubating", "bi-hourglass-split"],
  ["active", "Active", "bi-lightning-charge"],
];

function ProjectKanban() {
  const [cols, setCols] = useState(KANBAN_INITIAL);
  const nextCol = key => KANBAN_COLS[(KANBAN_COLS.findIndex(c => c[0] === key) + 1) % KANBAN_COLS.length][0];
  const move = (fromKey, id) => {
    const toKey = nextCol(fromKey);
    if (fromKey === toKey) return;
    setCols(prev => {
      const card = prev[fromKey].find(c => c.id === id);
      if (!card) return prev;
      return {
        ...prev,
        [fromKey]: prev[fromKey].filter(c => c.id !== id),
        [toKey]: [...prev[toKey], card],
      };
    });
  };
  return (
    <div className="mk-kanban">
      {KANBAN_COLS.map(([key, title, ic]) => (
        <div key={key} className="mk-kan-col">
          <div className="mk-kan-hd">
            <span><i className={"bi " + ic} /> {title}</span>
            <span className="mk-kan-count">{cols[key].length}</span>
          </div>
          {cols[key].map(card => (
            <div
              key={card.id}
              className={"mk-kan-card" + (card.blocked ? " blocked" : "")}
              onClick={() => move(key, card.id)}
              title="Click to promote"
            >
              <div className="mk-kan-title">{card.title}</div>
              <div className="mk-kan-meta">{card.tag}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/* ------------------------- Page ------------------------- */
function TodayPage() {
  const [active, setActive] = useState("today");
  const [toast, setToast] = useState(null);
  const onCapture = (c) => {
    setToast("Captured: " + c.text.slice(0, 40) + (c.text.length > 40 ? "…" : ""));
    setTimeout(() => setToast(null), 2200);
  };
  return (
    <div className="mk-page">
      <TopNav active={active} onTab={setActive} />
      <div className="mk-h1">Today</div>
      <div className="mk-grid">
        <div className="mk-col">
          <MorningBrief />
          <ValueBoxStrip />
          <RecentRuns />
        </div>
        <div className="mk-col">
          <CaptureBar onCapture={onCapture} />
          <InboxCard />
        </div>
      </div>
      <div className="mk-section-lab" style={{ marginTop: 20 }}>Projects</div>
      <ProjectKanban />
      {toast && (
        <div style={{
          position: "fixed", bottom: 24, right: 24,
          background: "#1d1d1f", color: "#fff", padding: "10px 14px",
          borderRadius: 10, fontSize: ".85rem", boxShadow: "0 8px 32px rgba(0,0,0,.25)",
          fontFamily: "var(--font-system)"
        }}>{toast}</div>
      )}
    </div>
  );
}

Object.assign(window, { TopNav, MorningBrief, ValueBoxStrip, RecentRuns, InboxCard, CaptureBar, ProjectKanban, TodayPage });
