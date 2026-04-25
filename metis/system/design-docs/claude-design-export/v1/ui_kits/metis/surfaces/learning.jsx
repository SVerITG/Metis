// Surface 07 — Learning
function LearningSurface() {
  return (
    <div className="page">
      <PageHead current="learning" right={<div className="page-meta"><div>6 COURSES · 48 CARDS DUE · STREAK · 22 DAYS</div></div>}/>
      <div className="grid grid-3" style={{ marginBottom: 32 }}>
        <div className="panel panel-pad" style={{ padding: '26px 28px', gridColumn: '1 / 3' }}>
          <Kicker kind="accent"><Ico name="card"/><span>SPACED REPETITION · 48 DUE TODAY</span></Kicker>
          <h2 style={{fontFamily:'var(--m-display)', fontSize:24, fontWeight:500, letterSpacing:'-0.015em', margin:'10px 0 8px', color:'var(--m-ink)'}}>
            Begin the morning's twenty.
          </h2>
          <p className="ed" style={{ fontSize:15, margin:'0 0 20px', maxWidth: 560 }}>
            Twenty cards first, <em>then</em> the essay. Metis has pruned duplicates and sorted by what lapsed longest.
          </p>
          <div style={{ display:'flex', alignItems:'center', gap: 14, padding:'14px 16px', background: 'var(--m-bg)', border: '1px solid var(--m-rule)', borderRadius: 2, marginBottom: 14 }}>
            <div style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.22em', color:'var(--m-muted)' }}>01 / 20</div>
            <div style={{ flex:1, fontFamily:'var(--m-display)', fontSize:17, color:'var(--m-ink)' }}>
              What does Kripke mean by <em>rigid designation?</em>
            </div>
            <div style={{ display:'flex', gap:4 }}>
              <button className="btn btn--sec btn--caps" style={{ padding:'4px 10px' }}>Again</button>
              <button className="btn btn--sec btn--caps" style={{ padding:'4px 10px' }}>Hard</button>
              <button className="btn btn--sec btn--caps" style={{ padding:'4px 10px', borderColor:'var(--m-accent)', color:'var(--m-accent)' }}>Good</button>
              <button className="btn btn--ghost btn--caps" style={{ padding:'4px 10px' }}>Easy</button>
            </div>
          </div>
          <div className="tnum" style={{ fontFamily:'var(--m-mono)', fontSize:11, letterSpacing:'0.14em', color:'var(--m-muted)' }}>
            NEW · 8 &nbsp;&nbsp; LEARNING · 14 &nbsp;&nbsp; REVIEW · 26
          </div>
        </div>

        <div className="panel panel-pad" style={{ padding: '22px 24px' }}>
          <Kicker><Ico name="clock"/><span>STREAK · 22 DAYS</span></Kicker>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 4, margin: '14px 0 10px' }}>
            {Array.from({ length: 40 }).map((_, i) => (
              <div key={i} style={{
                aspectRatio: '1 / 1',
                background: i < 22 ? 'var(--m-accent)' : i === 22 ? 'var(--m-ochre)' : 'var(--m-surface-3)',
                opacity: i < 22 ? (0.4 + (i/22)*0.6) : 1,
                borderRadius: 1,
              }}/>
            ))}
          </div>
          <div style={{ fontFamily: 'var(--m-display)', fontStyle: 'italic', fontSize: 13, color: 'var(--m-muted)' }}>
            Since the 23<sup>rd</sup> of October. <em>Don't break it;</em> don't gamify it either.
          </div>
        </div>
      </div>

      <SecLabel tail="SIX COURSES · FOUR ACTIVE">Courses</SecLabel>
      <div className="grid grid-3">
        {[
          { tag:'PHILOSOPHY', t:'Naming, Necessity, Sense', by:'After Kripke, Frege, Putnam', p:0.42, due:12, kind:'accent' },
          { tag:'LOGIC', t:'Modal logic, gently', by:'Self-designed · Priest text', p:0.18, due:8 },
          { tag:'LANGUAGE', t:'Italian · B1', by:'Duolingo import · 14 wks', p:0.66, due:14, kind:'ochre' },
          { tag:'HISTORY', t:'The long 19th century', by:'Hobsbawm · Bayly', p:0.08, due:0, paused:true },
          { tag:'WRITING', t:'Practice · 500 words/day', by:'Internal course · streak', p:0.80, due:0, kind:'accent' },
          { tag:'MUSIC', t:'Ear training, basic intervals', by:'Self-designed', p:0.25, due:14 },
        ].map((c, i) => (
          <div key={i} className="panel panel-pad" style={{ padding: '20px 22px', opacity: c.paused ? 0.55 : 1 }}>
            <div style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.2em', color: c.kind === 'ochre' ? 'var(--m-ochre-deep)' : 'var(--m-accent)', marginBottom:8 }}>{c.tag}</div>
            <div style={{ fontFamily:'var(--m-display)', fontSize:18, fontWeight:500, color:'var(--m-ink)', marginBottom:4, letterSpacing:'-0.01em' }}>{c.t}</div>
            <div style={{ fontFamily:'var(--m-display)', fontStyle:'italic', fontSize:13, color:'var(--m-muted)', marginBottom:16 }}>{c.by}</div>
            <div style={{ height:2, background:'var(--m-surface-3)', borderRadius:1 }}>
              <div style={{ height:'100%', width: `${c.p*100}%`, background: c.kind === 'ochre' ? 'var(--m-ochre)' : 'var(--m-accent)' }}/>
            </div>
            <div style={{ display:'flex', justifyContent:'space-between', marginTop:8, fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color:'var(--m-muted)' }}>
              <span>{Math.round(c.p*100)}%</span>
              <span>{c.paused ? 'PAUSED' : c.due > 0 ? `${c.due} DUE` : 'CAUGHT UP'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
window.LearningSurface = LearningSurface;
