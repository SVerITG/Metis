// Surface 03 — Thinking (the flagship: dialogue + marginalia)
function ThinkingSurface() {
  return (
    <div className="page" style={{ maxWidth: 1180 }}>
      <PageHead current="thinking" right={
        <div className="page-meta"><div>3 OPEN · 28 ARCHIVED THIS MONTH</div><div style={{marginTop:4,color:'var(--m-muted-soft)'}}>MODEL · SONNET 4.5 · REASONING</div></div>
      }/>
      <div className="grid" style={{ gridTemplateColumns: '220px 1fr 240px', gap: 28 }}>
        <div>
          <SecLabel>Open threads</SecLabel>
          <div className="panel">
            {[
              { t: 'Kripke on rigid designators', d: '2d', on: true },
              { t: 'Peirce — interpretant', d: '1d' },
              { t: 'Frege\'s puzzle, revisited', d: '3d' },
              { t: 'Indexicals (paused)', d: '9d', muted: true },
            ].map((th, i, a) => (
              <div key={i} style={{
                padding: '14px 16px',
                borderBottom: i === a.length - 1 ? 0 : '1px solid var(--m-rule-soft)',
                borderLeft: th.on ? '2px solid var(--m-accent)' : '2px solid transparent',
                background: th.on ? 'var(--m-accent-wash)' : 'transparent',
                opacity: th.muted ? 0.55 : 1,
                cursor: 'pointer',
              }}>
                <div style={{ fontFamily: 'var(--m-display)', fontSize: 14, color: 'var(--m-ink)', lineHeight: 1.3 }}>{th.t}</div>
                <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--m-muted)', marginTop: 4 }}>{th.d} · OPEN</div>
              </div>
            ))}
          </div>
          <button className="btn btn--sec btn--caps" style={{ marginTop: 12, width: '100%', justifyContent: 'center' }}>+ New thread</button>
        </div>

        <div>
          <div className="panel" style={{ padding: '28px 36px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 18, paddingBottom: 12, borderBottom: '1px solid var(--m-rule)' }}>
              <div>
                <Kicker kind="accent"><Ico name="thread"/><span>THINKING · ACTIVE</span><span>·</span><span style={{color:'var(--m-ochre-deep)'}}>2d OPEN</span></Kicker>
                <h2 style={{ fontFamily: 'var(--m-display)', fontSize: 28, fontWeight: 500, letterSpacing: '-0.018em', color: 'var(--m-ink)', margin: '8px 0 0' }}>Kripke's rigid designators</h2>
              </div>
              <Chip kind="sonnet" plain>Sonnet 4.5</Chip>
            </div>

            <Turn who="STAN · 07:12" body={<>I'm stuck on why rigid designation isn't just a strong description. If "Hesperus" picks out Venus in every world Venus exists in, isn't that what "the evening star" does too?</>}/>
            <Turn who="METIS · 07:12" metis body={<>The description shifts with the world. In a world where Venus rose in the morning and not the evening, <em>"the evening star"</em> picks out something else — or nothing. <em>"Hesperus"</em> still picks out Venus. The name holds; the description travels.</>}/>
            <Turn who="STAN · 07:13" body={<>So the name is indexed to <em>this</em> Venus, not to what Venus does.</>}/>
            <Turn who="METIS · 07:13" metis body={<>Exactly. Kripke's baptism: a name fastens, once, to a particular. The causal-historical chain carries it forward; possible worlds don't shake it loose.</>}/>
            <Turn who="STAN · 07:14" body={<>Where does Peirce's interpretant fit in here?</>}/>
            <Turn who="METIS · 07:14" metis body={<>Differently, I think. Peirce is asking what a sign <em>does</em> in a mind — Kripke, what a name <em>is</em>, across worlds. The morning-star example is the same mineral; they're mining for different metals. <em>Shall I open a branch thread on that?</em></>}/>

            <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--m-rule)' }}>
              <div className="m-cmd" style={{ background: 'var(--m-bg)', border: '1px solid var(--m-rule-strong)', borderRadius: 2, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--m-display)', fontSize: 15, fontStyle: 'italic', color: 'var(--m-muted)' }}>
                <span style={{ color: 'var(--m-accent)', fontFamily: 'var(--m-mono)', fontStyle: 'normal', fontSize: 13 }}>›</span>
                <span>Reply, or ask Metis to branch this thread…</span>
                <span style={{ marginLeft: 'auto', fontFamily: 'var(--m-mono)', fontStyle: 'normal', fontSize: 10, letterSpacing: '0.16em', color: 'var(--m-muted-soft)' }}>⌘↵</span>
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                <button className="btn btn--ghost btn--caps">Branch</button>
                <button className="btn btn--ghost btn--caps">File to Knowledge</button>
                <button className="btn btn--ghost btn--caps">Export as note</button>
                <button className="btn btn--ghost btn--caps" style={{ marginLeft: 'auto', color: 'var(--m-muted)' }}>Retire thread</button>
              </div>
            </div>
          </div>
        </div>

        <div>
          <SecLabel>Marginalia</SecLabel>
          <div className="panel panel-pad" style={{ padding: '18px 20px', marginBottom: 12 }}>
            <Kicker kind="accent"><Ico name="tag"/><span>METIS · LINK</span></Kicker>
            <div className="ed" style={{ fontSize: 13, marginTop: 8 }}>
              Cross-ref added: this thread and <em>"On Peirce's interpretant"</em> now share the Hesperus example.
            </div>
          </div>
          <div className="panel panel-pad" style={{ padding: '18px 20px', marginBottom: 12, borderLeft: '2px solid var(--m-ochre)' }}>
            <Kicker kind="ochre"><Ico name="book"/><span>SOURCE · CITED</span></Kicker>
            <div style={{ fontFamily: 'var(--m-display)', fontSize: 14, fontWeight: 500, marginTop: 6, color: 'var(--m-ink)' }}>Naming and Necessity</div>
            <div style={{ fontFamily: 'var(--m-display)', fontStyle: 'italic', fontSize: 12, color: 'var(--m-muted)' }}>Kripke · pp. 48–52</div>
          </div>
          <div className="panel panel-pad" style={{ padding: '18px 20px' }}>
            <Kicker><Ico name="pen"/><span>SUGGESTED NOTE</span></Kicker>
            <div className="ed" style={{ fontSize: 13, marginTop: 8 }}>
              <em>"The name holds; the description travels."</em> — a one-line card.
            </div>
            <button className="btn btn--sec btn--caps" style={{ marginTop: 10, padding: '4px 10px' }}>File to Knowledge</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Turn({ who, body, metis }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '120px 1fr',
      gap: 24,
      padding: '18px 0',
      borderBottom: '1px solid var(--m-rule-soft)',
    }}>
      <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.2em', color: metis ? 'var(--m-accent)' : 'var(--m-muted)', paddingTop: 3 }}>{who}</div>
      <div style={{ fontFamily: 'var(--m-display)', fontSize: 16, lineHeight: 1.55, color: 'var(--m-text)' }}>{body}</div>
    </div>
  );
}

window.ThinkingSurface = ThinkingSurface;
