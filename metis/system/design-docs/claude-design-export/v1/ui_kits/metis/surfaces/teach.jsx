// Surface 08 — Teach (drafts outward)
function TeachSurface() {
  return (
    <div className="page" style={{ maxWidth: 1180 }}>
      <PageHead current="teach" right={<div className="page-meta"><div>3 DRAFTS · 1 PUBLISHED · 2 IN THE DRAWER</div></div>}/>
      <div className="grid" style={{ gridTemplateColumns: '1.6fr 1fr', gap: 32 }}>
        <div>
          <SecLabel tail="IN PROGRESS · 1 120 / ~1 800 WORDS">The Thursday essay</SecLabel>
          <div className="panel" style={{ padding: '40px 56px' }}>
            <div style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.22em', color:'var(--m-muted)', marginBottom:24 }}>DRAFT · NOV 08 → NOV 14 · FOR THE REVIEW</div>
            <h1 style={{ fontFamily:'var(--m-display)', fontSize:36, fontWeight:500, letterSpacing:'-0.02em', color:'var(--m-ink)', lineHeight:1.15, margin:'0 0 10px' }}>
              The name holds; the description travels
            </h1>
            <div style={{ fontFamily:'var(--m-display)', fontStyle:'italic', fontSize:18, color:'var(--m-muted)', marginBottom:32 }}>
              On Kripke, Peirce, and why the morning star keeps returning.
            </div>
            <div style={{ fontFamily:'var(--m-display)', fontSize:17, lineHeight:1.7, color:'var(--m-text)' }}>
              <p style={{ margin:'0 0 1em' }}>
                A name, Kripke tells us, is <em>rigid</em>. It picks out the same thing in every possible world in which that thing exists. To say "Hesperus" is to reach for Venus — not for <em>some</em> bright evening star, but for this one, the one we baptized.
              </p>
              <p style={{ margin:'0 0 1em' }}>
                A description, by contrast, <span style={{ background: 'var(--m-highlight)', padding:'0 2px' }}>travels</span>. "The evening star" means different things in worlds where the evening star is a different body, and nothing where there is no evening star at all.
              </p>
              <p style={{ margin:'0 0 1em', color: 'var(--m-muted-soft)', position: 'relative' }}>
                [MIDDLE SECTION · in progress]
                <span style={{ position:'absolute', right: -240, top: 0, width: 220, fontFamily:'var(--m-display)', fontStyle:'italic', fontSize:13, color: 'var(--m-accent)', lineHeight: 1.4, borderLeft: '2px solid var(--m-accent)', paddingLeft: 10 }}>
                  Metis · The turn from Peirce to Kripke wants a sentence of air. Consider a one-line epigraph here, or a sparer paragraph.
                </span>
              </p>
              <p style={{ margin:'0 0 1em' }}>
                For Peirce, the same star sits in a different question. Not <em>what does the name hold onto</em>, but <em>what does the sign do in a mind</em>. The interpretant is not a further term on the line; it is the effect, the turn, the small inner click. The name insists; the sign <em>happens</em>.
              </p>
              <p style={{ margin:0, color: 'var(--m-muted)' }}>
                [continue: the essay's turn, then the close]
              </p>
            </div>

            <div style={{ marginTop: 32, paddingTop: 18, borderTop: '1px solid var(--m-rule)', display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color:'var(--m-muted)' }}>SAVED · 07:12 · VERSION 12</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn--ghost btn--caps">Versions</button>
                <button className="btn btn--sec btn--caps">Read-through</button>
                <button className="btn btn--primary btn--caps">Publish</button>
              </div>
            </div>
          </div>
        </div>

        <div>
          <SecLabel>All pieces</SecLabel>
          <div className="panel">
            {[
              { t:'The name holds; the description travels', s:'Draft · this week', k:'accent', on:true, pct:62 },
              { t:'On Frege\'s puzzle, for a general reader', s:'Draft · in the drawer', k:'ochre', pct:30 },
              { t:'Against the indexical as an afterthought', s:'Outline · in the drawer', k:'ochre', pct:10 },
              { t:'Why Kripke still matters', s:'Published · June', k:'ok', pct:100 },
            ].map((p,i,a) => (
              <div key={i} style={{ padding:'16px 20px', borderBottom: i===a.length-1?0:'1px solid var(--m-rule-soft)', borderLeft: p.on ? '2px solid var(--m-accent)' : '2px solid transparent', background: p.on ? 'var(--m-accent-wash)' : 'transparent' }}>
                <div style={{ fontFamily:'var(--m-display)', fontSize:15, color:'var(--m-ink)', lineHeight:1.3, marginBottom:4 }}>{p.t}</div>
                <div style={{ fontFamily:'var(--m-mono)', fontSize:10, letterSpacing:'0.14em', color: p.k === 'ok' ? 'var(--m-ok)' : p.k === 'ochre' ? 'var(--m-ochre-deep)' : 'var(--m-accent)', textTransform:'uppercase' }}>{p.s}</div>
              </div>
            ))}
          </div>
          <SecLabel>Suggested next</SecLabel>
          <div className="panel panel-pad" style={{ padding: '18px 20px' }}>
            <div className="ed" style={{ fontSize: 14 }}>
              The Frege's-puzzle draft has been in the drawer for thirty-two days. <em>Retire, or reopen after the Thursday essay ships.</em>
            </div>
            <div style={{ display:'flex', gap:6, marginTop:12 }}>
              <button className="btn btn--sec btn--caps">Reopen later</button>
              <button className="btn btn--ghost btn--caps">Retire</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
window.TeachSurface = TeachSurface;
