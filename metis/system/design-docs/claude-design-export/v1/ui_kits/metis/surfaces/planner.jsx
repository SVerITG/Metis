// Surface 04 — Planner
function PlannerSurface() {
  return (
    <div className="page">
      <PageHead current="planner" right={<div className="page-meta"><div>WEEK 46 · Q4 · 6 WEEKS REMAINING</div></div>}/>
      <div className="grid grid-3" style={{ marginBottom: 32 }}>
        <HorizonCard label="QUARTER · Q4 OCT–DEC" title="Finish the essays on naming." body={<>Three pieces, publishable. Two are <em>in hand</em>; the third is the shape of a question.</>} progress={0.55} meta="2 of 3 drafts · est. Dec 20"/>
        <HorizonCard label="WEEK · 46" title="Thursday's essay, middle section." body={<>The single thing. If it's done by Friday, the week is <em>good enough.</em></>} progress={0.62} meta="4 focus blocks · 2 used"/>
        <HorizonCard label="TODAY · THU 14" title="Begin with the essay." body={<>One focus block at 09:30. <em>Everything else is optional.</em></>} progress={0} meta="90 MIN · 09:30 → 11:00"/>
      </div>

      <SecLabel tail="WEEK 46 · NOV 11 → NOV 17">This week at a glance</SecLabel>
      <div className="panel" style={{ padding: '24px 24px', marginBottom: 32 }}>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
          {['MON 11','TUE 12','WED 13','THU 14','FRI 15','SAT 16','SUN 17'].map((d, i) => (
            <div key={i} style={{
              padding: '12px 10px',
              border: '1px solid var(--m-rule)',
              background: i === 3 ? 'var(--m-accent-wash)' : 'var(--m-surface)',
              borderLeft: i === 3 ? '2px solid var(--m-accent)' : '1px solid var(--m-rule)',
              minHeight: 150,
              borderRadius: 2,
            }}>
              <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.16em', color: i===3?'var(--m-accent)':'var(--m-muted)', marginBottom: 8 }}>{d}</div>
              {WEEK_ITEMS[i].map((it, j) => (
                <div key={j} style={{
                  fontSize: 11, fontFamily: 'var(--m-display)', color: 'var(--m-text)',
                  padding: '3px 6px', marginBottom: 3,
                  background: it.accent ? 'var(--m-accent)' : it.ochre ? 'var(--m-ochre-wash)' : 'var(--m-surface-2)',
                  color: it.accent ? 'var(--m-on-accent)' : it.ochre ? 'var(--m-ochre-deep)' : 'var(--m-text)',
                  borderRadius: 2,
                  borderLeft: it.ochre ? '2px solid var(--m-ochre)' : '',
                  lineHeight: 1.3,
                }}>{it.t}</div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-2">
        <div>
          <SecLabel>Intentions · Q4</SecLabel>
          <div className="panel">
            {INTENTIONS.map((it, i, a) => (
              <div key={i} style={{ padding: '16px 20px', borderBottom: i === a.length - 1 ? 0 : '1px solid var(--m-rule-soft)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <div style={{ fontFamily: 'var(--m-display)', fontSize: 15, color: 'var(--m-ink)' }}>{it.t}</div>
                  <div className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--m-muted)' }}>{it.p}</div>
                </div>
                <div style={{ height: 2, background: 'var(--m-surface-3)', marginTop: 6, borderRadius: 1 }}>
                  <div style={{ height: '100%', width: it.p, background: it.ok ? 'var(--m-ok)' : it.warn ? 'var(--m-ochre)' : 'var(--m-accent)' }}/>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <SecLabel>Notes from the planner</SecLabel>
          <div className="panel panel-pad" style={{ padding: '22px 24px' }}>
            <div className="ed" style={{ fontSize: 15, marginBottom: 12 }}>
              <em>The Frege's-puzzle thread</em> is drifting — three weeks open, no recent addition. Retire, pause, or fold into the Kripke essay?
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn--sec btn--caps">Retire</button>
              <button className="btn btn--sec btn--caps">Pause</button>
              <button className="btn btn--primary btn--caps">Fold in</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HorizonCard({ label, title, body, progress, meta }) {
  return (
    <div className="panel panel-pad" style={{ padding: '22px 24px' }}>
      <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.2em', color: 'var(--m-accent)', marginBottom: 10 }}>{label}</div>
      <div style={{ fontFamily: 'var(--m-display)', fontSize: 20, fontWeight: 500, color: 'var(--m-ink)', lineHeight: 1.25, marginBottom: 8 }}>{title}</div>
      <div className="ed" style={{ fontSize: 14, marginBottom: 16 }}>{body}</div>
      <div style={{ height: 2, background: 'var(--m-surface-3)', borderRadius: 1 }}>
        <div style={{ height: '100%', width: `${progress*100}%`, background: 'var(--m-accent)' }}/>
      </div>
      <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--m-muted)', marginTop: 8 }}>{meta}</div>
    </div>
  );
}

const WEEK_ITEMS = [
  [{t:'Essay opening'},{t:'Read · Kripke'}],
  [{t:'Essay draft'},{t:'Lunch · H.'}],
  [{t:'Editing pass'}],
  [{t:'Middle section',accent:true},{t:'Laurent · 14:00',ochre:true},{t:'Peirce reply'}],
  [{t:'Closing pass'},{t:'Reading group'}],
  [{t:'Rest'}],
  [{t:'Plan week 47'}],
];

const INTENTIONS = [
  { t: 'Finish the three essays on naming', p: '66%' },
  { t: 'Read Putnam, "Meaning of Meaning"', p: '40%' },
  { t: 'Submit the Peirce reply to Laurent', p: '85%', ok: true },
  { t: 'Close the Indexicals thread', p: '15%', warn: true },
];

window.PlannerSurface = PlannerSurface;
