# Lesson 7 — What a phylogenetic tree is, and the five things people read into it that are not there

> **Concept map**
> **Builds on** — Lessons 1–2 (why differences accumulate) and Lesson 5 (the genomes going in).
> **Connects to** — Lesson 8 (how the tree is estimated), Lesson 9 (how time gets onto it), Lesson 12 (why it is not a transmission tree).
> **Leads to** — every figure in every deep dive.

## Why this matters

A phylogenetic tree is the most-shown and least-understood object in genomic surveillance. It appears on the front of outbreak reports and in ministerial briefings, and it is routinely read as things it is not: a map, a timeline of who infected whom, a ranking, an ordering of importance.

This lesson does two jobs. First, the anatomy: what each part of a tree means, precisely. Second — and this is the part that separates people who can use trees from people who can only look at them — **the five misreadings**, including the one Black and Dudas give a whole chapter to: *the transmission tree does not equate the phylogenetic tree.*

Before either, the step that everybody skips.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** why a multiple sequence alignment is a hypothesis and what happens when it is wrong.
- **Name** every component of a tree and state exactly what it asserts.
- **Recognise** the five standard misreadings and correct them in a meeting.
- **Explain** why a tree of sequences is not a tree of people, using the three mechanisms that separate them.

## Prerequisites
Lessons 0–6.

---

## Section 1 · Alignment: the hypothesis nobody calls a hypothesis

You cannot compare two genomes position by position until you have decided **which positions correspond**. That decision is the **multiple sequence alignment**, and it is a hypothesis of homology: this base in genome A descends from the same ancestral base as this base in genome B.

For closely related genomes in an outbreak, alignment is nearly trivial — the sequences are almost identical, and the only complications are indels and missing data. `MAFFT` is the standard tool and it is what the Bundibugyo team used. For divergent sequences, alignment is genuinely hard and genuinely uncertain, and **alignment error produces phylogenetic error that looks exactly like biological signal.**

Three practical points:

**Gaps.** An indel produces a gap. Whether gaps are treated as missing data or as characters changes the tree. Most viral pipelines treat them as missing.

**Trimming.** Alignment ends are unreliable — coverage falls, primers sit there, assemblers get ragged. The Bundibugyo authors **trimmed their alignment to 18,900 bases** because one genome (26FHV054) showed sequencing artefacts at the genome ends, and they preferred losing a few hundred positions across every sequence to keeping noise in all of them.

✱ That trade is worth naming, because you will make it repeatedly: **trimming loses real signal from every sequence in order to remove artefactual signal from a few.** It is the right call when the artefacts are concentrated at the edges — which, for amplicon-derived viral genomes, they reliably are. It is the wrong call if applied so aggressively that the informative sites go too.

**Masking.** Beyond trimming ends, specific sites are often masked: known problem positions, homoplastic sites, drug-resistance loci in bacteria (Lesson 6), and recombinant regions (Lesson 8). Masking is a stronger intervention than trimming — you are asserting that specific positions are misleading — and it should be justified and listed.

## Section 2 · Anatomy of a tree

```
                        ┌──────── A   (tip / taxon / leaf: a sampled sequence)
              ┌─────────┤
              │         └──────── B
    ──────────┤ ← internal node: an inferred common ancestor
     ↑        │         ┌──────── C
    root      └─────────┤
                        └──────── D
              ├────────►│
              branch length: how much change, in the units of the axis
```

- **Tips (leaves, taxa).** Your sequences. One tip = one consensus genome = one sample. Not one person, unless you sampled each person once.
- **Internal nodes.** Inferred common ancestors. **They are not observed and they are almost never sampled individuals.** In an outbreak with 5% of cases sequenced, essentially every internal node corresponds to an unsampled infection.
- **Branches.** Lines of descent. Their **length** is the whole information content, and you must always check the units:
- **Substitutions per site** — the default for a maximum likelihood tree. A "divergence tree".
- **Time** — for a time-scaled tree (Lesson 9). A "time tree".
- **Nothing** — some layouts (cladograms) draw all branches equal to show topology only. Reading branch lengths off a cladogram is a common and serious error.
- **Root.** The oldest point, the common ancestor of everything shown. **A tree is not rooted by default** — inferring the root is a separate step (Lesson 8) and rooting decisions change the story completely.
- **Topology.** The branching pattern: who is more closely related to whom.
- **Clade.** A node and all its descendants. The unit that gets named (Lesson 6).
- **Polytomy.** A node with more than two children — either genuinely simultaneous divergence, or, far more often, **an honest admission that the data cannot resolve the order.** The Bundibugyo analysis explicitly collapsed near-zero-length branches, converting unresolvable bifurcations into polytomies. That is good practice: a resolved-looking tree built from zero-length branches is a false claim of precision.
- **Newick.** The text format trees are stored in: `((A,B),(C,D));`. You will see it in supplements.

## Section 3 · The five misreadings

### 1. "These two are next to each other on the page, so they are closely related."
**No.** Vertical position is a drawing convention. A tree can be rotated at any node without changing its meaning at all — the same tree has an enormous number of equally valid layouts. **Only the branching structure and the branch lengths mean anything.** Two tips can be adjacent on the page and separated by the deepest split in the tree.

### 2. "The tree goes from primitive on the left to advanced on the right."
**No.** All tips are contemporary with their sampling dates; none is ancestral to another tip. A "ladderised" tree that looks like a progression is a layout choice. There is no direction of improvement in a phylogeny.

### 3. "The internal node is the index case."
**No.** Internal nodes are inferred ancestral sequences. Even if you happen to have sampled the true ancestor, it appears as a *tip* (with a short branch), not as an internal node. In sparsely sampled outbreaks, internal nodes overwhelmingly correspond to people you never sequenced.

### 4. "This clade is bigger, so it is more important / more transmissible."
**No.** Clade size is a function of **sampling** at least as much as of transmission. A health zone that sequenced 200 samples produces a large clade; a health zone that sequenced 4 does not. Deep Dive 1 shows the disciplined version of this: the Bundibugyo authors noted that Mongbwalu genomes showed substantial diversity and emerged from deep parts of the tree, and described it as *suggesting* a possible origin — a hypothesis flagged as such, not a conclusion.

### 5. "The tree shows who infected whom."
**No**, and this one needs its own section.

## Section 4 · The transmission tree is not the phylogenetic tree

Three distinct mechanisms separate them, and all three operate at once.

**Mechanism 1 — Incomplete sampling.** Sequence 5% of cases and 95% of the transmission tree's nodes are missing. Two tips that appear adjacent may be separated by many unsampled people. The phylogeny is a *sparse projection* of the transmission tree, and you cannot recover what was never sampled.

**Mechanism 2 — Within-host diversity and the transmission bottleneck.** A host carries a *population* of pathogen genomes (Lesson 2). Transmission passes some subset of that population, sometimes a single variant, sometimes several. So the coalescent event joining two people's viruses may sit *before* the transmission event in time — the lineages diverged inside the donor before either was transmitted. This is the **pre-transmission interval**, and it means the phylogeny's branching points and the transmission events do not coincide even in principle.

**Mechanism 3 — Not enough mutations.** Lesson 1's arithmetic. At ~0.66 substitutions per transmission for Bundibugyo virus, a chain of three people frequently produces three identical genomes. The tree cannot order what the molecular clock never recorded.

```
   TRANSMISSION TREE (people)      PHYLOGENETIC TREE (sequences)
   ──────────────────────────      ─────────────────────────────
        Ann                              ┌── Ann
       ╱   ╲                          ───┤
    Ben     Cal        →                 ├── Ben        Ben and Cal appear
     │                                   └── Cal        as a polytomy with Ann;
    Dee  (not sampled)                                  Dee is simply absent;
     │                                   ┌── Eve        Eve attaches high in the
    Eve                                  └──            tree with no sign that
                                                        two people separate her
                                                        from Ann.
```

✱ **This is why sequencing dismisses links better than it confirms them.** A large genetic distance is strong evidence *against* a direct link — that would require an implausible burst of mutation in one transmission. A small distance is *consistent with* a direct link and with a dozen other histories. In an outbreak investigation, the defensible genomic statements are almost always negative ones: "these two cases are not part of the same chain", "this is not a continuation of the earlier cluster", "this is a new introduction, not local transmission".

⚠ Methods do exist that attempt actual transmission-tree inference — `TransPhylo`, `outbreaker2` and relatives — by combining the phylogeny with epidemiological data (serial intervals, exposure windows, sampling fractions). They are legitimate and useful. But they buy resolution by adding assumptions, and their output is a *posterior distribution over transmission trees*, not a diagram of who infected whom. Presenting the maximum a posteriori transmission tree as fact is a misuse of the method, not a use of it. Lesson 12.

## Section 5 · Reading a real tree, in order

A checklist for the next tree you are shown:

1. **What are the branch length units?** Substitutions per site, or time, or nothing? Find the scale bar. If there is no scale bar, ask for one.
2. **Is it rooted, and how?** Outgroup, midpoint, or clock-based? (Lesson 8.)
3. **What do the colours encode?** Location, date, host, sequencing batch? And **has anyone coloured it by sequencing batch?**
4. **What is the support on the nodes carrying the argument?** (Lesson 8.) Deep splits with 60% bootstrap support are not evidence.
5. **What is the sampling fraction, and does it vary by the thing the colours encode?** If the tree is coloured by health zone and health zones sequenced at different rates, the geographic pattern is partly a sampling pattern.
6. **Are there polytomies, and were near-zero branches collapsed?** Precision that is not there should not be drawn.

## Section 6 · Where you will meet trees

- **Nextstrain / Auspice** — the interactive standard: time tree, map, colour-by, filter, with a shareable URL. The tool that made real-time genomic epidemiology a public activity, now maintaining continuously updated builds across many pathogens including the 2025–2026 North America measles outbreak, and extended by others to pathogens like Lassa virus.
- **PearTree** — the interactive viewer used for the Bundibugyo trees on virological.org.
- **Microreact** — tree plus map plus metadata table, widely used in bacterial surveillance.
- **FigTree**, **`ggtree`** (R), **`baltic`**/**`Bio.Phylo`** (Python) — for figures you control.
- **Pathogenwatch** — trees in a bacterial surveillance frame, with AMR and typing attached.

## Practice

Open any Nextstrain build for a pathogen you care about. Then:

1. Switch between the time tree and the divergence tree. Notice which relationships change appearance and which do not.
2. Colour by country, then by "originating lab". If those two views look similar, sampling geography is driving the picture.
3. Find a clade and ask: is this large because transmission was intense, or because someone sequenced a lot?
4. Pick two adjacent tips and write down, honestly, what you can and cannot say about a link between those two cases.

## In one paragraph

A phylogenetic tree is a hypothesis about shared ancestry among *sequences*, built on a prior hypothesis — the alignment — that is rarely acknowledged as one. Its meaning lies entirely in branching structure and branch lengths, so vertical position, left-to-right order and visual adjacency carry no information, and clade size is as much a statement about sampling as about transmission. Internal nodes are inferred ancestors, not index cases. Above all, the tree of sequences is not the tree of people: incomplete sampling, within-host diversity with its pre-transmission interval, and too few mutations per transmission all separate them, which is why the defensible genomic statements in an outbreak are usually the negative ones.
