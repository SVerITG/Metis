// TodayPage.jsx — the Metis "Today" page, themed.
// Exports TodayPage (takes theme: 'manuscript' | 'archive' | 'observatory')
// plus the Metis compass wordmark. Single Babel scope → expose on window.

const Wordmark = () => (
  <a className="metis-brand" href="#">
    <svg viewBox="0 0 64 64" className="metis-mark reveal" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
        <circle cx="32" cy="32" r="26" className="m-outer"/>
        <circle cx="32" cy="32" r="16" className="m-inner"/>
        <line x1="6"  y1="32" x2="58" y2="32" className="m-h"/>
        <line x1="32" y1="6"  x2="32" y2="58" className="m-v"/>
        <line x1="32" y1="2"  x2="32" y2="6"  className="m-t m-n"/>
        <line x1="32" y1="58" x2="32" y2="62" className="m-t m-s"/>
        <line x1="2"  y1="32" x2="6"  y2="32" className="m-t m-w"/>
        <line x1="58" y1="32" x2="62" y2="32" className="m-t m-e"/>
      </g>
      <circle cx="32" cy="32" r="2.2" className="m-dot" fill="currentColor"/>
    </svg>
    <span className="wordmark">Metis</span>
  </a>
);

const Nav = () => (
  <nav className="mf-nav">
    <Wordmark/>
    <div className="mf-tabs">
      <button className="mf-tab active">Today</button>
      <button className="mf-tab">Threads</button>
      <button className="mf-tab">Library</button>
      <button className="mf-tab">Sources</button>
    </div>
    <div className="mf-nav-right">
      <span className="mf-trust"><span className="dot"/>Local · Private</span>
      <button className="mf-capture">Capture <kbd>⌘K</kbd></button>
    </div>
  </nav>
);

const Hero = () => (
  <header className="mf-hero">
    <div>
      <div className="mf-hero-date">Tuesday · April 21, 2026 · Day 112</div>
      <h1 className="mf-hero-greeting">
        Good morning, Ines.<br/>
        <em>Three threads need you today.</em>
      </h1>
    </div>
    <div className="mf-hero-stats">
      <div className="mf-stat">
        <div className="mf-stat-num">47</div>
        <div className="mf-stat-label">Open threads</div>
      </div>
      <div className="mf-stat">
        <div className="mf-stat-num">1,284</div>
        <div className="mf-stat-label">Sources indexed</div>
      </div>
      <div className="mf-stat">
        <div className="mf-stat-num">6h 12m</div>
        <div className="mf-stat-label">Deep work · wk</div>
      </div>
    </div>
  </header>
);

const Focus = () => (
  <div>
    <div className="mf-seclabel">Focus thread</div>
    <article className="mf-focus">
      <div className="mf-focus-kicker">Reopened yesterday · 14:22</div>
      <h2 className="mf-focus-title">
        Does municipal fiber actually lower churn, or does it just correlate with density?
      </h2>
      <div className="mf-focus-next">
        <b>Next step</b>
        You paused on the Chattanooga 2018–2023 cohort. The control-group paper
        you asked for arrived overnight — <em>Powell & Ito</em>, already summarized below.
        Pick up where you left off, or re-scope the question.
      </div>
      <div className="mf-focus-meta">
        <span>◦ 23 sources</span>
        <span>◦ 8 notes</span>
        <span>◦ 4 open questions</span>
        <span>◦ Last touched 17 hrs ago</span>
      </div>
    </article>
  </div>
);

const Overnight = () => {
  const items = [
    { kind: 'News',    count: 3, text: <>FCC released the <em>Q1 broadband affordability report</em> — 214 pages, 11 match your thread filters.</> },
    { kind: 'Source',  count: 1, text: <>New paper on your watchlist: Powell & Ito, <em>“Fiber, density, and the churn confound.”</em></> },
    { kind: 'Reply',   count: 2, text: <>Dr. Agyeman responded to your 3 citation requests. Two PDFs attached.</> },
    { kind: 'Digest',  count: 1, text: <>Your <em>Monday brief</em> is ready — 6 items, ~4 min read.</> },
    { kind: 'Flag',    count: 1, text: <>A contradiction was detected between two of your cited sources on rural uptake rates.</> },
  ];
  return (
    <div>
      <div className="mf-seclabel">Overnight · since 22:14 yesterday</div>
      <div className="mf-overnight">
        {items.map((it, i) => (
          <div className="mf-ov-item" key={i}>
            <div className={'mf-ov-kind' + (it.kind === 'News' ? ' news' : '')}>{it.kind}</div>
            <div className="mf-ov-text">{it.text}</div>
            <div className="mf-ov-count">{String(it.count).padStart(2, '0')}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const Scan = () => (
  <div>
    <div className="mf-seclabel">Continuous scan</div>
    <div className="mf-scan">
      <div className="mf-scan-left">
        <div className="mf-scan-label">Watching 12 feeds · last run 06:02</div>
        <div className="mf-scan-status">
          Next scan in <code>18m</code> — arXiv, SSRN, 3 RSS, and your <code>~/research</code> folder.
        </div>
      </div>
      <button className="mf-btn">Tune scan</button>
    </div>
  </div>
);

const CaptureCard = () => (
  <div>
    <div className="mf-seclabel">Capture</div>
    <div className="mf-capture-card">
      <div className="ct-modes">
        <span className="active">Note</span>
        <span>Question</span>
        <span>Quote</span>
        <span>Source</span>
      </div>
      <textarea
        defaultValue=""
        placeholder="What are you thinking about?"
      />
      <div className="mf-capture-foot">
        <span>↵ save  ·  ⌘↵ file into thread  ·  ⌘J attach source</span>
        <span>Drafting · not saved</span>
      </div>
    </div>
  </div>
);

const Tokens = () => (
  <div className="mf-tokens">
    <span><b>47</b> threads</span>
    <span><b>1,284</b> sources</span>
    <span><b>312</b> notes</span>
    <span style={{marginLeft: 'auto'}}>v0.4.2 · Direction Preview</span>
  </div>
);

window.TodayPage = function TodayPage({ theme = 'manuscript' }) {
  return (
    <div className={'metis-frame theme-' + theme}>
      <Nav/>
      <div className="mf-page">
        <Hero/>
        <div className="mf-grid">
          <div className="mf-col">
            <Focus/>
            <Scan/>
          </div>
          <div className="mf-col">
            <Overnight/>
            <CaptureCard/>
          </div>
        </div>
        <Tokens/>
      </div>
    </div>
  );
};

window.MetisWordmark = Wordmark;
