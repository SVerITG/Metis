// Surface 06 — Meetings
function MeetingsSurface() {
  return (
    <div className="page">
      <PageHead current="meetings" right={<div className="page-meta"><div>2 TODAY · 3 THIS WEEK · 1 PREPPED</div></div>}/>
      <div className="grid grid-main" style={{ gap: 28 }}>
        <div>
          <SecLabel tail="PREPPED · 14:00 TODAY">M. Laurent · reading group</SecLabel>
          <div className="panel" style={{ padding: '28px 32px', marginBottom: 18 }}>
            <Kicker kind="ochre"><Ico name="clock"/><span>THU 14 NOV · 14:00 — 14:30 · MET. LAURENT</span></Kicker>
            <h2 style={{ fontFamily:'var(--m-display)', fontSize:26, fontWeight:500, letterSpacing:'-0.018em', margin:'10px 0 10px', color:'var(--m-ink)' }}>
              Reading group — Kripke, lectures I–II
            </h2>
            <p className="ed" style={{ fontSize:15, maxWidth:640, marginBottom:18 }}>
              M. Laurent has read through lecture II. She has a disagreement about the role of <em>a priori</em> knowledge in the baptism case. <em>Metis flagged it in her last email.</em>
            </p>
            <SecLabel>One-pager</SecLabel>
            <ul style={{ margin:0, padding:0, listStyle:'none', fontFamily:'var(--m-display)', fontSize:15, color:'var(--m-text)', lineHeight: 1.9 }}>
              <li>· Agree on what "rigid" means before arguing about descriptions.</li>
              <li>· Hesperus / Phosphorus — <em>do not rehash;</em> M. knows it.</li>
              <li>· M.'s objection: a priori necessity vs. a posteriori necessity.</li>
              <li>· Open with Kripke's own concession on p. 56 — good-faith framing.</li>
              <li>· If time: the Putnam thread. Otherwise next week.</li>
            </ul>
            <div style={{ display:'flex', gap:6, marginTop: 22, paddingTop:18, borderTop:'1px solid var(--m-rule)'}}>
              <button className="btn btn--primary">Open one-pager</button>
              <button className="btn btn--sec btn--caps">Transcript (after)</button>
              <button className="btn btn--ghost btn--caps">Reschedule</button>
            </div>
          </div>
          <SecLabel>Transcripts · recent</SecLabel>
          <div className="panel">
            {[
              { d:'07 NOV', t:'M. Laurent · reading group', mins:'32 MIN', follow: '3 follow-ups' },
              { d:'05 NOV', t:'C. Hookway · office hour (Zoom)', mins:'58 MIN', follow: '1 follow-up' },
              { d:'01 NOV', t:'Editorial — essay pitch, interim', mins:'22 MIN', follow: 'filed' },
            ].map((m,i,a)=>(
              <div key={i} style={{ display:'grid', gridTemplateColumns:'80px 1fr 100px 140px', gap:16, padding:'14px 22px', borderBottom: i===a.length-1?0:'1px solid var(--m-rule-soft)', alignItems:'center' }}>
                <div style={{fontFamily:'var(--m-mono)', fontSize:11, letterSpacing:'0.16em', color:'var(--m-muted)'}}>{m.d}</div>
                <div style={{fontFamily:'var(--m-display)', fontSize:15, color:'var(--m-ink)'}}>{m.t}</div>
                <div className="tnum" style={{fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color:'var(--m-muted)'}}>{m.mins}</div>
                <div style={{textAlign:'right'}}><Chip kind="mute" plain>{m.follow.toUpperCase()}</Chip></div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <SecLabel>Week ahead</SecLabel>
          <div className="panel">
            {[
              {d:'THU · 14:00',t:'M. Laurent · reading',k:'NOW', ochre:true},
              {d:'FRI · 10:30',t:'Essay editor — call',k:''},
              {d:'MON · 09:00',t:'C. Hookway · office',k:''},
            ].map((m,i,a)=>(
              <div key={i} style={{padding:'14px 18px', borderBottom: i===a.length-1?0:'1px solid var(--m-rule-soft)', borderLeft: m.ochre?'2px solid var(--m-ochre)':'2px solid transparent'}}>
                <div style={{fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.2em', color: m.ochre ? 'var(--m-ochre-deep)':'var(--m-muted)', marginBottom:4}}>{m.d}{m.k && ' · '+m.k}</div>
                <div style={{fontFamily:'var(--m-display)', fontSize:14, color:'var(--m-ink)'}}>{m.t}</div>
              </div>
            ))}
          </div>

          <SecLabel>Open follow-ups</SecLabel>
          <div className="panel" style={{padding:'16px 20px'}}>
            <div className="ed" style={{ fontSize: 14, marginBottom: 10 }}>
              From <em>07 Nov · reading group:</em>
            </div>
            <ul style={{margin:0, paddingLeft:18, fontFamily:'var(--m-display)', fontSize:14, color:'var(--m-text)', lineHeight:1.7}}>
              <li>Send M. the Putnam reading <Chip kind="warn" plain>2D OVERDUE</Chip></li>
              <li>Confirm next date — Nov 21 or 28</li>
              <li>File Hookway's epigraph idea</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
window.MeetingsSurface = MeetingsSurface;
