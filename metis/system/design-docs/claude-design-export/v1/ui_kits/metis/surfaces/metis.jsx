// Surface 09 — Metis (settings: model, memory, keys, billing)
function MetisSurface() {
  return (
    <div className="page" style={{ maxWidth: 1180 }}>
      <PageHead current="metis" right={<div className="page-meta"><div>STAN · READER IN RESIDENCE</div><div style={{marginTop:4, color:'var(--m-muted-soft)'}}>SIGNED IN · 14 NOV</div></div>}/>

      <div className="grid" style={{ gridTemplateColumns: '220px 1fr', gap: 40 }}>
        <div>
          {[
            { id: 'model', label: 'Model' , on: true },
            { id: 'memory', label: 'Memory & archive' },
            { id: 'keys', label: 'Keys & identity' },
            { id: 'connections', label: 'Connections' },
            { id: 'appearance', label: 'Appearance' },
            { id: 'billing', label: 'Billing' },
            { id: 'about', label: 'About Metis' },
          ].map(s => (
            <div key={s.id} style={{
              padding: '10px 14px',
              borderLeft: s.on ? '2px solid var(--m-accent)' : '2px solid transparent',
              background: s.on ? 'var(--m-accent-wash)' : 'transparent',
              color: s.on ? 'var(--m-ink)' : 'var(--m-muted)',
              fontFamily: 'var(--m-display)', fontSize: 14,
              cursor: 'pointer', borderRadius: 2,
            }}>{s.label}</div>
          ))}
        </div>

        <div>
          <SecLabel tail="CHOOSE YOUR HAND">Model</SecLabel>
          <div className="grid grid-3" style={{ marginBottom: 28 }}>
            {[
              { name:'Haiku', v:'4.5', use:'Fast marginal notes, tagging, small answers.', chip:'haiku', on:false },
              { name:'Sonnet', v:'4.5', use:'The default. Reading, replying, writing with you.', chip:'sonnet', on:true },
              { name:'Opus', v:'4.1', use:'Long reasoning, book-length threads, careful arguments.', chip:'opus', on:false },
            ].map((m,i) => (
              <div key={i} className="panel panel-pad" style={{ padding:'22px 24px', borderColor: m.on ? 'var(--m-accent)' : 'var(--m-rule)', borderLeftWidth: m.on?2:1, borderLeftColor: m.on ? 'var(--m-accent)' : 'var(--m-rule)' }}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:8}}>
                  <div style={{ fontFamily:'var(--m-display)', fontSize:22, fontWeight:500, color:'var(--m-ink)' }}>{m.name}</div>
                  <Chip kind={m.chip} plain>{m.v}</Chip>
                </div>
                <div className="ed" style={{ fontSize:13, margin:0, minHeight:52 }}>{m.use}</div>
                <div style={{ marginTop: 14, paddingTop: 12, borderTop:'1px solid var(--m-rule-soft)', fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color: m.on ? 'var(--m-accent)' : 'var(--m-muted)' }}>{m.on ? '· SELECTED' : 'USE'}</div>
              </div>
            ))}
          </div>

          <SecLabel>Memory & archive</SecLabel>
          <div className="panel" style={{ marginBottom: 28 }}>
            <SettingRow label="Remember across threads" help="Metis keeps a compact index of what you've filed and what you've said. No raw chats stored." value={<Toggle on/>}/>
            <SettingRow label="Archive after" help="How long an untouched thread stays open before it's filed." value={<Select value="30 days"/>}/>
            <SettingRow label="Cards per review queue" help="The default size of a spaced-repetition session." value={<Select value="20"/>}/>
            <SettingRow label="Export the archive" help="A zip of your notes, threads, sources. Monthly or on demand." value={<button className="btn btn--sec btn--caps">Export · 142 MB</button>} last/>
          </div>

          <SecLabel>Appearance</SecLabel>
          <div className="panel" style={{ marginBottom: 28 }}>
            <SettingRow label="Theme" help="Archive (light) for the reading room; Observatory for the lamp at night." value={
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn--sec btn--caps" style={{ padding: '5px 12px', borderColor:'var(--m-accent)', color:'var(--m-accent)' }}>Archive</button>
                <button className="btn btn--sec btn--caps" style={{ padding: '5px 12px' }}>Observatory</button>
                <button className="btn btn--ghost btn--caps" style={{ padding: '5px 12px' }}>Follow system</button>
              </div>
            }/>
            <SettingRow label="Display family" help="Newsreader, set. You can swap it here if you prefer something else from the same mood." value={<Select value="Newsreader"/>} last/>
          </div>

          <SecLabel>Identity</SecLabel>
          <div className="panel" style={{ padding: '18px 22px', marginBottom: 24 }}>
            <div style={{ display:'flex', alignItems:'center', gap:16 }}>
              <div style={{ width:52, height:52, borderRadius:'50%', background:'var(--m-surface-2)', border:'1px solid var(--m-rule)', display:'inline-flex', alignItems:'center', justifyContent:'center', fontFamily:'var(--m-display)', fontSize:22, fontWeight:500, color:'var(--m-accent)' }}>S</div>
              <div>
                <div style={{ fontFamily:'var(--m-display)', fontSize:17, color:'var(--m-ink)' }}>Researcher</div>
                <div style={{ fontFamily:'var(--m-display)', fontStyle:'italic', fontSize:13, color:'var(--m-muted)' }}>stan@metis.local · reader in residence since June 2024</div>
              </div>
              <div style={{ marginLeft:'auto', display:'flex', gap:6 }}>
                <button className="btn btn--ghost btn--caps">Rename</button>
                <button className="btn btn--sec btn--caps">Keys</button>
              </div>
            </div>
          </div>

          <div style={{ fontFamily:'var(--m-display)', fontStyle:'italic', fontSize:14, color:'var(--m-muted)', padding: '8px 4px' }}>
            <em>Metis · Archive edition · v1.0.</em> Built slowly, for one reader.
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingRow({ label, help, value, last }) {
  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr 240px', gap: 24, alignItems:'center', padding:'18px 22px', borderBottom: last ? 'none' : '1px solid var(--m-rule-soft)' }}>
      <div>
        <div style={{ fontFamily:'var(--m-display)', fontSize:15, color:'var(--m-ink)' }}>{label}</div>
        <div style={{ fontSize:12, color:'var(--m-muted)', marginTop:2 }}>{help}</div>
      </div>
      <div style={{ textAlign:'right' }}>{value}</div>
    </div>
  );
}
function Toggle({ on }) {
  return (
    <div style={{ display:'inline-flex', alignItems:'center', gap:8 }}>
      <div style={{ width: 34, height: 18, borderRadius: 12, background: on ? 'var(--m-accent)' : 'var(--m-surface-3)', position:'relative', transition: '0.2s' }}>
        <div style={{ position:'absolute', top: 2, left: on ? 18 : 2, width: 14, height: 14, borderRadius: '50%', background: 'var(--m-surface)', border: '1px solid var(--m-rule)', transition: '0.2s' }}/>
      </div>
      <span style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color: on ? 'var(--m-accent)' : 'var(--m-muted)' }}>{on?'ON':'OFF'}</span>
    </div>
  );
}
function Select({ value }) {
  return (
    <div style={{ display:'inline-flex', alignItems:'center', gap:8, padding:'6px 12px', background:'var(--m-surface)', border:'1px solid var(--m-rule-strong)', borderRadius:2, fontFamily:'var(--m-ui)', fontSize:13, color:'var(--m-ink)' }}>
      <span>{value}</span>
      <Ico name="chev" />
    </div>
  );
}
window.MetisSurface = MetisSurface;
