// Surface 05 — Work (kanban)
function WorkSurface() {
  return (
    <div className="page" style={{ maxWidth: 1320 }}>
      <PageHead current="work" right={<div className="page-meta"><div>3 PROJECTS · 14 TASKS · 2 PAUSED</div></div>}/>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, alignItems: 'center' }}>
        <Chip kind="mute" plain>ALL</Chip>
        <Chip>Essay on naming</Chip>
        <Chip kind="ochre">Reading group</Chip>
        <Chip kind="mute" plain>Site redesign</Chip>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="btn btn--sec btn--caps">+ Task</button>
          <button className="btn btn--ghost btn--caps">Group · Project</button>
        </div>
      </div>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        <Column title="Inbox" count={3} items={[
          {title:'Rename the Frege thread',tag:'Essay',mins:'5m'},
          {title:'Pull quotes from Putnam',tag:'Essay',mins:'20m'},
          {title:'Schedule reading group prep',tag:'Group',kind:'ochre',mins:'10m'},
        ]}/>
        <Column title="This week" count={6} items={[
          {title:'Middle section of Thursday essay',tag:'Essay',mins:'90m',star:true,kind:'accent'},
          {title:'Reply to M. Laurent',tag:'Group',kind:'ochre',mins:'30m'},
          {title:'Read N&N, pp. 48–62',tag:'Essay',mins:'45m'},
          {title:'Pick epigraph for opening',tag:'Essay',mins:'15m'},
          {title:'Outline the third essay',tag:'Essay',mins:'60m'},
          {title:'Tidy the Unfiled slipcase',tag:'Admin',kind:'mute',mins:'20m'},
        ]}/>
        <Column title="In progress" count={2} items={[
          {title:'Essay — middle section',tag:'Essay',mins:'1h used · 30m left',kind:'accent',bar:0.68},
          {title:'Peirce reply for Metis',tag:'Thinking',kind:'info',mins:'short'},
        ]}/>
        <Column title="Closed · this week" count={3} muted items={[
          {title:'Opening paragraph filed',tag:'Essay',mins:'Tue'},
          {title:'Kripke outline agreed',tag:'Essay',mins:'Mon'},
          {title:'Send readings to group',tag:'Group',kind:'ochre',mins:'Mon'},
        ]}/>
      </div>
    </div>
  );
}
function Column({ title, count, items, muted }) {
  return (
    <div style={{ background: 'var(--m-surface-3)', borderRadius: 3, padding: 12, opacity: muted ? 0.85 : 1 }}>
      <div style={{ display:'flex', justifyContent:'space-between', padding:'4px 8px 12px', fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.22em', textTransform:'uppercase', color:'var(--m-muted)' }}>
        <span>{title}</span><span>{count}</span>
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
        {items.map((it,i) => (
          <div key={i} style={{ background:'var(--m-surface)', border:'1px solid var(--m-rule)', borderLeft: it.kind==='accent' ? '2px solid var(--m-accent)' : it.kind==='ochre' ? '2px solid var(--m-ochre)' : it.kind==='info' ? '2px solid var(--m-info)' : '1px solid var(--m-rule)', borderRadius: 2, padding: '12px 14px' }}>
            <div style={{ display:'flex', alignItems:'baseline', justifyContent:'space-between', gap:8 }}>
              <div style={{ fontFamily:'var(--m-display)', fontSize:14, color:'var(--m-ink)', lineHeight:1.3 }}>{it.title}</div>
              {it.star && <span style={{fontSize:10, color:'var(--m-accent)'}}>★</span>}
            </div>
            <div style={{ marginTop:8, display:'flex', justifyContent:'space-between', fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.12em', color:'var(--m-muted)' }}>
              <span>{it.tag.toUpperCase()}</span><span>{it.mins}</span>
            </div>
            {it.bar != null && <div style={{height:2,background:'var(--m-surface-3)',marginTop:8,borderRadius:1}}><div style={{height:'100%',width:`${it.bar*100}%`,background:'var(--m-accent)'}}/></div>}
          </div>
        ))}
      </div>
    </div>
  );
}
window.WorkSurface = WorkSurface;
