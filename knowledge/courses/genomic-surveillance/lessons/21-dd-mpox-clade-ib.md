# Deep Dive 2 — Mpox clade Ib: when the host's own enzyme becomes the clock

> **The case.** A DNA virus that evolves far too slowly for outbreak epidemiology became, in human transmission chains, fast enough to date — because human APOBEC3 enzymes are editing it. That single fact turned mpox genomics from nearly useless into the evidence base for a PHEIC.

---

## 1 · The question someone actually asked

In 2023–2024, eastern DRC reported rising mpox cases with an unfamiliar epidemiology. Clade I mpox had always been the more severe form and had always been understood as largely zoonotic: people infected from animals, with limited onward human transmission and repeated independent spillovers.

What was being seen looked different — transmission chains among adults, associated with sexual contact networks, sustained over time. But the epidemiological evidence was circumstantial, and the policy stakes were high. Sustained human-to-human transmission of a clade I virus is a fundamentally different threat from repeated zoonotic introductions: it implies international spread, it implies exponential rather than linear growth, and it changes what vaccination could achieve.

**The question:** is this sustained human-to-human transmission, or a series of spillovers?

## 2 · Why it looked untractable — and then didn't

Orthopoxviruses are large double-stranded DNA viruses, ~197,000 bases, replicating with high-fidelity machinery. Baseline substitution rates are around **10⁻⁶ per site per year** — roughly **0.2 substitutions per genome per year**. Run Lesson 1's arithmetic: at a two-week serial interval that is effectively **zero substitutions per transmission**. The genome cannot distinguish anything at outbreak scale.

Then the exception. **APOBEC3** enzymes are part of human innate antiviral defence. They deaminate cytosine to uracil in single-stranded DNA — which poxvirus genomes expose during replication. The result is a characteristic **C→T** substitution (G→A on the complementary strand), strongly enriched in a **TC dinucleotide context**.

In sustained human transmission, these accumulate fast enough to give a usable clock — roughly two orders of magnitude above the baseline rate. **The host's immune system is writing the timestamps.**

This produces two distinct uses, and keeping them separate is the analytical heart of the case:

**(a) APOBEC3 as a clock.** Enough change accumulates per transmission to date lineages, build time trees and estimate tMRCAs.

**(b) APOBEC3 as a *signature of human passage*.** A genome carrying many APOBEC3-type mutations has been passing through humans. A genome carrying few has not. **This is a direct, sequence-only test of the question that was actually asked** — and it does not require dense sampling, contact data, or any epidemiological investigation.

## 3 · What the data showed

The 2024 *Nature Medicine* work describing a sustained human outbreak of a new MPXV clade I lineage in eastern DRC established the entity now called **clade Ib**. Its genomic characteristics, repeated across subsequent surveillance:

- **Low overall genetic diversity** — consistent with a recent common ancestor and rapid expansion from a single introduction into human networks.
- **Accumulation of APOBEC3-signature mutations** — the evidence for sustained human-to-human transmission.
- **A large ~1,142 bp deletion**, plus terminal deletions, serving as lineage markers.

Subsequent detections traced its spread internationally: a case in **Canada in November 2024**, where genomic analysis found APOBEC3-related mutations indicating sustained human-to-human transmission; and detections in the **United States in January and June 2025**. By early 2025, more than **22,000 confirmed or suspected clade Ib cases** globally with over 60 deaths. Nationwide genomic surveillance studies since have described clade Ib **introductions**, APOBEC3-driven evolution and terminal deletions as the defining features, alongside continuing clade IIb diversity — 13 distinct lineages observed in one 2025 surveillance period, including the new **G.1** lineage from the 2025 Sierra Leone outbreak.

## 4 · The method, and where it is fragile

**Counting APOBEC3 mutations.** Classify each substitution by type and context. Compute the proportion that are C→T (or G→A) in TC context. Compare against the expectation under neutral evolution. A strong excess is the signature.

**Dating with an APOBEC3-driven clock.** Standard tip-dated Bayesian phylogenetics (Lesson 9), with the caveat that the clock is being driven by a host process rather than viral replication error.

⚠ **Three fragilities, and they are not minor.**

**1. The substitution model is wrong, and knowingly so.** Every standard model (Lesson 8) assumes substitutions at different sites are independent draws from a common process. APOBEC3 mutations are neither independent nor uniform: they are concentrated in a specific base context, occur in bursts, and depend on which strand was single-stranded at the time. Fitting `GTR+G` to an APOBEC3-driven dataset is fitting the wrong model to data everyone knows violates it. It works well enough to be useful and it is an open methodological problem, not a solved one.

**2. The clock rate is a property of the host, not the virus.** It reflects how much APOBEC3 exposure the virus experienced, which may differ between transmission routes, tissues and individuals. A rate estimated in one transmission network is not automatically transferable to another.

**3. The signature is a statement about *cumulative* human passage, not about the current transmission chain.** A genome carries the APOBEC3 marks of its whole history. High APOBEC3 content proves the lineage has been in humans; it does not prove that this particular case was infected by a human.

## 5 · What it is actually worth

**High value.** It answered the question that mattered — sustained human transmission versus repeated spillover — from sequence alone, in a setting where the epidemiological investigation needed to reach across conflict-affected territory and marginalised populations. That determination underpinned the 2024 PHEIC and the international response.

**And it created a category.** Mpox is now the canonical example of a phenomenon worth carrying forward: **a host process supplying epidemiological signal that the pathogen's own evolution cannot.** ADAR in filoviruses (Deep Dive 1) is the mirror image — the same class of process, treated as an artefact to be removed rather than a clock to be used. The difference is not the biology. It is whether the pathogen has an adequate clock of its own.

| | Mpox / APOBEC3 | Filovirus / ADAR |
|---|---|---|
| Host process | Cytosine deamination, ssDNA | Adenosine deamination, dsRNA |
| Signature | C→T in TC context | T→C in short spans |
| Viral clock without it | ~0.2 subs/genome/year — unusable | ~16 subs/genome/year — adequate |
| Therefore | **Use it as the clock** | **Remove it as an artefact** |
| Risk if mishandled | Wrong model, over-transferred rate | Inflated clock, spurious branches |

✱ **The general rule:** when a host editing process is present, ask first whether the pathogen's own clock is adequate. If it is, the editing is noise and you filter it. If it is not, the editing may be your only signal — and then you must model it, or at minimum say out loud that you did not.

## 6 · Transferable lessons

1. **Check whether the observed clock is the pathogen's or the host's.** They have different properties and different transferability.
2. **A mutational signature can be a direct epidemiological test.** APOBEC3 content answers "has this lineage been in humans" without any contact data.
3. **Low diversity plus a shared deletion is the signature of a single successful introduction**, not of a slow-evolving virus. Distinguishing those two readings requires the clock.
4. **A DNA virus is not automatically outside genomic epidemiology.** Ask about host-driven mutation before concluding the rate is too slow.
5. **Structural variants can be better lineage markers than SNPs**, particularly in large genomes with low point-mutation rates. The 1,142 bp deletion is more informative than most individual substitutions in this dataset.

## 7 · Explain it in 60 seconds

> Mpox is a DNA virus, and DNA viruses copy themselves carefully — mpox changes so slowly that in a normal outbreak, every sample would look identical. Useless for tracking transmission.
>
> Except that human cells fight back with an enzyme called APOBEC3, which chemically damages the virus's genome in a very distinctive way — always the same letter change, always in the same context. Every time the virus passes through a person, it picks up a few more of these marks.
>
> So the marks do two jobs. They act as a clock, letting you date the outbreak. And they act as a fingerprint of human passage: a virus covered in them has been going person to person, not jumping repeatedly from animals.
>
> That is how clade Ib in eastern DRC was shown to be sustained human-to-human transmission rather than a run of spillovers — a distinction that changed it from a local zoonotic problem into a public health emergency of international concern.

## 8 · Read more

- *Sustained human outbreak of a new MPXV clade I lineage in eastern Democratic Republic of the Congo*, **Nature Medicine** (2024) — nature.com/articles/s41591-024-03130-3
- *Nationwide Mpox Genomic Surveillance Reveals Clade Ib Introductions, APOBEC3-Driven Evolution, and Terminal Deletions*, medRxiv 2026.07.15.26357894
- *Emergence of Clade Ib Monkeypox Virus — Current State of Evidence*, **Emerging Infectious Diseases** 31(8), August 2025
- *Molecular detection and isolation of clade Ib monkeypox virus, Canada, November 2024*
- Nextclade mpox datasets, including clade IIb outbreak lineage designations (e.g. G.1)

⚠ Leads, not verified citations. See `sources/source-ledger.md`.
