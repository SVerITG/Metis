// Shared nav + shell for Metis UI kit.
// Exposes: Sidebar, Topbar, MetisMark, NAV_ITEMS, Ico, Chip, Kicker, SecLabel
// to window, used by app.html and each surface file.

const NAV_ITEMS = [
  { id: 'today',     num: '01', label: 'Today',     meta: '07:12',  group: 'surfaces' },
  { id: 'knowledge', num: '02', label: 'Knowledge', meta: '240',    group: 'surfaces' },
  { id: 'thinking',  num: '03', label: 'Thinking',  meta: '3',      group: 'surfaces' },
  { id: 'planner',   num: '04', label: 'Planner',   meta: 'Q4',     group: 'surfaces' },
  { id: 'work',      num: '05', label: 'Work',      meta: '14',     group: 'surfaces' },
  { id: 'meetings',  num: '06', label: 'Meetings',  meta: '2',      group: 'surfaces' },
  { id: 'learning',  num: '07', label: 'Learning',  meta: '6',      group: 'surfaces' },
  { id: 'teach',     num: '08', label: 'Teach',     meta: '1',      group: 'surfaces' },
  { id: 'metis',     num: '09', label: 'Metis',     meta: '',       group: 'settings' },
];

const NAV_TITLES = {
  today:     { eyebrow: 'Thursday · 14 November · 07:12', title: 'Good morning, Researcher.', accent: 'em' },
  knowledge: { eyebrow: 'The shelves · 240 cards · 14 slipcases', title: 'Knowledge' },
  thinking:  { eyebrow: 'Three open · last touched 07:12', title: 'Thinking' },
  planner:   { eyebrow: 'Q4 · week 46 of 52', title: 'Planner' },
  work:      { eyebrow: '14 tasks · 3 projects · 2 paused', title: 'Work' },
  meetings:  { eyebrow: 'Two today · three this week', title: 'Meetings' },
  learning:  { eyebrow: '6 courses · 48 cards due today', title: 'Learning' },
  teach:     { eyebrow: 'Drafts outward · 1 published this year', title: 'Teach' },
  metis:     { eyebrow: 'Settings · model · memory · keys', title: 'Metis' },
};

function MetisMark({ className = 'metis-mark', ...props }) {
  return (
    <svg className={className} viewBox="0 0 64 64" {...props}>
      <circle cx="32" cy="32" r="26"/>
      <circle cx="32" cy="32" r="16"/>
      <line x1="6"  y1="32" x2="13" y2="32"/>
      <line x1="51" y1="32" x2="58" y2="32"/>
      <line x1="32" y1="6"  x2="32" y2="13"/>
      <line x1="32" y1="51" x2="32" y2="58"/>
      <line x1="23" y1="32" x2="41" y2="32"/>
      <line x1="32" y1="23" x2="32" y2="41"/>
      <circle className="pup" cx="32" cy="32" r="2.4"/>
    </svg>
  );
}

// Tiny stroke icon bank — bespoke, 1.5px, round caps. currentColor.
const ICONS = {
  search:    <><circle cx="7" cy="7" r="4.5"/><line x1="10.2" y1="10.2" x2="13" y2="13"/></>,
  plus:      <><line x1="8" y1="3" x2="8" y2="13"/><line x1="3" y1="8" x2="13" y2="8"/></>,
  chev:      <polyline points="5 6 8 9 11 6"/>,
  chevR:     <polyline points="6 4 9 8 6 12"/>,
  chevL:     <polyline points="10 4 7 8 10 12"/>,
  arrowR:    <><line x1="3" y1="8" x2="13" y2="8"/><polyline points="9 4 13 8 9 12"/></>,
  dot:       <circle cx="8" cy="8" r="1.5" fill="currentColor" stroke="none"/>,
  square:    <rect x="3" y="3" width="10" height="10"/>,
  check:     <polyline points="3 8 7 12 13 4"/>,
  card:      <><rect x="2" y="4" width="12" height="9"/><line x1="2" y1="7" x2="14" y2="7"/></>,
  pen:       <><line x1="3" y1="13" x2="5" y2="13"/><path d="M4 12 L11 5 L13 7 L6 14 Z"/></>,
  book:      <><path d="M2 3 h5 a2 2 0 0 1 2 2 v8 a2 2 0 0 0 -2 -2 H2 Z"/><path d="M14 3 h-5 a2 2 0 0 0 -2 2 v8 a2 2 0 0 1 2 -2 h5 Z"/></>,
  clock:     <><circle cx="8" cy="8" r="5.5"/><polyline points="8 5 8 8 10 9.5"/></>,
  thread:    <><circle cx="5" cy="5" r="2"/><circle cx="11" cy="11" r="2"/><path d="M5 7 L5 10 Q5 11 6 11 L9 11"/></>,
  tag:       <><path d="M3 3 h5 l5 5 -5 5 -5 -5 Z"/><circle cx="6" cy="6" r="0.8" fill="currentColor" stroke="none"/></>,
  compass:   <><circle cx="8" cy="8" r="5.5"/><polygon points="8 4 10 8 8 12 6 8"/></>,
  column:    <><rect x="2" y="2" width="4" height="12"/><rect x="7" y="2" width="4" height="12"/><rect x="12" y="2" width="2" height="12"/></>,
  at:        <><circle cx="8" cy="8" r="2.5"/><path d="M10.5 8 v1.5 a2 2 0 0 0 2 0 v-1 a4.5 4.5 0 1 0 -2 4"/></>,
  play:      <polygon points="4 3 13 8 4 13"/>,
  teach:     <><path d="M2 5 L8 2 L14 5 L8 8 Z"/><path d="M4 6.5 V10 Q4 11 5 11.5 L8 13 L11 11.5 Q12 11 12 10 V6.5"/></>,
  setting:   <><circle cx="8" cy="8" r="2"/><path d="M8 1 v2 M8 13 v2 M1 8 h2 M13 8 h2 M3 3 l1.4 1.4 M11.6 11.6 L13 13 M3 13 l1.4 -1.4 M11.6 4.4 L13 3"/></>,
  archive:   <><rect x="2" y="3" width="12" height="3"/><path d="M3 6 V13 H13 V6"/><line x1="6" y1="9" x2="10" y2="9"/></>,
};

function Ico({ name, className = 'ico', ...props }) {
  return (
    <svg className={className} viewBox="0 0 16 16" {...props}>
      {ICONS[name] || ICONS.dot}
    </svg>
  );
}

function Chip({ kind = '', children, plain = false }) {
  const cls = 'chip' + (kind ? ' chip--' + kind : '') + (plain ? ' chip--plain' : '');
  return <span className={cls}>{children}</span>;
}

function Kicker({ kind = '', children }) {
  const cls = 'kicker' + (kind ? ' kicker--' + kind : '');
  return <div className={cls}>{children}</div>;
}

function SecLabel({ children, tail }) {
  return (
    <div className="sec-label">
      <span>{children}</span>
      {tail && <span className="tail">{tail}</span>}
    </div>
  );
}

function Sidebar({ current, onNavigate }) {
  const surfaces = NAV_ITEMS.filter(n => n.group === 'surfaces');
  const settings = NAV_ITEMS.filter(n => n.group === 'settings');
  return (
    <aside className="side">
      <div className="brand">
        <MetisMark />
        <div>
          <div className="b-word">Meti<em>s</em></div>
          <div className="b-sub">Archive</div>
        </div>
      </div>

      <div className="nav-sec">
        <div className="nav-label"><span>Surfaces</span><span>IX</span></div>
        {surfaces.map(item => (
          <div key={item.id}
               className={'nav-item' + (current === item.id ? ' active' : '')}
               onClick={() => onNavigate(item.id)}>
            <span className="n-num">{item.num}</span>
            <span className="n-label">{item.label}</span>
            <span className="n-meta">{item.meta}</span>
          </div>
        ))}
      </div>

      <div className="nav-sec">
        <div className="nav-label"><span>System</span></div>
        {settings.map(item => (
          <div key={item.id}
               className={'nav-item' + (current === item.id ? ' active' : '')}
               onClick={() => onNavigate(item.id)}>
            <span className="n-num">{item.num}</span>
            <span className="n-label">{item.label}</span>
            <span className="n-meta">{item.meta}</span>
          </div>
        ))}
      </div>

      <div className="side-foot">
        <span className="mini-ava">S</span>
        <span>Researcher · Reader in residence</span>
      </div>
    </aside>
  );
}

function Topbar({ current }) {
  const t = NAV_TITLES[current];
  const item = NAV_ITEMS.find(n => n.id === current);
  return (
    <div className="topbar">
      <div className="crumbs">
        <span>Metis</span>
        <span className="sep">/</span>
        <span className="here">{item?.label}</span>
      </div>
      <div className="search">
        <Ico name="search" />
        <span>Find across the archive…</span>
        <span className="hk">⌘K</span>
      </div>
    </div>
  );
}

function PageHead({ current, right }) {
  const t = NAV_TITLES[current] || {};
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{t.eyebrow}</div>
        <h1>{t.accent === 'em' ? <>Good morning, <em>Researcher.</em></> : t.title}</h1>
      </div>
      {right}
    </div>
  );
}

Object.assign(window, {
  NAV_ITEMS, NAV_TITLES,
  MetisMark, Ico, Chip, Kicker, SecLabel,
  Sidebar, Topbar, PageHead,
});
