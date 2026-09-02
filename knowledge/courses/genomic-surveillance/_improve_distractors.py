#!/usr/bin/env python3
"""Rewrite thin distractors in _build_manifest.py.

The first build put the uniquely-longest option on the correct answer in 54% of
questions (chance 25%) — an exploitable tell. The recorded procedure forbids
mechanical length rebalancing, which produced a worse tell than it fixed in the
AI in Public Health course: padding every distractor makes padding itself the
signal.

So this rewrites the *weakest* distractor in each flagged question into a fuller,
more specific piece of wrong reasoning. A thin distractor is a bad distractor
regardless of word count; making it substantive is a quality improvement whose
side effect is that the length tell stops being systematic.

Idempotent: replaces exact strings, reports anything it cannot find.
"""
import pathlib, sys

REPLACEMENTS = [
("The tree stage recovers within-host diversity that consensus calling discarded earlier",
 "Depth of coverage above the minimum threshold preserves within-host diversity all the way through to the tree"),
("Consensus genomes are more accurate at detecting differences than at detecting identity",
 "Consensus calling resolves genuine differences reliably but reports spurious identity whenever coverage is uneven between samples"),
("The count should be reported per capita to allow international comparison",
 "The count should be normalised against the number of reported cases so that programmes of different sizes can be compared"),
("Genome length, which scales per-site rates into per-genome rates",
 "Genome length, since longer genomes present more sites at which a copying error can occur during each replication"),
("Use a relaxed clock, which accommodates the rate variation the plot reveals",
 "Fit an uncorrelated lognormal relaxed clock, since a shapeless root-to-tip cloud is the signature of rate variation between lineages"),
("Segmentation raises the per-site substitution rate relative to unsegmented RNA viruses",
 "Segmentation raises the effective per-site substitution rate, because each segment is replicated independently by its own polymerase complex"),
("Oxidative damage during library preparation, which is strand-biased",
 "Oxidative damage introduced while shearing the sample during library preparation, which is characteristically strand-biased"),
("Mixed infections produce reads that fail mapping quality filters and are discarded",
 "Reads from the two lineages map to overlapping positions and are discarded by the pipeline as ambiguous duplicates"),
("Removing sequences until the root-to-tip regression achieves an acceptable R-squared",
 "Removing sequences one at a time until the root-to-tip regression reaches an acceptable R-squared, then reporting that final fit"),
("Alignment algorithms systematically insert gaps at sequence termini",
 "Alignment algorithms systematically insert gaps at sequence termini, so terminal positions are unreliable in every dataset"),
("Because it introduces a fixed false-negative rate into the sequencing workflow",
 "Because it introduces a fixed false-negative rate into the workflow that must be corrected for in any prevalence estimate"),
("Chimeric amplicons spanning two pools, and systematic underestimation of genome length",
 "Formation of chimeric amplicons spanning two primer pools, and a systematic underestimation of the true genome length"),
("To satisfy accreditation requirements for traceability of control materials",
 "To satisfy laboratory accreditation requirements for full traceability of control materials used in each diagnostic run"),
("Basecalling on under-provisioned compute, particularly for super-accurate models",
 "Basecalling on under-provisioned compute, since super-accurate nanopore models require a GPU that field laboratories rarely have"),
("Consensus calling applies platform-specific error models that correct nanopore reads",
 "Consensus calling applies a platform-specific error model that corrects the systematic biases characteristic of nanopore chemistry"),
("Because regulatory accreditation requires full software version traceability",
 "Because regulatory accreditation of a clinical sequencing service requires traceability of every software version in the workflow"),
("Adjusts the motor protein speed dynamically to balance accuracy against throughput",
 "Adjusts the speed at which the motor protein ratchets the strand through the pore, trading accuracy against throughput"),
("Short reads cannot resolve repetitive regions in bacterial genomes",
 "Short reads cannot span repetitive regions, so bacterial assemblies fragment into contigs rather than closing into a chromosome"),
("Primers introduce adapter contamination that propagates into downstream assemblies",
 "Retained primer sequence is read as adapter contamination and propagates into every downstream assembly and alignment"),
("Recompute the alignment with a different multiple sequence aligner",
 "Recompute the alignment with a different multiple sequence aligner and check whether the cluster survives the change"),
("Depth is measured before trimming; breadth is measured after",
 "Depth is measured on raw reads before trimming, whereas breadth is measured on the final trimmed and primer-clipped alignment"),
("Clade 2.3.4.4b includes non-influenza viruses that must be excluded first",
 "Clade 2.3.4.4b spans several host species, so the name cannot distinguish a cattle-adapted lineage from an avian one"),
("Alleles capture indels, which SNP-based methods discard entirely",
 "Allele calling captures insertions and deletions, which reference-mapped SNP-based methods discard from the distance entirely"),
("Because filovirus taxonomy uses geographic rather than phylogenetic naming",
 "Because filovirus taxonomy names species after the place of first detection rather than by phylogenetic position"),
("They are sister taxa unless a polytomy separates them",
 "They are sister taxa, unless the node immediately joining them is drawn as an unresolved polytomy"),
("Reducing alignment length in exchange for faster likelihood computation",
 "Reducing the number of alignment columns, and therefore the computational cost of every likelihood evaluation during the tree search"),
("Uninterpretable without the corresponding SH-aLRT value",
 "Uninterpretable on its own, because ultrafast bootstrap is only meaningful when reported alongside an SH-aLRT branch test"),
("It requires no assumption that rates are constant across lineages",
 "It requires no assumption that substitution rates are constant across lineages, unlike every alternative rooting strategy"),
("Recombinant sequences fail to align without excessive gap insertion",
 "Recombinant sequences cannot be aligned without inserting so many gaps that the homology hypothesis becomes untenable"),
("The index case was infected in late February and went undetected",
 "The index case was infected in late February and went undetected until the Bunia case was identified two months later"),
("Longer alignments increase statistical power and narrow the credible interval",
 "Additional sequences increase statistical power, which narrows the credible interval and shifts the point estimate with it"),
("The prior is dominating, and should be widened before rerunning",
 "The prior is dominating the posterior for that parameter, and it should be widened before the analysis is rerun"),
("Compare marginal likelihoods between strict and relaxed clock models",
 "Compare marginal likelihoods between a strict and a relaxed clock model, and take the better-supported one as authoritative"),
("Thirty-one sequences sampled per week to give balanced temporal coverage",
 "A requirement that thirty-one sequences be sampled in each of the weekly blocks to give balanced temporal coverage"),
("The clock rate differs between countries, biasing ancestral node dates",
 "The clock rate almost certainly differs between the two countries, which biases the ancestral node dates the model reconstructs"),
("Outbreak sequences are over-represented relative to the case count",
 "Outbreak investigation sequences are over-represented relative to their share of the national case count for the period"),
("Sequencers depreciate whereas metadata schemas do not",
 "Sequencing instruments depreciate over a five-year cycle whereas a metadata schema, once designed, retains its value indefinitely"),
("Because filovirus sequences are dual-use and subject to biosecurity export controls",
 "Because filovirus sequences are considered dual-use research of concern and are therefore subject to biosecurity export controls"),
("Sequences are deposited later, delaying real-time analysis",
 "Sequences are deposited later, because the terms of use must be accepted before submission is possible"),
("Abandoned after negotiations failed, with bilateral agreements replacing it",
 "Abandoned after negotiations failed in early 2026, with a network of bilateral agreements now replacing the multilateral approach"),
("Repositories reject submissions containing off-target reads",
 "Sequence repositories automatically reject any submission found to contain off-target host reads"),
("The credible interval on every quantitative estimate",
 "The credible interval attached to every quantitative estimate presented"),
("Cold chain and connectivity infrastructure at peripheral sites",
 "Cold chain and connectivity infrastructure at peripheral collection sites, without which samples never arrive"),
("They were duplicated submissions from the same patient at different timepoints",
 "They were duplicate submissions taken from the same patients at different timepoints during their admission"),
("That the substitution model selected was stable as sequences accumulated",
 "That the substitution model chosen by ModelFinder remained stable as further sequences accumulated in each successive dataset"),
("Around 24 April 2026, matching the index case identified in Bunia",
 "Around 24 April 2026, coinciding exactly with the index case that was identified in Bunia"),
("Extensive recombination homogenising the population",
 "Extensive recombination between co-circulating lineages homogenising the population"),
("It applied only to herds in the originally affected states",
 "It applied only to the herds in the states affected during the first wave, and not to subsequent introductions"),
("It covers every anti-TB medicine in current clinical use worldwide",
 "It covers every anti-TB medicine in current clinical use worldwide, including those still in trial phases"),
("Consensus genomes cannot detect the resistance mutations at all",
 "Consensus genomes average across the bacterial population and cannot detect resistance mutations at all"),
("Deletion calling requires whole genome rather than targeted sequencing",
 "Reliable deletion calling requires whole genome rather than targeted sequencing, which this survey did not perform"),
("It produces a complete genome suitable for transmission analysis",
 "It produces a complete closed genome that is also suitable for downstream transmission analysis"),
("Inhibitors in wastewater bias the polymerase toward reference bases",
 "Inhibitors carried through from wastewater bias the polymerase systematically toward incorporating reference bases"),
("They require uniform coverage across the genome to produce stable estimates",
 "They require uniform coverage across the whole genome, which degraded wastewater RNA can very rarely provide"),
("Polio deconvolution requires no reference lineage set",
 "Poliovirus deconvolution is the one application that requires no reference lineage set"),
("Sequencing depth achievable on current platforms",
 "The sequencing depth achievable per sample on current short-read platforms"),
]

src_path = pathlib.Path(__file__).parent / "_build_manifest.py"
src = src_path.read_text()
missing, applied = [], 0
for old, new in REPLACEMENTS:
    if f'"{old}"' in src:
        src = src.replace(f'"{old}"', f'"{new}"', 1)
        applied += 1
    elif f'"{new}"' in src:
        pass  # already applied
    else:
        missing.append(old)
src_path.write_text(src)
print(f"applied {applied}/{len(REPLACEMENTS)}")
if missing:
    print("NOT FOUND:")
    for m in missing:
        print("  ", m)
    sys.exit(1)
