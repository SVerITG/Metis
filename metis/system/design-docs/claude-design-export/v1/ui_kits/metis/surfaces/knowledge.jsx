// Surface 02 — Knowledge
// Personal library. Slipcases (collections), index cards, sources.

function KnowledgeSurface() {
  return (
    <div className="page">
      <PageHead current="knowledge" right={
        <div className="page-meta"><div>240 CARDS · 14 SLIPCASES · 6 SOURCES ADDED THIS WEEK</div></div>
      }/>

      <div className="grid" style={{ gridTemplateColumns: '240px 1fr', gap: 32, marginBottom: 32 }}>
        <div>
          <SecLabel>Slipcases</SecLabel>
          <div className="panel" style={{ overflow: 'hidden' }}>
            {SLIPCASES.map((s, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px',
                borderBottom: i === SLIPCASES.length - 1 ? 'none' : '1px solid var(--m-rule-soft)',
                borderLeft: s.active ? '2px solid var(--m-accent)' : '2px solid transparent',
                background: s.active ? 'var(--m-accent-wash)' : 'transparent',
                cursor: 'pointer',
                fontSize: 13,
                color: s.active ? 'var(--m-ink)' : 'var(--m-text)',
                fontFamily: 'var(--m-display)',
              }}>
                <span>{s.name}</span>
                <span className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.12em', color: 'var(--m-muted)' }}>{s.count}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--m-muted)', padding: '0 4px' }}>
            ADD SLIPCASE · ⌘⇧N
          </div>
        </div>

        <div>
          <SecLabel tail="SORT · LAST TOUCHED">Philosophy / Language</SecLabel>
          <div className="panel" style={{ padding: '20px 24px', marginBottom: 16 }}>
            <Kicker><Ico name="book" /><span>SLIPCASE · 62 CARDS · 8 SOURCES</span></Kicker>
            <h3 style={{ fontFamily: 'var(--m-display)', fontSize: 24, fontWeight: 500, margin: '10px 0 6px', color: 'var(--m-ink)' }}>Philosophy of Language</h3>
            <p className="ed" style={{ margin: 0, fontSize: 15 }}>
              Reading around <em>names, descriptions, and the things they hold onto.</em> Warm threads: rigid designation, the interpretant, Frege's puzzle.
            </p>
          </div>

          <div className="grid grid-3">
            {CARDS.map((c, i) => <IndexCard key={i} {...c} />)}
          </div>
        </div>
      </div>

      <SecLabel tail="IN THE HAND">Sources · recently clipped</SecLabel>
      <div className="panel">
        {SOURCES.map((s, i) => (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: '100px 1fr 140px 100px',
            gap: 20, alignItems: 'center',
            padding: '14px 24px',
            borderBottom: i === SOURCES.length - 1 ? 'none' : '1px solid var(--m-rule-soft)',
          }}>
            <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.18em', color: s.tagColor, textTransform: 'uppercase' }}>{s.tag}</div>
            <div>
              <div style={{ fontFamily: 'var(--m-display)', fontSize: 16, color: 'var(--m-ink)' }}>{s.title}</div>
              <div style={{ fontFamily: 'var(--m-display)', fontStyle: 'italic', fontSize: 13, color: 'var(--m-muted)', marginTop: 2 }}>{s.by}</div>
            </div>
            <div className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 11, color: 'var(--m-muted)' }}>{s.when}</div>
            <div style={{ textAlign: 'right' }}>
              <Chip kind="mute" plain>{s.highlights} HL</Chip>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const SLIPCASES = [
  { name: 'Philosophy / Language', count: 62, active: true },
  { name: 'Philosophy / Mind', count: 41 },
  { name: 'Writing · practice', count: 28 },
  { name: 'Reading group', count: 19 },
  { name: 'History of science', count: 24 },
  { name: 'Mathematics / set theory', count: 14 },
  { name: 'Poetry', count: 22 },
  { name: 'Unfiled', count: 30 },
];

const CARDS = [
  { date: '14 NOV', kicker: 'NOTE', title: 'Rigid designators hold across worlds', body: <>Kripke, <em>N&amp;N</em>, p. 48. The designator picks out the same object in every world where it exists — it is not a <em>de dicto</em> description.</>, tag: 'Kripke', tagKind: 'accent' },
  { date: '13 NOV', kicker: 'HIGHLIGHT', title: 'Hesperus and Phosphorus, again', body: <>The example Peirce and Kripke both reach for. <em>Same evidence, different questions.</em></>, tag: 'Frege' },
  { date: '12 NOV', kicker: 'NOTE', title: 'Descriptivism as fall-back', body: <>When the name fails, description does the work. But the work is different — the name <em>insists</em>, description <em>identifies.</em></>, tag: 'Kripke' },
  { date: '11 NOV', kicker: 'QUESTION', title: 'Does the interpretant nest?', body: <>If every sign generates an interpretant which is itself a sign — <em>where does that terminate?</em></>, tag: 'Peirce', tagKind: 'ochre' },
  { date: '10 NOV', kicker: 'CLIP', title: 'Frege\'s puzzle — the canonical form', body: <>The puzzle is not about the referent; it is about <em>cognitive value.</em> Two names for Venus, two different lights.</>, tag: 'Frege' },
  { date: '08 NOV', kicker: 'NOTE', title: 'Why "natural kind" is doing heavy lifting', body: <>Kripke's argument extends from names to kinds — but kinds are <em>not</em> individuals, and this is where Putnam steps in.</>, tag: 'Putnam' },
];

function IndexCard({ date, kicker, title, body, tag, tagKind = 'accent' }) {
  return (
    <div className="panel" style={{ padding: '18px 20px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
        <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.18em', color: 'var(--m-muted)' }}>{date} · {kicker}</div>
        <Chip kind={tagKind} plain>{tag}</Chip>
      </div>
      <div style={{ fontFamily: 'var(--m-display)', fontSize: 16, fontWeight: 500, color: 'var(--m-ink)', lineHeight: 1.3, marginBottom: 8 }}>{title}</div>
      <div className="ed" style={{ fontSize: 13, color: 'var(--m-text)', margin: 0 }}>{body}</div>
    </div>
  );
}

const SOURCES = [
  { tag: 'BOOK',    tagColor: 'var(--m-accent)', title: 'Naming and Necessity', by: 'Saul Kripke · 1980 · Harvard UP', when: '14 NOV · 14:22', highlights: 12 },
  { tag: 'PAPER',   tagColor: 'var(--m-info)',   title: 'On Sense and Reference', by: 'Gottlob Frege · 1892 · trans. Geach', when: '12 NOV · 09:08', highlights: 8 },
  { tag: 'LECTURE', tagColor: 'var(--m-ochre-deep)', title: 'Peirce on signs — Part II', by: 'C. Hookway · Oxford, 2019', when: '10 NOV · 19:45', highlights: 5 },
  { tag: 'ESSAY',   tagColor: 'var(--m-accent)', title: 'The Meaning of "Meaning"', by: 'Hilary Putnam · 1975', when: '08 NOV · 11:30', highlights: 9 },
];

window.KnowledgeSurface = KnowledgeSurface;
