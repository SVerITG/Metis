## Phase 2 — Agent Architecture Refactor

### Completed

**Task 1: Refactored 17 existing agents (skill.md created)**

- builder: skill.md created
- career-coach: skill.md created
- cybersecurity: skill.md created
- dashboard-engineer: skill.md created
- data-guardian: skill.md created
- epidemiologist: skill.md created
- learning-coach: skill.md created
- librarian: skill.md created
- meeting-memory: skill.md created
- methods-coach: skill.md created
- metis: skill.md created
- news-aggregator: skill.md created
- news-radar: skill.md created
- presentation-maker: skill.md created
- software-engineer: skill.md created
- ux-engineer: skill.md created
- writing-partner: skill.md created

**Task 2: Rename phd-architect → research-architect**

- research-architect folder created at `02_agents/research-architect/`
- All files copied from phd-architect (README.md, contract.md, hat-clustering-context.md, output-spec.md, system-prompt.md, workflows.md)
- skill.md created with slug `research-architect` and updated name/references from "PhD Architect" to "Research Architect"
- phd-architect folder preserved as archive (not deleted)

**Task 3: Created 3 new agents**

- hr-talent: skill.md + contract.md created
- pkm-builder: skill.md + contract.md created
- edu-expert: skill.md + contract.md created

### Skipped / deferred

- ruflo-reference folder: present in 02_agents but not in the task scope — left untouched
- system-prompt.md files: preserved in all agent folders alongside new skill.md (not deleted per spec)
- contract.md files: preserved in all agent folders (not deleted per spec)

### Issues found

- None. All 21 agent folders now contain skill.md. The model matrix specified `dashboard-engineer` as `claude-opus-4-6` with `effort: normal` — this was applied exactly. Note that dashboard-engineer uses opus (unlike most other agents) due to the complexity of Shiny reactive dependency reasoning.
- The model matrix did not specify a `complexity` field for all agents — this was inferred from the agent's purpose and the quick/standard/deep guidance.

### Verification

Check that each agent folder contains skill.md:

```bash
ls 02_agents/*/skill.md
```

Expected output: 21 skill.md files across:
builder, career-coach, cybersecurity, dashboard-engineer, data-guardian,
edu-expert, epidemiologist, hr-talent, learning-coach, librarian,
meeting-memory, methods-coach, metis, news-aggregator, news-radar,
pkm-builder, presentation-maker, research-architect, software-engineer,
ux-engineer, writing-partner

Verify phd-architect is preserved (archive):

```bash
ls 02_agents/phd-architect/
```

Verify new agent contract files exist:

```bash
ls 02_agents/hr-talent/contract.md
ls 02_agents/pkm-builder/contract.md
ls 02_agents/edu-expert/contract.md
```
