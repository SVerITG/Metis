// Surface 01 — Today
// Morning briefing: editorial greeting, warm threads, day's cards.

function TodaySurface() {
  return (
    <div className="page">
      <PageHead current="today" right={
        <div className="page-meta">
          <div>07:12 · CALM · NO MEETINGS UNTIL 14:00</div>
          <div style={{ marginTop: 4, color: 'var(--m-muted-soft)' }}>WEATHER · GREY · 4°C</div>
        </div>
      }/>

      {/* Opening paragraph — the briefing itself */}
      <div className="panel panel-pad" style={{ padding: '32px 40px', marginBottom: 32 }}>
        <Kicker kind="accent"><Ico name="compass" /><span>MORNING BRIEFING</span><span>·</span><span style={{ color: 'var(--m-muted)' }}>A paragraph, not a dashboard</span></Kicker>
        <p className="ed" style={{ fontSize: 18, marginTop: 16, marginBottom: 14, maxWidth: 720 }}>
          Three threads from yesterday are still warm — <em>Kripke on rigid designators</em>, the draft of Thursday's essay, and a question you left open for me about Peirce. The morning is free until fourteen hundred; the Laurent meeting is prepped.
        </p>
        <p className="ed" style={{ fontSize: 16, color: 'var(--m-muted)', maxWidth: 720, marginBottom: 18 }}>
          If you'll take one thing first, <em>take the essay.</em> It is the nearest to finished.
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn--primary">Open the essay</button>
          <button className="btn btn--sec">Continue Kripke</button>
          <button className="btn btn--ghost btn--caps">Later ↓</button>
        </div>
      </div>

      <SecLabel tail="ACROSS YOUR SURFACES">Active threads</SecLabel>
      <div className="grid grid-3" style={{ marginBottom: 32 }}>
        <ThreadCard kind="thinking" days="2d" title="Kripke's rigid designators" note={<>A tension with descriptivism on p. 48. Two notes reference the <em>morning-star / evening-star</em> example.</>} meta="3 NOTES · 1 QUESTION" />
        <ThreadCard kind="draft" days="6d" title="The Thursday essay" note={<>Middle section still loose — the turn from Peirce to Kripke <em>wants a sentence of air.</em></>} meta="1 120 WORDS · 4 EDITS" />
        <ThreadCard kind="question" days="1d" title="On Peirce's interpretant" note={<>You left this for me. <em>I have a short reply in the margin.</em></>} meta="UNREAD · FROM METIS" />
      </div>

      <div className="grid grid-main" style={{ marginBottom: 32 }}>
        <div>
          <SecLabel tail="THU · 14 NOV">The day at hand</SecLabel>
          <div className="panel">
            <DayRow time="09:30" label="FOCUS" title="Essay, middle section" meta="90 MIN" accent/>
            <DayRow time="11:00" label="READ" title="Naming and Necessity — pp. 48–62" meta="45 MIN"/>
            <DayRow time="12:30" label="LUNCH" title={<span style={{ color: 'var(--m-muted)', fontStyle:'italic'}}>— protected hour —</span>} meta=""/>
            <DayRow time="14:00" label="MEETING" title="M. Laurent · reading group" meta="30 MIN" ochre/>
            <DayRow time="16:00" label="WRITE" title="Reply to the Peirce question" meta="30 MIN"/>
            <DayRow time="17:30" label="END" title={<span style={{ color: 'var(--m-muted)'}}>Close threads · file the day</span>} meta="" last/>
          </div>
        </div>
        <div>
          <SecLabel tail="ONE FOCUS">Today's single intention</SecLabel>
          <div className="panel panel-pad" style={{ padding: '24px 26px' }}>
            <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--m-accent)', marginBottom: 10 }}>THE ONE THING</div>
            <div style={{ fontFamily: 'var(--m-display)', fontSize: 24, fontWeight: 500, letterSpacing: '-0.015em', color: 'var(--m-ink)', lineHeight: 1.25, marginBottom: 12 }}>
              Finish the middle section of Thursday's essay.
            </div>
            <div className="ed" style={{ fontSize: 15, color: 'var(--m-muted)', marginBottom: 18 }}>
              From your planner, this week. <em>Everything else is optional.</em>
            </div>
            <div className="hr hr-soft" style={{ margin: '16px 0' }}/>
            <Kicker><Ico name="pen" /><span>DRAFT</span><span>·</span><span>NOV 8 → NOV 14</span></Kicker>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, alignItems: 'baseline' }}>
              <span className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 12, color: 'var(--m-muted)' }}>1 120 / ~1 800 WORDS</span>
              <button className="btn btn--primary btn--caps" style={{ padding: '5px 10px' }}>Begin</button>
            </div>
            <div style={{ height: 2, background: 'var(--m-surface-3)', marginTop: 10, borderRadius: 1 }}>
              <div style={{ height: '100%', width: '62%', background: 'var(--m-accent)', borderRadius: 1 }}/>
            </div>
          </div>
        </div>
      </div>

      <SecLabel tail="METIS · NOTES IN THE MARGIN">From the assistant</SecLabel>
      <div className="grid grid-2">
        <MarginNote title="Two threads are converging." body={<>Your Kripke note and the Peirce question both lean on the <em>morning-star / evening-star</em> pair. I've added a cross-reference from each to the other.</>} model="haiku" />
        <MarginNote title="Three drafts older than a week." body={<>The Thursday essay is closest to finished. The other two — on <em>Frege's puzzle</em> and <em>indexicals</em> — can wait, or be retired.</>} model="sonnet" />
      </div>
    </div>
  );
}

function ThreadCard({ kind, days, title, note, meta }) {
  const kicker = {
    thinking: { tag: 'THINKING · ACTIVE', kind: 'accent' },
    draft:    { tag: 'DRAFT · TEACH',     kind: 'ochre' },
    question: { tag: 'QUESTION · LEFT FOR METIS', kind: 'accent' },
  }[kind] || { tag: 'THREAD', kind: 'accent' };
  return (
    <div className="panel panel-pad" style={{ padding: '22px 24px 18px' }}>
      <div className="kicker" style={{ justifyContent: 'space-between' }}>
        <span className={'kicker kicker--' + kicker.kind} style={{ padding: 0 }}>
          <Ico name={kind === 'draft' ? 'pen' : kind === 'question' ? 'at' : 'thread'} />
          <span>{kicker.tag}</span>
        </span>
        <span style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.16em', color: 'var(--m-muted)' }}>{days.toUpperCase()}</span>
      </div>
      <h3 style={{ fontFamily: 'var(--m-display)', fontSize: 20, fontWeight: 500, letterSpacing: '-0.012em', color: 'var(--m-ink)', margin: '10px 0 8px' }}>{title}</h3>
      <p className="ed" style={{ fontSize: 14, color: 'var(--m-text)', margin: 0, marginBottom: 14 }}>{note}</p>
      <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--m-muted)', borderTop: '1px solid var(--m-rule-soft)', paddingTop: 10 }}>{meta}</div>
    </div>
  );
}

function DayRow({ time, label, title, meta, accent, ochre, last }) {
  const color = accent ? 'var(--m-accent)' : ochre ? 'var(--m-ochre-deep)' : 'var(--m-muted)';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '64px 80px 1fr 100px',
      gap: 20,
      alignItems: 'center',
      padding: '16px 24px',
      borderBottom: last ? 'none' : '1px solid var(--m-rule-soft)',
    }}>
      <div className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 14, color: 'var(--m-ink)', fontWeight: 500 }}>{time}</div>
      <div style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.2em', color, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontFamily: 'var(--m-display)', fontSize: 16, color: 'var(--m-ink)' }}>{title}</div>
      <div className="tnum" style={{ fontFamily: 'var(--m-mono)', fontSize: 10, letterSpacing: '0.14em', color: 'var(--m-muted-soft)', textAlign: 'right' }}>{meta}</div>
    </div>
  );
}

function MarginNote({ title, body, model }) {
  return (
    <div className="panel panel-pad" style={{ borderLeft: '3px solid var(--m-accent)', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <Kicker kind="accent"><MetisMark className="metis-mark" style={{ width: 14, height: 14 }}/><span>METIS · 07:14</span></Kicker>
        <Chip kind={model} plain>{model}</Chip>
      </div>
      <div style={{ fontFamily: 'var(--m-display)', fontSize: 17, fontWeight: 500, color: 'var(--m-ink)', marginBottom: 6 }}>{title}</div>
      <div className="ed" style={{ fontSize: 14 }}>{body}</div>
    </div>
  );
}

window.TodaySurface = TodaySurface;
