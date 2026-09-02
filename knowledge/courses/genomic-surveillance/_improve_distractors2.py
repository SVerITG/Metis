#!/usr/bin/env python3
"""Second distractor pass.

Pass 1 removed the longest-is-correct tell by making one thin distractor per
flagged question substantive. That left a new structure: the correct answer was
the second-longest option in 63% of questions, because exactly one distractor
had been lifted past it each time. A single-move fix produces a single-move tell.

This pass expands a *second* thin distractor in about forty of those questions,
chosen for how thin the distractor was rather than for where it would move the
correct answer. Same quality argument as pass 1; the effect on rank is a side
effect of no longer having any option that is merely a short dismissal.

Idempotent. Reports anything it cannot find.
"""
import pathlib, sys

REPLACEMENTS = [
("Information is preserved at each step provided the sequencing depth is adequate throughout",
 "Information is preserved at each step of the chain provided the sequencing depth is adequate throughout the genome"),
("Exclusion requires no molecular clock estimate, whereas confirmation requires a calibrated one",
 "Exclusion requires no molecular clock estimate at all, whereas confirming a link requires a fully calibrated one"),
("It omits the completeness distribution, which determines how many are analysable",
 "It omits the genome completeness distribution, which is what determines how many of those genomes were analysable at all"),
("Poxvirus polymerases lose proofreading capacity during sustained human transmission",
 "Poxvirus polymerases progressively lose their proofreading capacity during sustained transmission in a human host"),
("The generation time, which converts per-replication rates into per-year rates",
 "The generation time of the pathogen, which is what converts a per-replication rate into a per-year rate"),
("Increase the MCMC chain length until the tMRCA credible interval narrows sufficiently",
 "Increase the MCMC chain length and the number of recorded samples until the tMRCA credible interval narrows sufficiently"),
("Each segment requires an independently designed tiling amplicon scheme to sequence",
 "Each of the eight segments requires an independently designed tiling amplicon scheme in order to be sequenced"),
("APOBEC3 editing, whose signature is cytosine deamination in single-stranded DNA",
 "APOBEC3 editing, whose signature is cytosine deamination occurring in exposed single-stranded regions of the genome"),
("Mixed infections raise the overall error rate above the consensus frequency threshold",
 "Mixed infections raise the overall per-position error rate above the consensus frequency threshold used by the pipeline"),
("Single-pass removal is computationally more expensive at this number of tips",
 "Single-pass removal becomes computationally more expensive than iteration once the tree exceeds a few hundred tips"),
("Excluding all sequences below the median genome completeness for the dataset",
 "Excluding every sequence falling below the median genome completeness value calculated for the dataset as a whole"),
("Terminal regions evolve faster and therefore saturate, making changes uninformative",
 "Terminal regions of the genome evolve faster and therefore saturate, which makes changes there uninformative about ancestry"),
("Because samples above the threshold are still sequenced at reduced coverage",
 "Because samples falling above the threshold are still sequenced, but only ever at substantially reduced genome coverage"),
("Increased amplicon yield, and a corresponding overrepresentation of that region in coverage",
 "Increased yield for that amplicon, and a corresponding overrepresentation of the affected region in the coverage profile"),
("To calibrate the Ct-to-coverage relationship for the specific assay in use",
 "To calibrate the relationship between Ct value and achieved genome coverage for the specific assay in use"),
("Library preparation, which involves multiple overnight incubation steps",
 "Library preparation, which involves several enzymatic steps including at least one overnight incubation"),
("Nanopore reads are longer, so each read spans more informative sites",
 "Nanopore reads are much longer, so each individual read spans many more informative sites than a short read does"),
("Because different versions support different flow cell chemistries and kits",
 "Because different basecaller versions support different flow cell chemistries and sequencing kit combinations"),
("Selects which barcodes to basecall first based on real-time coverage accumulation",
 "Selects which barcoded samples to basecall first, based on how coverage is accumulating across the run in real time"),
("Per-base accuracy is unnecessary when consensus depth is adequate",
 "Per-base accuracy becomes largely irrelevant once consensus depth across the genome is adequate"),
("Construction of time-scaled phylogenies for the archived sequences",
 "Construction of time-scaled phylogenies from the archived sequences at any point in the future"),
("Primer sequence inflates apparent genome length and biases alignment trimming",
 "Retained primer sequence inflates the apparent genome length and biases the alignment trimming step downstream"),
("They are pathogen-specific and therefore not comparable between programmes",
 "They are pathogen-specific and therefore cannot be compared between programmes working on different organisms"),
("Rebuild the tree under a more parameter-rich substitution model",
 "Rebuild the tree under a more parameter-rich substitution model and check whether the cluster persists"),
("That it carries the phenotypic properties associated with that lineage",
 "That it carries the phenotypic properties epidemiologically associated with that lineage elsewhere"),
("Subtype names change too frequently to support a stable epidemiological claim",
 "Subtype designations are revised too frequently to support an epidemiological claim that must remain stable over time"),
("Because variant designations are reserved for viruses under WHO risk assessment",
 "Because variant designations are formally reserved for viruses currently under active WHO risk assessment"),
("They were sampled at similar times if the tree is time-scaled",
 "They were sampled at similar times, provided the tree being shown is time-scaled rather than a divergence tree"),
("To reduce the number of parameters the substitution model must estimate",
 "To reduce the number of free parameters that the substitution model is required to estimate from the alignment"),
("Losing indel information in exchange for more reliable substitution calls",
 "Losing all indel information in exchange for more reliable substitution calls across the remaining positions"),
("Equivalent to a Bayesian posterior probability of approximately 0.78",
 "Equivalent to a Bayesian posterior clade probability of approximately 0.78 for that same split"),
("It is the only rooting method compatible with time-reversible substitution models",
 "It is the only rooting strategy that is formally compatible with a time-reversible substitution model"),
("Recombination rates cannot be estimated jointly with substitution rates",
 "Recombination rates cannot be estimated jointly with substitution rates in a single likelihood framework"),
("The spillover from the animal reservoir occurred on or near 22 February",
 "The spillover from the animal reservoir into humans occurred on or very close to 22 February"),
("Adding sequences changes the substitution model selected by information criteria",
 "Adding sequences changes which substitution model is selected by the information criterion, and therefore the branch lengths"),
("The chain has converged, since ESS above 20 indicates adequate mixing",
 "The chain has converged adequately, since an effective sample size above 20 indicates sufficient mixing"),
("Check that the root-to-tip regression R-squared exceeds a threshold",
 "Check that the R-squared of the root-to-tip regression exceeds an agreed threshold before proceeding"),
("Thirty-one independent MCMC chains, one per week, combined at the end",
 "Thirty-one independent MCMC chains, one for each week of the analysis, combined into a single posterior at the end"),
("The migration rate matrix is likely too sparse to estimate reliably",
 "The migration rate matrix between the two countries is likely too sparsely populated to be estimated reliably"),
("The sequences were generated on different platforms and are not comparable",
 "The sequences were generated on different sequencing platforms with different error profiles and are not comparable"),
("Because DRC national law prohibits open deposition of pathogen sequence data",
 "Because national law in the DRC prohibits the open deposition of pathogen sequence data derived from human samples"),
("Merged into the CBD's digital sequence information mechanism at COP16",
 "Merged into the Convention on Biological Diversity's digital sequence information mechanism agreed at COP16"),
("It confirms that the sequencing pipeline was free of systematic error",
 "It confirms that the sequencing pipeline used across the outbreak was free of systematic error"),
("Subtype names are reserved for viruses circulating in avian hosts",
 "Subtype names are conventionally reserved for influenza viruses circulating in avian rather than mammalian hosts"),
("It is updated continuously as new mutations are reported in the literature",
 "It is updated continuously, incorporating each new resistance mutation as it is reported anywhere in the literature"),
("Double deletions must be confirmed by protein-level testing before action",
 "Double deletions must always be confirmed by protein-level testing before any programmatic action is taken"),
("RNA degradation in sewage makes base calls unreliable at any depth",
 "RNA degradation during transit through the sewer network makes individual base calls unreliable at any sequencing depth"),
]

src_path = pathlib.Path(__file__).parent / "_build_manifest.py"
src = src_path.read_text()
missing, applied = [], 0
for old, new in REPLACEMENTS:
    if f'"{old}"' in src:
        src = src.replace(f'"{old}"', f'"{new}"', 1); applied += 1
    elif f'"{new}"' in src:
        pass
    else:
        missing.append(old)
src_path.write_text(src)
print(f"applied {applied}/{len(REPLACEMENTS)}")
if missing:
    print("NOT FOUND:"); [print("  ", m) for m in missing]; sys.exit(1)
