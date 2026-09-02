# Source ledger — Genomic Surveillance course

**Read this before citing anything from this course.**

The AI in Public Health course shipped with the warning "every citation is an unverified
lead". This course keeps the same honesty but grades it, because the grades differ a lot.

| Grade | Meaning |
|---|---|
| **FETCHED** | The page was retrieved and read during authoring. Numbers quoted in lessons come from the page itself. |
| **SEARCH** | Title, URL and a short extract were seen in search results. The claim is probably right; the page was not read end to end. Verify before citing in a manuscript. |
| **STANDING** | Background knowledge of the field, not sourced to a specific page during authoring. Treat as a prompt to find the primary source. |

---

## CROSSREF-VERIFIED — DOIs resolved and correctly attributed

Checked 2026-08-28 with `tools/check_course_dois.py` (control-gated: a known-good and a
known-bad DOI are resolved first, and the tool refuses to judge anything unless they differ).

- `10.1093/molbev/msag117` — IQ-TREE 3: phylogenomic inference software using complex evolutionary models (Mol Biol Evol)
- `10.1126/science.adq0900` — Emergence and interstate spread of highly pathogenic avian influenza A(H5N1) in dairy cattle (Science)

**0 unresolvable, 0 misattributed.** Note that this course states most of its sources as
titles and venues rather than DOIs, so two verified DOIs is a small fraction of the reading
lists — the SEARCH grade below still governs the rest.

## FETCHED — read in full during authoring

- **Wawina-Bokalanga T, Mbala-Kingebeni P, et al. (2026).** *Phylodynamics and evolution of
  the 2026 Bundibugyo virus circulating in the Democratic Republic of the Congo: insights
  from a 100-day window of genomic sequencing.* virological.org, post 1046.
  https://virological.org/t/phylodynamics-and-evolution-of-the-2026-bundibugyo-virus-circulating-in-the-democratic-republic-of-the-congo-insights-from-a-100-day-window-of-genomic-sequencing/1046
  — **the flagship of this course.** Deep dive 1 walks it line by line. INRB Kinshasa,
  Edinburgh, Oxford, Birmingham, ITM Antwerp, WHO, Africa CDC, US CDC.
  Data: Pathoplexus dataset `BDBV_DRC_20260820` (PP_SS_3400.1), restricted licence.

- **Black A, Dudas G. *The Applied Genomic Epidemiology Handbook.*** Open web version,
  https://alliblk.github.io/genepi-book/ (print: Chapman & Hall/CRC, 2024).
  Table of contents fetched. The single best companion text for this course; Lessons 1, 7
  and 12 lean on its framing (overlapping timescales; the transmission tree is not the
  phylogenetic tree; sequencing dismisses links better than it confirms them).

- **COG-Train / Wellcome Connecting Science.** *Pathogen genomics: a new era in global
  health surveillance and strategy.* Curriculum structure fetched from
  https://wcscourses.github.io/COG-Train_Resources/pathogen_genomics_home.html
  — used as a coverage check, not a template. Their week 3 (communicating genomics) is a
  gap in this course, deliberately: see README, "what this course does not cover".

## SEARCH — seen in results, not read end to end

**The flagship's methods stack**
- IQ-TREE 3 — Mol Biol Evol 43(5):msag117 (2026), https://doi.org/10.1093/molbev/msag117
- BEAST X — Nat Methods (2025), https://www.nature.com/articles/s41592-025-02751-x
- ARTIC `amplicon-nf` — https://github.com/artic-network/amplicon-nf and
  https://artic.network/resources/amplicon-nf
- ARTIC fieldbioinformatics — https://artic.network/software/fieldbioinformatics

**The 2026 outbreak**
- WHO Disease Outbreak News 2026-DON602, Ebola disease caused by Bundibugyo virus, DRC & Uganda
- *Bundibugyo virus disease outbreak in Ituri, DRC*, The Lancet (2026), PIIS0140-6736(26)01072-X
- *Bundibugyo Virus Disease in 2026 — Clinical and Public Health Responses*, NEJM, NEJMra2607216
- Case counts (3,748 cases / 1,657 deaths as of 1 Aug 2026; declared 15 May 2026; index case
  Bunia 24 Apr 2026) — from WHO/ReliefWeb search extracts. **Verify before quoting.**

**Recent applications**
- Mpox clade Ib nationwide genomic surveillance, APOBEC3 evolution, terminal deletions —
  medRxiv 2026.07.15.26357894
- *Sustained human outbreak of a new MPXV clade I lineage in eastern DRC*, Nat Med (2024),
  https://www.nature.com/articles/s41591-024-03130-3
- H5N1 dairy cattle: *Emergence and interstate spread of HPAI A(H5N1) in dairy cattle in the
  United States*, Science, doi:10.1126/science.adq0900; *Spillover of HPAI H5N1 to dairy
  cattle*, Nature 2024, s41586-024-07849-4
- Freyja 2 multi-pathogen wastewater — medRxiv 2025.07.26.25332245
- MalariaGEN Pf8 (June 2025, 33,325 samples); *Understanding the global rise of artemisinin
  resistance*, eLife 105544
- WHO *Catalogue of mutations in M. tuberculosis complex*, 2nd ed (2023),
  ISBN 9789240082410; WHO 2025 consolidated guidance placing tNGS after initial NAATs
- Pathogenwatch platform paper — medRxiv 2026.03.18.26348693
- Africa CDC Africa PGI / AGARI — africacdc.org; 7 countries with sequencing capacity in
  2019 → 46 by late 2025; 70 platforms distributed; >1,000 people trained
- WHO *Global genomic surveillance strategy for pathogens with pandemic and epidemic
  potential 2022–2032*
- Pathoplexus (launched 2024; Ebola, West Nile, CCHF first, then mpox) — pathoplexus.org
- Nanopore Kit 14 / R10.4.1: ~Q23 simplex SUP, ~Q30 duplex — nanoporetech.com Kit 14 docs
- *Sample size calculations for pathogen variant surveillance in the presence of biological
  and systematic biases* — Cell Reports Medicine, S2666379123001325

## STANDING — verify before citing

Farrington/Noufaily aberration detection; Pango lineage nomenclature rules; cgMLST scheme
design; TransPhylo / outbreaker2 transmission-tree inference; structured coalescent vs
discrete trait phylogeography; ESS thresholds in MCMC practice; Nagoya Protocol scope for
pathogen sequence data. Every one of these is standard field knowledge and none of it was
re-verified against a primary source while writing.
