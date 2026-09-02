#!/usr/bin/env python3
"""Assemble lessons.json for the genomic-surveillance course.

Superset manifest: the dashboard reader consumes id/title/description/section/order;
the multilevel learning layer consumes day/phase/emoji/topics/key_terms/time/optional/
quiz/practical. One file, two consumers. See course.json -> manifest_shape.
"""
import json, pathlib, random

# ---------------------------------------------------------------- modules
MODULES = [
    (0,  "Start here",            "The atlas",                          "Understand", 1.0),
    (1,  "Day 1 · Molecule",      "Two clocks",                         "Understand", 1.0),
    (2,  "Day 1 · Molecule",      "Mutation, signal, artefact",         "Analyze",    1.0),
    (3,  "Day 1 · Machine",       "Sample to library",                  "Apply",      1.25),
    (4,  "Day 1 · Machine",       "The machines",                       "Apply",      1.25),
    (5,  "Day 2 · Data",          "Reads to genome",                    "Apply",      1.25),
    (6,  "Day 2 · Data",          "Naming things",                      "Analyze",    1.0),
    (7,  "Day 2 · Trees",         "What a tree is",                     "Understand", 1.0),
    (8,  "Day 2 · Trees",         "Building the tree",                  "Analyze",    1.25),
    (9,  "Day 3 · Time",          "Time on the tree",                   "Analyze",    1.25),
    (10, "Day 3 · Dynamics",      "Coalescent and growth",              "Analyze",    1.25),
    (11, "Day 3 · Dynamics",      "Where it came from",                 "Evaluate",   1.0),
    (12, "Day 3 · Dynamics",      "Clusters and transmission",          "Evaluate",   1.25),
    (13, "Day 4 · The system",    "Sampling and metadata",              "Evaluate",   1.25),
    (14, "Day 4 · The system",    "Sharing, governance, equity",        "Evaluate",   1.0),
    (15, "Day 4 · The system",    "Genome to decision",                 "Evaluate",   1.0),
    (20, "Deep dives",            "Bundibugyo virus, DRC 2026",         "Evaluate",   1.5),
    (21, "Deep dives",            "Mpox clade Ib",                      "Evaluate",   1.0),
    (22, "Deep dives",            "H5N1 in dairy cattle",               "Evaluate",   0.83),
    (23, "Deep dives",            "Resistance markers",                 "Evaluate",   1.0),
    (24, "Deep dives",            "Wastewater and agnostic surveillance","Evaluate",  1.0),
    (25, "Deep dives",            "T. b. gambiense — the counter-example","Evaluate", 1.25),
]

PHASES = [
    (1, "Orientation",                ["lesson-00"]),
    (2, "From DNA to data",           ["lesson-01","lesson-02","lesson-03","lesson-04","lesson-05","lesson-06"]),
    (3, "From data to trees to time", ["lesson-07","lesson-08","lesson-09","lesson-10","lesson-11","lesson-12"]),
    (4, "From inference to decision", ["lesson-13","lesson-14","lesson-15"]),
    (5, "Recent applications",        ["lesson-20","lesson-21","lesson-22","lesson-23","lesson-24","lesson-25"]),
]

# id, order, section, phase, day, emoji, minutes, optional, file, title, subtitle, description, topics, key_terms, practical
META = [
 ("lesson-00",0,"Start here",1,"Atlas","🗺️",60,False,"00-the-atlas.md",
  "The atlas — what genomic surveillance is, and the four questions it answers",
  "The whole landscape on day one, so every later lesson has something to point at",
  "Sixty applications sorted by the four questions genomic surveillance can answer, the molecule-to-decision chain, and the three things a consensus genome can never tell you.",
  ["The four questions","The molecule-to-decision chain","The atlas of applications","What a consensus genome cannot tell you"],
  ["genomic surveillance","consensus genome","comparator","sampling frame"],
  "Take the last three genomic surveillance claims you read. Sort each into one of the four questions, name its classical comparator, and note whether the evidence offered belongs to the question actually being asked."),

 ("lesson-01",1,"Day 1 · Molecule",2,"1.1","🕰️",60,False,"01-two-clocks.md",
  "Two clocks — why a pathogen genome carries epidemiological information at all",
  "One multiplication that tells you in advance what any genomic study can possibly find",
  "The overlapping timescales of evolution and transmission, the substitutions-per-transmission calculation, and how to test whether a population is measurably evolving.",
  ["Overlapping timescales","Genome length and rate","Substitutions per transmission","Measurably evolving populations"],
  ["substitution rate","serial interval","temporal signal","root-to-tip regression"],
  "For a pathogen you work on: find a published evolutionary rate, multiply by genome length and serial interval, and write the sentence 'sequencing this pathogen can distinguish ___ but cannot distinguish ___'."),

 ("lesson-02",2,"Day 1 · Molecule",2,"1.2","🔬",60,False,"02-mutation-to-signal.md",
  "Mutation, substitution, signal, artefact",
  "The vocabulary that stops you being fooled, and the host enzymes that write fake mutations",
  "Precise terminology for genetic change, why the consensus genome discards within-host diversity, and how to recognise APOBEC3, ADAR and oxidative signatures from base-change patterns alone.",
  ["Mutation vs substitution","Within-host diversity and iSNVs","APOBEC3, ADAR, oxidative damage","Defensible exclusion of sequences"],
  ["iSNV","consensus","APOBEC3","ADAR","homoplasy"],
  "Take a phylodynamic paper on an RNA virus. How many sequences were generated versus analysed, was mutational-signature screening done, was outlier removal iterative, and was the alignment trimmed with a stated reason?"),

 ("lesson-03",3,"Day 1 · Machine",2,"1.3","🧪",75,False,"03-sample-to-library.md",
  "Sample to library — the wet-lab chain and the decisions inside it that are epidemiological",
  "The Ct threshold is a sampling frame wearing laboratory clothes",
  "Specimen choice, extraction, the Ct gate and the selection it introduces, the four enrichment strategies, multiplexing and the controls that must be on every run.",
  ["Specimen types and biosafety","Ct as a selection rule","Amplicon, capture, metagenomics, culture WGS","Multiplexing and index hopping","Controls"],
  ["Ct value","tiling amplicon","primer dropout","index hopping","host depletion"],
  "Find a methods section and extract: specimen types, the sequencing selection rule, enrichment strategy and primer scheme version, whether primer trimming is mentioned, and the controls. Then write one sentence describing the sampling frame."),

 ("lesson-04",4,"Day 1 · Machine",2,"1.4","⚙️",75,False,"04-the-machines.md",
  "The machines — how DNA becomes data",
  "Basecalling is the literal moment a molecule becomes a file, and its version belongs in your metadata",
  "Illumina sequencing-by-synthesis and nanopore mechanism, Phred scores and why depth beats per-read accuracy, adaptive sampling, and platform choice as a surveillance-design decision.",
  ["Sequencing by synthesis","Nanopore and basecalling","Phred scores and depth","Adaptive sampling","Choosing a platform"],
  ["basecalling","Phred score","duplex","adaptive sampling","systematic error"],
  "For a surveillance programme you know: write down samples arriving per week, acceptable sample-to-answer time, genome size and repeat structure, and available power/cold chain/compute/maintenance. Then pick a platform and answer: what happens the day the machine breaks?"),

 ("lesson-05",5,"Day 2 · Data",2,"2.1","💻",75,False,"05-reads-to-genome.md",
  "Reads to genome — the bioinformatics chain and the four thresholds that decide your dataset",
  "Four numbers set by humans, all pushing the same way",
  "File formats and what each discards, mapping versus assembly, primer trimming, depth and breadth, and the compound selection produced by the four QC thresholds.",
  ["FASTQ to BAM to VCF to FASTA","Mapping vs de novo assembly","Primer trimming","Depth, breadth, consensus","The sampling cascade"],
  ["FASTQ","BAM","consensus threshold","amplicon dropout","batch effect"],
  "Open a methods section and find the pipeline version, minimum depth, completeness threshold, primer trimming and the sample counts at each stage. Then draw the cascade from cases to analysed genomes."),

 ("lesson-06",6,"Day 2 · Data",2,"2.2","🏷️",60,False,"06-naming-things.md",
  "Naming things — clades, lineages, variants, sequence types and the SNP threshold",
  "A name is a claim about a tree; a SNP threshold is a case definition",
  "Four overlapping naming systems, Pango aliasing, influenza genotypes, MLST and cgMLST, and how to interrogate a SNP-threshold cluster definition.",
  ["Clade, lineage, variant, ST","Pango and WHO labels","Influenza genotypes","MLST and cgMLST","SNP thresholds as case definitions"],
  ["Pango lineage","clade","cgMLST","sequence type","SNP threshold"],
  "Take three news items about a 'new variant'. For each, identify the naming system, state what the name asserts phylogenetically, state the phenotypic claim being made, and note the gap between the two."),

 ("lesson-07",7,"Day 2 · Trees",3,"2.3","🌳",60,False,"07-what-a-tree-is.md",
  "What a phylogenetic tree is, and the five things people read into it that are not there",
  "The transmission tree is not the phylogenetic tree, and three mechanisms keep them apart",
  "Alignment as a hypothesis, the anatomy of a tree, the five standard misreadings, and why sequencing dismisses transmission links better than it confirms them.",
  ["Alignment, trimming, masking","Tips, nodes, branches, root","The five misreadings","Transmission tree vs phylogenetic tree"],
  ["alignment","polytomy","topology","branch length","pre-transmission interval"],
  "Open a Nextstrain build. Switch between time and divergence trees; colour by country then by originating lab; find a clade and ask whether it is large because of transmission or sampling."),

 ("lesson-08",8,"Day 2 · Trees",3,"2.4","📐",75,False,"08-building-the-tree.md",
  "Building the tree — substitution models, likelihood, support and rooting",
  "By the end, GTR+F+R3 is transparent and rooting is visibly a decision about the direction of time",
  "Decoding model strings, why maximum likelihood is standard, how to read bootstrap and UFBoot support, the three rooting strategies, and the three ways a tree can be confidently wrong.",
  ["Substitution models and ModelFinder","Maximum likelihood","Bootstrap and UFBoot","Rooting strategies","Recombination, homoplasy, batch effects"],
  ["GTR","FreeRate","ultrafast bootstrap","midpoint rooting","residual-minimising rooting"],
  "For a published ML tree: what model and was it selected by procedure, what support metric and on what scale, how was it rooted and was a reason given, were near-zero branches collapsed, and was recombination screened for?"),

 ("lesson-09",9,"Day 3 · Time",3,"3.1","⏳",75,False,"09-time-on-the-tree.md",
  "Putting time on the tree — molecular clocks, tMRCA, and what a date of origin actually is",
  "The most over-interpreted number in the field, read correctly",
  "Testing temporal signal, strict versus relaxed clocks, the three things tMRCA is not, and how to read ESS, burn-in and HPD intervals in a Bayesian phylodynamic result.",
  ["Temporal signal as a gate","Strict and relaxed clocks","tMRCA and its three misreadings","MCMC, ESS, burn-in, HPD","When the prior takes over"],
  ["tMRCA","HPD interval","ESS","relaxed clock","TempEst"],
  "For a time-scaled tree in your field: find the root-to-tip regression, the clock model, the tMRCA and its HPD, and ESS. Then compare the tMRCA with the date of first detection — that gap is the surveillance system's blind period."),

 ("lesson-10",10,"Day 3 · Dynamics",3,"3.2","📈",75,False,"10-coalescent-and-growth.md",
  "Phylodynamics — reading epidemic dynamics off the shape of a tree",
  "And the sensitivity analysis that separates a real slowdown from a sampling slowdown",
  "Coalescent intuition, why effective population size is not prevalence, the four tree priors including SkyGrid, and the nested-truncation analysis that tests whether a curve is real.",
  ["Coalescent intuition","Ne is not prevalence","Exponential, skyline, SkyGrid, birth-death","Doubling time and Re","Sampling change vs dynamic change"],
  ["effective population size","SkyGrid","doubling time","birth-death skyline","nested truncation"],
  "For a published skyline: what are the axis units, what is the grid resolution against the generation time, what did sequencing effort do over the same period, is there a truncation sensitivity analysis, and is the case-based curve on the same figure?"),

 ("lesson-11",11,"Day 3 · Dynamics",3,"3.3","🗺️",60,False,"11-where-it-came-from.md",
  "Where it came from — phylogeography, introductions, and the sampling bias that eats it",
  "Discrete trait analysis will place the origin wherever you sequenced most",
  "Discrete trait analysis and its failure mode, structured coalescent alternatives, what an introduction count depends on, and the same machinery applied to hosts rather than places.",
  ["Discrete trait analysis","Structured coalescent","Counting introductions","Subsampling","Host-state reconstruction"],
  ["DTA","Markov jumps","BSSVS","structured coalescent","introduction count"],
  "For a published phylogeographic analysis: compute sequences-per-case by location and check whether the inferred origin is also the best-sampled location. Then rewrite the origin claim as observation, hedged inference, and alternative explanation."),

 ("lesson-12",12,"Day 3 · Dynamics",3,"3.4","🔗",75,False,"12-clusters-and-transmission.md",
  "Clusters, transmission and the language of genomic evidence",
  "The sentences you are actually entitled to write",
  "The three strengths of genomic statement, how genomic and epidemiological evidence cover each other's blind spots, what transmission-tree software really outputs, and four questions genomics answers well.",
  ["Exclusion, consistency, indeterminacy","Combining genomic and epi evidence","Cluster definitions","Transmission tree inference","Relapse vs reinfection; import vs residual"],
  ["exclusion","single linkage","TransPhylo","background diversity","overdispersion"],
  "Take an outbreak investigation with sequences. For each case pair, place the evidence into one of the three strengths and write the sentence. Then delete every use of 'confirmed' that is not an exclusion."),

 ("lesson-13",13,"Day 4 · The system",4,"4.1","🎯",75,False,"13-sampling-and-metadata.md",
  "Sampling and metadata — the two things that decide whether any of it is true",
  "A modest sequencer with a defensible frame beats a NovaSeq with convenience sampling",
  "Four sampling strategies for four objectives, the 3/p rule for detecting a variant, the minimum metadata set, and how to evaluate a genomic surveillance system.",
  ["Four sampling frames","Sample size for variant detection","The minimum metadata set","The sampling cascade","Evaluating a system"],
  ["representative sampling","sentinel","3/p rule","collection date","metadata completeness"],
  "For a system you know: name its objective, compute sequences-per-case across strata, compute metadata completeness for the ten core fields, compute median and 90th-percentile turnaround, and list the decisions it changed in twelve months."),

 ("lesson-14",14,"Day 4 · The system",4,"4.2","🌍",60,False,"14-sharing-governance-equity.md",
  "Sharing, governance and equity — where the sequence goes, and who decides",
  "Unsequenced regions do not leave gaps, they cause wrong answers",
  "INSDC, GISAID and Pathoplexus compared, why immediate open sharing is not simply right, Nagoya/DSI and the PABS negotiations, human read depletion, and equity as a methodological requirement.",
  ["Three sharing models","Why restricted licences exist","Nagoya, DSI, the Cali Fund, PABS","Human reads and re-identification","Sequencing equity as method"],
  ["INSDC","GISAID","Pathoplexus","digital sequence information","PABS"],
  "For a dataset your institution holds: where is it deposited, what terms apply and who decided, are human reads depleted and verified, could an individual be re-identified, and what is your institution's position if someone else publishes it tomorrow?"),

 ("lesson-15",15,"Day 4 · The system",4,"4.3","✅",60,False,"15-genome-to-decision.md",
  "From genome to decision — what genomic surveillance is actually for",
  "A programme that cannot name the decisions it changed is producing data, not surveillance",
  "The decisions genomics changes, the four-question 'so what' test, deriving timeliness from the decision, writing for an incident management team, and when genomics is the wrong tool.",
  ["Decisions genomics changes","The so-what test","Timeliness from the decision","Writing for incident management","When genomics is the wrong tool"],
  ["so-what test","decisions changed","turnaround distribution","opportunity cost"],
  "Capstone: design a genomic surveillance activity on one page — decision, question, sampling frame, the arithmetic, platform, metadata, timeliness, analysis, sharing, the result that would change the decision, and the limitation you already know you will write."),

 ("lesson-20",20,"Deep dives",5,"5.1","🦠",90,False,"20-dd-bundibugyo-drc-2026.md",
  "Bundibugyo virus in Ituri, DRC, 2026 — a 100-day window, line by line",
  "Every methodological choice in the flagship study, including the ones the authors assumed you knew",
  "The 2026 BDBV outbreak analysis decoded phrase by phrase: amplicon-nf, the ADAR exclusion, GTR+F+R3, residual-minimising rooting, BEAST X, SkyGrid, and the nested-truncation sensitivity analysis that makes it trustworthy.",
  ["The outbreak and the four questions","The sequencing cascade: 626 to 525","Every method phrase decoded","tMRCA and the detection lag","The negative finding on lineage dominance","The iterative cutoff analysis"],
  ["Bundibugyo virus","amplicon-nf","ADAR exclusion","SkyGrid","Pathoplexus","tMRCA"],
  "Read the virological.org post alongside this deep dive. Then list every methodological phrase in it and check you can say which lesson covers it and what it would cost to get wrong."),

 ("lesson-21",21,"Deep dives",5,"5.2","🧬",60,False,"21-dd-mpox-clade-ib.md",
  "Mpox clade Ib — when the host's own enzyme becomes the clock",
  "The same class of process that Deep Dive 1 filters out, used here as the only available signal",
  "How APOBEC3 editing turns a too-slow DNA virus into a datable one, why the same signature is a direct test of sustained human transmission, and the three fragilities of an editing-driven clock.",
  ["Why mpox has no usable viral clock","APOBEC3 as clock and as signature","Clade Ib: low diversity, deletions, introductions","Fragilities of an editing-driven clock"],
  ["APOBEC3","clade Ib","hypermutation signature","terminal deletion"],
  "Compare the APOBEC3 and ADAR tables in this deep dive and Lesson 2. Then state the general rule for deciding whether a host editing process is your clock or your artefact."),

 ("lesson-22",22,"Deep dives",5,"5.3","🐄",50,False,"22-dd-h5n1-dairy-cattle.md",
  "H5N1 in dairy cattle — one spillover, then two, and what a genotype name carries",
  "A phylogenetic reconstruction describes the past; it does not bound the future",
  "Host-state reconstruction establishing a single B3.13 spillover into US dairy cattle, why only a genotype name could carry the finding, polymerase adaptation as a hypothesis about phenotype, and the independent D1.1 introduction that followed.",
  ["Host-state reconstruction","Why genotype not subtype","Adaptation markers PB2 M631L, PA K497R","Spillback","The second, independent spillover"],
  ["reassortment","genotype B3.13","D1.1","host-state reconstruction","spillback"],
  "Apply the one-clade-versus-many-clades logic to a reservoir question in your own field. What sampling of the source population would you need before the conclusion is safe?"),

 ("lesson-23",23,"Deep dives",5,"5.4","💊",60,False,"23-dd-resistance-markers.md",
  "Resistance as genomic surveillance — malaria and TB, or genomics without trees",
  "The most decision-linked genomics in global health, and the most deployable",
  "Marker surveillance as a distinct discipline: kelch13 and pfhrp2/3 deletions, the WHO TB mutation catalogue built from 52,000 matched isolates, where tNGS sits in the diagnostic algorithm, and the five failure modes of marker surveillance.",
  ["Why trees do not apply","kelch13 and artemisinin partial resistance","pfhrp2/3 deletions and diagnostic escape","The WHO TB mutation catalogue","tNGS versus WGS","Failure modes"],
  ["kelch13","pfhrp2 deletion","mutation catalogue","tNGS","heteroresistance"],
  "Take a resistance marker in your field. Is it validated or candidate? What decision and threshold does it feed? And what sampling frame would the frequency estimate need to justify that decision?"),

 ("lesson-24",24,"Deep dives",5,"5.5","🚰",60,False,"24-dd-wastewater-and-agnostic.md",
  "Wastewater and pathogen-agnostic surveillance — sequencing a population, sequencing without a hypothesis",
  "Two frontiers that break assumptions the rest of the course relied on",
  "Why the consensus genome is a chimera in a mixture, how Freyja deconvolution works and what its reference-set dependency costs, the polio template, and the five obstacles facing routine metagenomic surveillance.",
  ["What changes when the sample is a population","Deconvolution and Freyja 2","The reference-set dependency","Polio environmental surveillance as template","Metagenomics: cost, sensitivity, interpretation"],
  ["deconvolution","Freyja","lineage abundance","pathogen-agnostic","host depletion"],
  "For a wastewater or metagenomic surveillance proposal you can find: name the action threshold and the decision-maker. If neither exists, it is research — say so, and fund it as research."),
 ("lesson-25",25,"Deep dives",5,"5.6","🪰",75,False,"25-dd-gambiense-hat.md",
  "T. b. gambiense — the course's counter-example, and what a genomic baseline would have to contain",
  "The one case where most of this course does not apply, and saying so is the skill",
  "Why a clonal, monophyletic parasite rules out three of the four questions; why blood is the wrong compartment when the reservoir is in the skin; why the animal-reservoir question is a structured-coalescent problem; and why the highest-value genomic act available today is archiving, not analysis.",
  ["Zero transmission by 2030 and the three ways it could be met while transmission persists","Tbg1 clonality and what it rules out","Low parasitaemia and the kinetoplast minicircle route","The host sampling asymmetry","Import vs residual, and the baseline archive"],
  ["Tbg1","minicircle","dermal reservoir","structured coalescent","baseline archive","acoziborole"],
  "For a focus you know: list what is currently archived, in what tissue, with what metadata. Then write the sentence you would need to answer 'import or residual?' in 2032, and identify what is missing to write it."),
]

# ---------------------------------------------------------------- quizzes
Q = {}

Q["lesson-00"] = [
 ("A report states that a lineage is more transmissible, supporting it only with the observation that it grew as a share of sequenced samples over eight weeks. Which failure is this?",
  ["A question-4 claim supported by question-3 evidence that is itself confounded by sampling",
   "A question-1 claim that should have used contact tracing as its comparator instead",
   "A valid inference, since growth in sequence share is the operational definition of transmissibility",
   "A question-2 claim, because share-of-sequences is fundamentally a geographic quantity"], 0,
  "Transmissibility is a property of the pathogen (Q4) and needs a phenotypic or carefully-controlled epidemiological link. Growth in sequence share is Q3 evidence, and it is confounded by every change in who got sequenced. Answering one question with another question's evidence is the field's most common error."),
 ("Which statement about the molecule-to-decision chain is correct?",
  ["Information is preserved at each step of the chain provided the sequencing depth is adequate throughout the genome",
   "Depth of coverage above the minimum threshold preserves within-host diversity all the way through to the tree",
   "Information is only ever lost moving rightward, so the skill is knowing what each step discarded",
   "Sampling and metadata sit inside the chain, between the machine stage and the data stage"], 2,
  "Every step is a lossy compression: consensus discards within-host diversity, alignment discards unsequenced regions, the tree discards everything but topology and branch lengths. Nothing downstream recovers it. Sampling and metadata sit outside the chain and determine all of it."),
 ("Genomics is described as better at ruling transmission links out than in. What underlies the asymmetry?",
  ["Consensus calling resolves genuine differences reliably but reports spurious identity whenever coverage is uneven between samples",
   "A large distance would require an improbable mutation burst; a small distance fits many histories",
   "Exclusion requires no molecular clock estimate at all, whereas confirming a link requires a fully calibrated one",
   "Contact tracing supplies the negative evidence, so the genomic contribution is purely confirmatory"], 1,
  "With well under one substitution per transmission, identical genomes are consistent with direct transmission, with a short unsampled chain, and with a common source. A large distance, by contrast, would require far more mutation than the clock allows — which is why it is strong evidence against a link."),
 ("Which of these can a consensus genome NOT tell you, however good the sequencing was?",
  ["Which lineage the sample belongs to under a current nomenclature scheme",
   "Whether the sample carries a documented drug-resistance substitution",
   "How far this sample sits from another sample in the same alignment",
   "Whether a minority resistant subpopulation is present in the patient"], 3,
  "Consensus calling reports the majority base at each position and discards everything below the threshold. Minority variants, mixed infection and transmission bottlenecks all require the reads. The other three are exactly what a consensus genome is for."),
 ("A surveillance programme reports 8,400 genomes produced last year. By this course's framing, what is the deficiency?",
  ["Genome count without a stated sequencing platform is not a comparable figure",
   "The count should be normalised against the number of reported cases so that programmes of different sizes can be compared",
   "Genome count is not a measure of decisions changed, which is what a programme is for",
   "It omits the genome completeness distribution, which is what determines how many of those genomes were analysable at all"], 2,
  "Volume is the metric most easily produced and least connected to purpose. The defensible account names decisions that came out differently. Completeness and platform matter, but they are inputs to the same question rather than the question itself."),
]

Q["lesson-01"] = [
 ("A virus has an evolutionary rate of 1e-3 substitutions per site per year, a 10 kb genome and a 4-day serial interval. Roughly how many substitutions separate two people in a direct transmission?",
  ["About 0.1",
   "About 1.1",
   "About 4.0",
   "About 0.01"], 0,
  "1e-3 x 10,000 = 10 substitutions per genome per year. Multiplied by 4/365 years gives about 0.11. At roughly one mutation per ten transmissions, this pathogen resolves lineages and introductions but cannot order individual links."),
 ("Why can mpox be used for outbreak-scale epidemiology despite orthopoxviruses having a baseline rate around 1e-6 per site per year?",
  ["Its 197 kb genome is large enough that even a very low per-site rate yields many changes",
   "Poxvirus polymerases progressively lose their proofreading capacity during sustained transmission in a human host",
   "Host APOBEC3 editing during human transmission drives an apparent rate far above baseline",
   "Structural variants accumulate independently of the point substitution rate"], 2,
  "APOBEC3 deaminates cytosine in single-stranded DNA, producing C-to-T changes fast enough to give a usable clock during human-to-human chains. Genome length alone does not rescue it: at baseline the rate is roughly 0.2 substitutions per genome per year."),
 ("The mutation rate and the substitution rate differ. What separates them?",
  ["Sequencing error, which inflates observed differences above the true mutation rate",
   "The generation time of the pathogen, which is what converts a per-replication rate into a per-year rate",
   "Genome length, since longer genomes present more sites at which a copying error can occur during each replication",
   "Selection and bottlenecks, which remove most mutations before they are ever observed"], 3,
  "The mutation rate is a property of the polymerase. The substitution rate is what survives purifying selection, population bottlenecks and your sampling — usually far less. Generation time and genome length are conversions between units, not the source of the gap."),
 ("A dataset's root-to-tip regression produces a flat, shapeless cloud. What follows?",
  ["Fit an uncorrelated lognormal relaxed clock, since a shapeless root-to-tip cloud is the signature of rate variation between lineages",
   "The population is not measurably evolving over this window, so it cannot be dated",
   "Re-root the tree using midpoint rooting, which does not depend on temporal signal",
   "Increase the MCMC chain length and the number of recorded samples until the tMRCA credible interval narrows sufficiently"], 1,
  "No temporal signal means no dating. The software will still return a tMRCA, but it will be the prior restated with a credible interval that looks like evidence. Neither a relaxed clock nor a longer chain creates signal that is absent from the data."),
 ("Influenza A's eight segments matter for genomic epidemiology because:",
  ["Segmentation raises the effective per-site substitution rate, because each segment is replicated independently by its own polymerase complex",
   "Each of the eight segments requires an independently designed tiling amplicon scheme in order to be sequenced",
   "Reassortment means there is no single phylogeny, so one tree cannot describe the virus",
   "The segments must be concatenated before alignment, which introduces frameshift artefacts"], 2,
  "Segments swap wholesale between co-infecting viruses, so influenza has eight phylogenies that can disagree. This is why H5N1 findings are expressed as genotypes — combinations of segment lineages — rather than as subtypes."),
]

Q["lesson-02"] = [
 ("A filovirus genome shows an excess of T-to-C changes concentrated in short consecutive runs. What is the most likely explanation?",
  ["ADAR host editing, which is processive and therefore affects short spans",
   "APOBEC3 editing, whose signature is cytosine deamination occurring in exposed single-stranded regions of the genome",
   "Oxidative damage introduced while shearing the sample during library preparation, which is characteristically strand-biased",
   "Primer sequence retained in the consensus because trimming was omitted"], 0,
  "ADAR deaminates adenosine in double-stranded RNA and works processively, so the marks cluster. APOBEC3 acts on ssDNA and writes C-to-T; oxidative damage writes G-to-T; retained primer sequence produces reversions to reference, not runs of T-to-C."),
 ("Why does a consensus genome make a mixed infection hard to detect?",
  ["Reads from the two lineages map to overlapping positions and are discarded by the pipeline as ambiguous duplicates",
   "It reports the majority base per position, so a minor lineage is averaged away or lost",
   "Ambiguity codes are not permitted in FASTA, so mixtures must be resolved arbitrarily",
   "Mixed infections raise the overall per-position error rate above the consensus frequency threshold used by the pipeline"], 1,
  "Consensus calling is a majority summary of a within-host population. Two lineages either average into one impossible sequence or the minor one falls below threshold. Detecting mixture requires the reads, which is why archiving only FASTA forecloses the question permanently."),
 ("The Bundibugyo team removed root-to-tip outliers iteratively rather than in one pass. Why?",
  ["Iterating allows the substitution model to be re-selected as sequences are removed",
   "Single-pass removal becomes computationally more expensive than iteration once the tree exceeds a few hundred tips",
   "A convention in the field requires at least two rounds before reporting a clock rate",
   "Editing on an internal branch affects multiple tips, so outliers are not independent"], 3,
  "A bout of ADAR editing on an internal branch propagates to every descendant tip. Treating those tips as independent outliers and removing them in one pass under-corrects; re-rooting and re-fitting between rounds handles the dependency."),
 ("Which exclusion practice makes a phylodynamic analysis most defensible?",
  ["Removing sequences one at a time until the root-to-tip regression reaches an acceptable R-squared, then reporting that final fit",
   "Excluding every sequence falling below the median genome completeness value calculated for the dataset as a whole",
   "Applying a mechanistic filter first, reporting counts at every stage, and iterating",
   "Retaining every sequence and correcting for artefacts within the substitution model"], 2,
  "The mechanistic filter removes sequences for a stated biological reason before the blunt statistical filter runs, counts let a reader reconstruct what happened, and iteration handles non-independence. Removing sequences until the fit improves is fitting the filter to the desired result."),
 ("Why is a change at the very end of a viral genome treated with suspicion?",
  ["Terminal regions of the genome evolve faster and therefore saturate, which makes changes there uninformative about ancestry",
   "Coverage falls off and primers sit there, so assembly is ragged and artefacts concentrate",
   "Alignment algorithms systematically insert gaps at sequence termini, so terminal positions are unreliable in every dataset",
   "Reverse transcription initiates at the 3-prime end and introduces characteristic errors"], 1,
  "Genome ends are where depth drops, primer sequence sits and assemblers produce ragged output. This is why the Bundibugyo alignment was trimmed to 18,900 bases after one genome showed end artefacts — losing a few positions everywhere to remove noise contaminating all of it."),
]

Q["lesson-03"] = [
 ("Sequencing all PCR-positive samples with Ct below 31 is described as an epidemiological decision. Why?",
  ["Because Ct thresholds differ between assays and cannot be compared across laboratories",
   "Because it introduces a fixed false-negative rate into the workflow that must be corrected for in any prevalence estimate",
   "Because samples falling above the threshold are still sequenced, but only ever at substantially reduced genome coverage",
   "Because viral load tracks onset timing, severity and access to care, so the gate selects cases"],  3,
  "The threshold is correct laboratory practice and simultaneously a sampling frame. It enriches for people who presented early and sick, and because access to care varies geographically, it structures the genomic sample in exactly the dimension phylogeography tries to estimate."),
 ("A tiling amplicon scheme's primer binding site acquires a mutation in the circulating virus. What are the two consequences?",
  ["Amplicon dropout producing Ns, and a false reversion to reference if primers are not trimmed",
   "Increased yield for that amplicon, and a corresponding overrepresentation of the affected region in the coverage profile",
   "Formation of chimeric amplicons spanning two primer pools, and a systematic underestimation of the true genome length",
   "Loss of strand balance, and elevated homopolymer indel rates in the affected amplicon"], 0,
  "A mismatched primer amplifies poorly, so you lose coverage exactly where the virus changed. And if primer sequence reaches the consensus untrimmed, it contributes the reference base at the variable position — manufacturing a reversion."),
 ("An outbreak presents as an unknown illness with high mortality and no candidate pathogen. Which enrichment approach is indicated?",
  ["Tiling amplicon PCR, because it is most sensitive at high Ct values",
   "Culture followed by whole genome sequencing, because it yields abundant clean nucleic acid",
   "Metagenomic shotgun sequencing, because it requires no prior knowledge of the target",
   "Bait capture with a broad viral family panel, because probes tolerate divergence"], 2,
  "Only metagenomics can find something nobody hypothesised. Amplicons need primers, which need a known target; capture needs probes, which need a panel; culture needs something that grows. Metagenomics costs far more and is less sensitive, which is the price of the agnosticism."),
 ("Why should an outbreak sequencing run's positive control be a distinguishable strain?",
  ["To provide a reference for depth normalisation across barcodes within the run",
   "To satisfy laboratory accreditation requirements for full traceability of control materials used in each diagnostic run",
   "To calibrate the relationship between Ct value and achieved genome coverage for the specific assay in use",
   "So that contamination of a sample by the control can be detected rather than hidden"], 3,
  "If the control is the same strain as the outbreak, contamination is invisible — the contaminated sample simply looks like a case. A distinguishable control turns a silent failure into a detectable one."),
 ("What most often dominates sample-to-answer time in outbreak sequencing?",
  ["Basecalling on under-provisioned compute, since super-accurate nanopore models require a GPU that field laboratories rarely have",
   "Transport of the specimen and waiting to fill a flow cell",
   "Library preparation, which involves several enzymatic steps including at least one overnight incubation",
   "Phylogenetic analysis, since Bayesian inference requires long MCMC chains"], 1,
  "Logistics and batching dominate. The run itself is rarely the bottleneck, which is why decentralised sequencing and small frequent batches — not faster chemistry — are what improve outbreak turnaround."),
]

Q["lesson-04"] = [
 ("Nanopore reads had per-base accuracy well below Illumina's for years, yet produced reliable consensus genomes. Why?",
  ["Nanopore reads are much longer, so each individual read spans many more informative sites than a short read does",
   "Consensus calling applies a platform-specific error model that corrects the systematic biases characteristic of nanopore chemistry",
   "Errors are largely independent between reads, so depth converts poor reads into a good consensus",
   "Amplicon sequencing avoids the genomic regions where nanopore error rates are highest"], 2,
  "With random, independent errors, the chance that a majority of 100 reads agree on the same wrong base is negligible. This is why minimum-depth thresholds are the load-bearing quality control rather than per-read quality — and why systematic error, which depth cannot fix, is the real hazard."),
 ("Why does the basecaller version belong in a sequence's metadata?",
  ["Because different basecaller versions support different flow cell chemistries and sequencing kit combinations",
   "Because regulatory accreditation of a clinical sequencing service requires traceability of every software version in the workflow",
   "Because it determines the maximum read length the instrument can produce",
   "Because re-basecalling the same raw signal with a newer model yields different sequence"], 3,
  "Basecalling is a model, and models have versions. Genomes compared across basecaller versions differ partly because of software rather than biology. This is the same reproducibility argument that makes pipeline version pinning worth the effort."),
 ("What does nanopore adaptive sampling do?",
  ["Adjusts the speed at which the motor protein ratchets the strand through the pore, trading accuracy against throughput",
   "Reads the start of a molecule, then ejects it if uninteresting, freeing the pore",
   "Selects which barcoded samples to basecall first, based on how coverage is accumulating across the run in real time",
   "Varies the applied voltage across the membrane to enrich for longer fragments"], 1,
  "Because the pore can be electrically reversed, the software can reject a read after seeing its first few hundred bases. This gives host depletion and targeted enrichment in software rather than at the bench — valuable for low-biomass, high-host metagenomic samples."),
 ("A national laboratory receives 15 samples a week in bursts, has unreliable power, no service engineer nearby, and needs results within 72 hours. What is the strongest argument against buying a high-throughput short-read instrument?",
  ["Short reads cannot span repetitive regions, so bacterial assemblies fragment into contigs rather than closing into a chromosome",
   "Per-base accuracy becomes largely irrelevant once consensus depth across the genome is adequate",
   "High-throughput instruments are only efficient when saturated, so batching adds fatal latency",
   "Reagent kits for high-throughput platforms have shorter shelf lives"], 2,
  "The instrument is efficient only when filled. At 15 samples a week, filling it means waiting, and waiting destroys the 72-hour requirement that justified the purchase. Match the instrument to the arrival rate, not to the annual total."),
 ("A variant is seen only on one sequencing platform and never on the other. What should you suspect?",
  ["Systematic error specific to that platform's chemistry or basecaller",
   "Insufficient depth on the platform where it was not observed",
   "A genuine minority variant below the second platform's consensus threshold",
   "Index hopping between barcodes within the run where it appeared"], 0,
  "Random error is beaten by depth; systematic error is not, because every read is wrong identically. Platform-specific weaknesses — homopolymer length on nanopore, particular sequence contexts on Illumina — are the first explanation for a platform-specific variant."),
]

Q["lesson-05"] = [
 ("A surveillance programme archives only consensus FASTA files. What is permanently foreclosed?",
  ["Re-assignment of lineages when a nomenclature scheme is revised",
   "Retrospective analysis of within-host diversity, mixture and minority resistance",
   "Recalculation of pairwise SNP distances against a different reference genome",
   "Construction of time-scaled phylogenies from the archived sequences at any point in the future"], 1,
  "Consensus discards read-level information by construction. Lineage reassignment and distance recalculation work fine from FASTA; anything about the within-host population needs BAMs or FASTQs, and once discarded they cannot be regenerated."),
 ("Why is primer trimming not optional for amplicon-derived consensus genomes?",
  ["Retained primer sequence inflates the apparent genome length and biases the alignment trimming step downstream",
   "Untrimmed primers cause reads to fail mapping and reduce effective coverage",
   "Retained primer sequence is read as adapter contamination and propagates into every downstream assembly and alignment",
   "Primers carry reference bases, so a mutation under a primer is called as a reversion"], 3,
  "The primer was synthesised from the reference. If its bases reach the consensus, they overwrite the patient's actual base at exactly the variable position — manufacturing a reversion to reference where a real mutation exists."),
 ("The four QC thresholds in the bioinformatics chain share a structural problem. What is it?",
  ["They are pathogen-specific and therefore cannot be compared between programmes working on different organisms",
   "They interact non-linearly, so their combined effect cannot be predicted",
   "They all preferentially remove low-load samples, compounding the Ct gate's selection",
   "They are applied after lineage assignment, so lineage calls are made on rejected data"], 2,
  "Minimum depth, consensus frequency, maximum N fraction and outlier distance all push the same way: out go the samples with least material, which came disproportionately from late presenters, milder cases and remote areas. The Ct gate selected once; these select again in the same direction."),
 ("What is the fastest check that a suspicious genomic cluster is a laboratory artefact rather than transmission?",
  ["Colour the tree by sequencing batch and look for clustering by run",
   "Recompute the alignment with a different multiple sequence aligner and check whether the cluster survives the change",
   "Rebuild the tree under a more parameter-rich substitution model and check whether the cluster persists",
   "Compare consensus sequences called at two different frequency thresholds"], 0,
  "Contamination and index hopping produce shared spurious variants, and therefore a well-supported clade of samples that share nothing but a flow cell. Colouring by run takes a minute and has saved entire studies."),
 ("Depth and breadth of coverage differ how?",
  ["Depth is measured on raw reads before trimming, whereas breadth is measured on the final trimmed and primer-clipped alignment",
   "Depth counts reads at a position; breadth is the fraction of the genome above a depth threshold",
   "Depth applies to mapped data; breadth applies only to de novo assemblies",
   "Depth is a per-sample average; breadth is a per-run average across the flow cell"], 1,
  "Depth is per-position read count; breadth is genome completeness at a chosen depth. Amplicon data is typically spiky, so a single depth threshold applied across an uneven profile can mask entire amplicons while the average looks healthy."),
]

Q["lesson-06"] = [
 ("What does assigning a sequence to a Pango lineage assert?",
  ["That it belongs to a defined clade on the phylogeny, and nothing more",
   "That it carries the phenotypic properties epidemiologically associated with that lineage elsewhere",
   "That it has been designated by WHO as a variant of interest or concern",
   "That it is antigenically distinct from the parental lineage it descends from"], 0,
  "A lineage name is a statement about phylogenetic position. Phenotype, risk designation and antigenic distinctness are separate claims requiring separate evidence — and conflating naming with importance is how a designation becomes a headline."),
 ("Why is the H5N1 dairy cattle finding expressible only at genotype resolution?",
  ["Subtype designations are revised too frequently to support an epidemiological claim that must remain stable over time",
   "Clade 2.3.4.4b spans several host species, so the name cannot distinguish a cattle-adapted lineage from an avian one",
   "A genotype names a combination of lineages across all eight reassorting segments",
   "Genotypes are assigned from whole genome data whereas subtypes use serology"], 2,
  "H5N1 names two surface proteins and covers thousands of distinct viruses; clade 2.3.4.4b names a haemagglutinin clade only. The finding is about one specific reassortant and its descendants, and only the genotype name carries that."),
 ("A colleague proposes a 5-SNP threshold to define outbreak clusters. What is the first thing to ask?",
  ["Which alignment masking scheme will be applied before distances are computed",
   "Whether single or complete linkage will be used to assemble clusters",
   "What the background pairwise distance is among unlinked local isolates",
   "Whether the threshold matches published values for this pathogen"], 2,
  "A threshold is meaningless without the local background distribution. If unlinked isolates routinely sit 3 SNPs apart in this setting, a 5-SNP rule has terrible specificity. Linkage rule and masking matter too, but they are secondary to knowing what the number is being compared against."),
 ("Why is cgMLST allele-based rather than SNP-based?",
  ["Allele calling is computationally cheaper on large bacterial genome collections",
   "Allele profiles can be computed without a reference genome assembly",
   "Allele calling captures insertions and deletions, which reference-mapped SNP-based methods discard from the distance entirely",
   "A single SNP and a recombined block both count as one difference, limiting recombination's inflation"], 3,
  "Counting a whole recombined locus as one allele difference stops a single recombination event from contributing dozens of SNPs and shattering a real cluster. The cost is that schemes are only comparable within themselves."),
 ("Why does this course insist that Bundibugyo virus is not a variant of Ebola virus?",
  ["Because filovirus taxonomy names species after the place of first detection rather than by phylogenetic position",
   "It is a distinct species, so vaccines and therapeutics for Zaire ebolavirus do not apply",
   "Because variant designations are formally reserved for viruses currently under active WHO risk assessment",
   "Because Bundibugyo virus has a segmented genome and Ebola virus does not"], 1,
  "The distinction is taxonomic and it has consequences: ERVEBO and the licensed monoclonals target Zaire ebolavirus, and Bundibugyo is far enough away that cross-protection cannot be assumed. That is why there was no licensed countermeasure in the 2026 outbreak."),
]

Q["lesson-07"] = [
 ("Two tips are drawn adjacent on a published tree. What does that tell you about their relatedness?",
  ["They are sister taxa, unless the node immediately joining them is drawn as an unresolved polytomy",
   "They share a recent common ancestor relative to the rest of the tree",
   "Nothing — a tree can be rotated at any node without changing its meaning",
   "They were sampled at similar times, provided the tree being shown is time-scaled rather than a divergence tree"], 2,
  "Vertical position is a drawing convention and any node can be rotated freely. Only branching structure and branch lengths carry information; two tips can be adjacent on the page and separated by the deepest split in the tree."),
 ("Which mechanism does NOT contribute to the phylogenetic tree differing from the transmission tree?",
  ["Incomplete sampling leaving most transmission events unrepresented",
   "Within-host diversity, so lineages diverge inside a donor before transmission",
   "Too few mutations per transmission to order the links that did occur",
   "Substitution model misspecification biasing the estimated branch lengths"], 3,
  "Model misspecification degrades a tree's accuracy but is not what separates a tree of sequences from a tree of people. The three mechanisms are structural: sparse sampling, the pre-transmission interval created by within-host diversity, and insufficient mutation per link."),
 ("Why did the Bundibugyo authors collapse near-zero-length branches into polytomies?",
  ["To reduce the number of free parameters that the substitution model is required to estimate from the alignment",
   "To satisfy the assumption of bifurcation required by coalescent tree priors",
   "Because a fully bifurcating tree built from zero-length branches claims precision it lacks",
   "To speed convergence of the MCMC chain by shrinking the tree space searched"], 2,
  "At about 0.66 substitutions per transmission, many internal branches rest on no evidence at all. Drawing them as resolved bifurcations asserts an ordering the data never recorded. A polytomy is an honest statement that the order is unresolved."),
 ("An internal node in an outbreak phylogeny most likely corresponds to:",
  ["The index case, if the tree is correctly rooted",
   "An inferred ancestral sequence from an unsampled infection",
   "The earliest sampled case within that clade",
   "A reference genome included to anchor the alignment"], 1,
  "Internal nodes are inferred ancestors, not observations. Even a genuinely sampled ancestor appears as a tip with a short branch. With a small fraction of cases sequenced, essentially every internal node is someone you never sequenced."),
 ("Trimming an alignment to remove end-of-genome artefacts involves what trade?",
  ["Losing real signal from every sequence to remove artefactual signal from a few",
   "Losing all indel information in exchange for more reliable substitution calls across the remaining positions",
   "Reducing the number of alignment columns, and therefore the computational cost of every likelihood evaluation during the tree search",
   "Discarding low-coverage samples in exchange for a more complete alignment"], 0,
  "Trimming removes positions from all sequences, including the ones with no artefact there. It is the right call when artefacts concentrate at the edges — which for amplicon-derived viral genomes they reliably do — and the wrong call if it takes the informative sites too."),
]

Q["lesson-08"] = [
 ("In GTR+F+R3, what does +R3 specify?",
  ["Three independent MCMC replicate runs combined after burn-in",
   "A three-parameter rate matrix restricting the six substitution types",
   "Three partitions corresponding to codon positions in coding regions",
   "Three freely-estimated site-rate classes, with no assumed rate distribution"], 3,
  "FreeRate estimates k rate categories and their weights directly from the data, unlike the more common +G gamma model which assumes a distributional shape governed by one parameter. R3 means three such classes."),
 ("An ultrafast bootstrap value of 78% on a branch should be read as:",
  ["Well supported, since it exceeds the conventional 70% bootstrap threshold",
   "Not well supported, because UFBoot is read on a scale where 95% is the threshold",
   "Uninterpretable on its own, because ultrafast bootstrap is only meaningful when reported alongside an SH-aLRT branch test",
   "Equivalent to a Bayesian posterior clade probability of approximately 0.78 for that same split"], 1,
  "UFBoot values are less biased than classical bootstrap and are conventionally read with 95% as the threshold for well supported. Applying the classical 70% cutoff to UFBoot systematically overstates confidence."),
 ("Why is residual-minimising rooting appropriate for a densely sampled single-outbreak dataset?",
  ["It requires no assumption that substitution rates are constant across lineages, unlike every alternative rooting strategy",
   "It is the only rooting strategy that is formally compatible with a time-reversible substitution model",
   "There is usually no suitable outgroup, and it uses the temporal signal that is present",
   "It produces the shortest total tree length and is therefore most parsimonious"], 2,
  "An earlier outbreak genome is decades divergent and distorts branch lengths; midpoint rooting assumes rate constancy. Clock-based rooting exploits what a time-stamped outbreak actually has — sampling dates — by choosing the root that best fits a root-to-tip regression."),
 ("A tree clusters samples by sequencing run rather than by geography or date, with high bootstrap support. What is happening?",
  ["Contamination or index hopping producing shared spurious variants",
   "Genuine transmission within the facilities that submitted each batch",
   "Rate variation between batches requiring a relaxed clock model",
   "Alignment error concentrated in samples processed together"], 0,
  "Shared contaminating reads really are shared, so the clade is well supported and completely artefactual. High support means your data under your model recover a split consistently — it says nothing about whether the data are real."),
 ("Recombination breaks maximum likelihood phylogenetics because:",
  ["Recombinant sequences cannot be aligned without inserting so many gaps that the homology hypothesis becomes untenable",
   "It creates homoplasy that inflates bootstrap support beyond its nominal meaning",
   "Recombination rates cannot be estimated jointly with substitution rates in a single likelihood framework",
   "Different genomic regions have different histories, so no single tree describes the alignment"], 3,
  "The whole framework assumes one tree for the whole alignment. Forcing one tree onto regions with different histories yields a tree that is wrong everywhere and often well supported — hence Gubbins and ClonalFrameML for bacteria, and per-segment trees for influenza."),
]

Q["lesson-09"] = [
 ("A tMRCA of 22 February 2026 is estimated for an outbreak whose first case was recognised on 24 April. What does this establish?",
  ["The spillover from the animal reservoir into humans occurred on or very close to 22 February",
   "The index case was infected in late February and went undetected until the Bunia case was identified two months later",
   "Transmission among sequenced cases was established at least six to eight weeks before recognition",
   "Surveillance sensitivity in the affected province was approximately 40% during that period"], 2,
  "tMRCA is a lower bound on the age of the outbreak, conditional on the sequences you have. It is not the index case, not the spillover date, and it says nothing directly about surveillance sensitivity — only that the detection lag was at least this long."),
 ("Why does a tMRCA move when you add sequences?",
  ["Additional sequences increase statistical power, which narrows the credible interval and shifts the point estimate with it",
   "Adding sequences changes which substitution model is selected by the information criterion, and therefore the branch lengths",
   "MCMC chains require proportionally more steps as tip number grows",
   "It is the ancestor of your sample, so an earlier divergent lineage pulls it back"], 3,
  "The estimate describes the common ancestor of the sequences in hand. Sample one case from an early divergent chain and the tMRCA moves earlier, sometimes substantially — which is why the Bundibugyo team checked stability across four nested datasets."),
 ("An ESS of 45 is reported for the clock rate parameter. What follows?",
  ["The credible interval for that parameter is not trustworthy and the chain needs extending",
   "The chain has converged adequately, since an effective sample size above 20 indicates sufficient mixing",
   "Burn-in was set too high, discarding usable samples from the posterior",
   "The prior is dominating the posterior for that parameter, and it should be widened before the analysis is rerun"], 0,
  "Effective sample size estimates how many independent draws your correlated MCMC samples are worth. The working convention is above 200 for every reported parameter. Below that the posterior is under-sampled and the interval is unreliable."),
 ("How do you test whether the data, rather than the prior, are driving a tMRCA estimate?",
  ["Compare marginal likelihoods between a strict and a relaxed clock model, and take the better-supported one as authoritative",
   "Run the analysis sampling from the prior only and compare the resulting tMRCA",
   "Check that the R-squared of the root-to-tip regression exceeds an agreed threshold before proceeding",
   "Increase the chain length until the credible interval stops narrowing"], 1,
  "Sampling from the prior with no data shows you what the model believes before seeing anything. If the tMRCA barely moves when the data are added, the data are not informing it. One extra run, and the single most useful robustness check in phylodynamics."),
 ("Which clock model is most defensible for a single-pathogen, single-host outbreak over a 100-day window?",
  ["An uncorrelated lognormal relaxed clock, which always accommodates more variation",
   "A random local clock, which infers where rate shifts occur along the tree",
   "A fixed clock rate taken from a previous outbreak of the same pathogen",
   "A strict clock, which is more powerful when a single rate is plausible"], 3,
  "Relaxing costs statistical power and should be justified by a reason for rates to differ — different hosts, chronic versus acute infection, long timescales. None applies here. Fixing the rate from a previous outbreak imports another study's assumption as this study's finding."),
]

Q["lesson-10"] = [
 ("A SkyGrid plot shows effective population size falling in the final four weeks of a dataset. What is the first alternative explanation to test?",
  ["That a fitter lineage has swept, reducing genetic diversity",
   "That the smoothing prior is too strong for the chosen grid resolution",
   "That sequencing effort declined over the same period",
   "That the clock model has become misspecified toward the present"], 2,
  "Fewer recent samples means fewer recent coalescences means an apparent fall in Ne. A change in sampling and a change in dynamics look identical, which is why nested-truncation analysis exists. The Bundibugyo team tested exactly this and reported it."),
 ("Why is effective population size systematically smaller than the number of infected people?",
  ["Because Ne counts only infections that were sequenced and passed quality filters",
   "Because overdispersed transmission means a minority of cases cause most transmission",
   "Because the coalescent conditions on the sampling process, which removes cases",
   "Because generation time is always shorter than the serial interval in practice"], 1,
  "Ne is the size of an idealised population that would produce the observed variability. Real epidemics are overdispersed, and superspreading pushes the effective size well below the census size. Population structure and generation time also separate them, but variance in transmission is the main driver."),
 ("SkyGrid with 31 transition points at one-week intervals over a 32-week cutoff means:",
  ["Thirty-one independent MCMC chains, one for each week of the analysis, combined into a single posterior at the end",
   "A prior requiring Ne to change by at most one order of magnitude per week",
   "Ne estimated freely in each weekly block back 32 weeks, with a smoothing prior between blocks",
   "A requirement that thirty-one sequences be sampled in each of the weekly blocks to give balanced temporal coverage"], 2,
  "The grid divides the 32 weeks before the most recent sample into weekly blocks, estimating Ne in each with a smoothing prior linking neighbours. Weekly resolution against a two-week serial interval is fine enough to see real change and coarse enough to be estimable."),
 ("A doubling time is reported as 21.0 days with a 95% HPDI of 15.0 to 40.7 days. What should the report say?",
  ["21 days, since the point estimate is the best available summary",
   "About three weeks, rounding to reflect the imprecision",
   "Between 15 and 41 days, noting the interval is strongly right-skewed",
   "Faster than 21 days, since the interval's lower bound is closer to the point estimate"], 2,
  "The interval runs to nearly six weeks, so much slower growth is entirely consistent with the data. Reporting the point alone hides that, and the right skew means the usual mental symmetry around a point estimate is wrong here."),
 ("Case-based Rt and phylodynamic Re disagree for a given outbreak. What is the correct interpretation?",
  ["The disagreement is itself the finding, since they have largely independent biases",
   "The case-based estimate is authoritative because it uses more of the data",
   "The genomic estimate is authoritative because it captures unobserved transmission",
   "One of the analyses contains an error that should be found and reconciled"], 0,
  "They measure related but different things with different blind spots. Agreement is genuine corroboration. Disagreement — classically, flat case counts with rising genomic diversity — usually means transmission continuing outside the surveillance system's view, which is precisely when the genomic result should change the response."),
]

Q["lesson-11"] = [
 ("Country A sequenced 5,000 cases; neighbouring Country B sequenced 50. A discrete trait analysis infers the epidemic originated in A. What is the main concern?",
  ["The migration rate matrix between the two countries is likely too sparsely populated to be estimated reliably",
   "The clock rate almost certainly differs between the two countries, which biases the ancestral node dates the model reconstructs",
   "DTA knows only how many sequences you supplied, not how many infections exist",
   "The tree prior assumed a single well-mixed population across both countries"], 2,
  "Discrete trait analysis treats location as a trait on a tree whose shape came from a coalescent that knows nothing about location. Most of the tree is in A because most sequences are, so A is inferred as ancestral — regardless of the truth."),
 ("What is the principal advantage of a structured coalescent method over discrete trait analysis?",
  ["It permits continuous rather than discrete location variables",
   "It separates deme population size from sampling intensity",
   "It runs substantially faster on datasets with many locations",
   "It does not require sampling dates to be known precisely"], 1,
  "The structured coalescent models subpopulations with their own sizes connected by migration, so a deme can be large and barely sampled and the model can represent that. The cost is more parameters, heavier computation and a practical limit on the number of demes."),
 ("An introduction count of 'at least 12 independent introductions' is preferred to '12 introductions' because:",
  ["Introduction counts are conventionally reported as lower bounds in the literature",
   "The Bayesian posterior for a count is always right-skewed",
   "Introductions from unsampled locations may have been merged or missed",
   "Twelve is within the credible interval rather than at its mode"], 2,
  "The count depends jointly on local sampling fraction, external sampling, the clustering rule and the time window. Denser sampling resolves single introductions into several, and unsampled sources get merged — so the number is a floor, not a measurement."),
 ("Applying phylogeographic machinery to hosts rather than places, what does a single monophyletic clade of cattle sequences indicate?",
  ["Repeated independent spillovers from the same bird lineage",
   "Ongoing bidirectional transmission between cattle and birds",
   "That cattle sequences were all generated in a single laboratory batch",
   "A single cross-species jump followed by onward transmission within cattle"], 3,
  "One clade means one successful jump; several scattered clades nested among bird sequences would mean several. This is exactly the logic that established a single B3.13 spillover into US dairy cattle — and it is bounded by how well the bird reservoir was sampled."),
 ("Why does subsampling not fix a phylogeographic dataset in which one region has zero sequences?",
  ["Subsampling reduces power, and the remaining sequences would be too few",
   "No statistical procedure recovers a location that was never sequenced",
   "Subsampling requires equal case counts, not equal sequence counts",
   "Zero-count locations violate the Markov assumption of the trait model"], 1,
  "Subsampling equalises among the locations you have. An empty region simply does not exist to the model, and transmission through it is attributed to the sampled locations either side. This is why sequencing equity is a methodological precondition rather than a fairness supplement."),
]

Q["lesson-12"] = [
 ("Two isolates are identical. What is the strongest defensible genomic statement?",
  ["Direct transmission between these two cases is confirmed by the sequence data",
   "This is consistent with direct transmission and with several other histories",
   "The two cases belong to the same transmission chain, though direction is unknown",
   "One case infected the other, with the direction determined by sampling dates"], 1,
  "With under one substitution per transmission, identity is consistent with direct transmission, a short unsampled chain, and two infections from a common source. Sampling dates do not establish direction, and the word confirmed belongs only to exclusions."),
 ("Which cell of the genomic-versus-epidemiological evidence table is most productive for an investigation?",
  ["Epidemiological link present and genomically compatible",
   "Epidemiological link present and genomically excluded",
   "No epidemiological link and genomically compatible",
   "No epidemiological link and genomically excluded"], 2,
  "Compatible genomes with no known contact point at a missing piece of the network — an unrecognised setting, an asymptomatic chain, a shared exposure. In hospital investigations this is the routine finding, and it is what leads to the shared equipment or the environmental reservoir."),
 ("What does transmission-tree inference software such as TransPhylo actually output?",
  ["The most likely chain of infections, with each link's probability",
   "A ranked list of candidate index cases with posterior support",
   "A network of contacts weighted by genetic distance",
   "A posterior distribution over transmission trees accommodating unsampled cases"], 3,
  "The output is a distribution, and its legitimate uses are estimating unobserved transmission and the offspring distribution. Presenting the maximum a posteriori tree as the transmission tree discards the method's whole contribution — and naming individuals raises ethical problems beyond the statistical ones."),
 ("A patient has two TB episodes. Whole genome sequencing shows the isolates are near-identical. What does this indicate?",
  ["Relapse — the original infection persisted and regrew",
   "Reinfection from a household contact carrying the same circulating strain",
   "Laboratory cross-contamination between the two specimens",
   "A mixed infection in which one strain was below threshold initially"], 0,
  "Near-identity between two episodes in one patient indicates the original population persisted rather than a new infection arriving. The same design settled the equivalent question in gambiense HAT, where sequencing showed relapse was parasite regrowth rather than reinfection — a statement about drug efficacy, not transmission."),
 ("Which element is most often missing from a published cluster definition?",
  ["The genetic distance threshold applied",
   "The pathogen and the reference genome used",
   "The local background distance distribution among unlinked isolates",
   "The number of isolates assigned to each cluster"], 2,
  "Thresholds are almost always stated; backgrounds almost never are. Without knowing how far apart unlinked local isolates typically sit, the threshold carries no information about how surprising the cluster is. The linkage rule is the second most commonly omitted element."),
]

Q["lesson-13"] = [
 ("A national dataset mixes routine sentinel sequences, outbreak investigation sequences and traveller screening sequences, then reports national lineage proportions. What is wrong?",
  ["The sequences were generated on different sequencing platforms with different error profiles and are not comparable",
   "Traveller sequences should be excluded because importations are not local transmission",
   "Outbreak investigation sequences are over-represented relative to their share of the national case count for the period",
   "Three different selection processes are being analysed as though they were one"], 3,
  "Each frame samples a different population. Pooled, the national picture is a composite, and apparent trends can be produced entirely by shifts in the mix. This is why sampling frame belongs as a field on every sequence — the highest-value metadata item almost nobody collects."),
 ("Approximately how many sequences are needed for 95% confidence of detecting at least one case of a variant circulating at 1%, under simple random sampling?",
  ["About 100",
   "About 300",
   "About 1,000",
   "About 30"], 1,
  "n = ln(0.05)/ln(1-p), which is approximately 3/p — so about 299. The real requirement is larger once case ascertainment, geographic clustering and the sequencing cascade are accounted for, since none of those is simple random sampling."),
 ("A programme records the date a sample arrived at the laboratory instead of the date it was collected. What is the epidemiological consequence?",
  ["A uniform shift in all node dates that cancels out in relative comparisons",
   "Loss of temporal signal, making the dataset undatable",
   "Remote areas appear later because transport delay is longer, creating spurious spread patterns",
   "Overestimation of the evolutionary rate proportional to the mean delay"], 2,
  "The delay is not uniform — it is longer for remote areas. Those health zones' tips shift later relative to central ones, which feeds phylogeographic inference and manufactures a centre-to-periphery spread pattern. A clerical shortcut becomes a published conclusion."),
 ("Which is the strongest argument that adding a metadata field can be worth more than adding a sequencer?",
  ["Metadata fields cost nothing to collect once a system is in place",
   "Sequencing instruments depreciate over a five-year cycle whereas a metadata schema, once designed, retains its value indefinitely",
   "Regulatory frameworks require metadata but do not mandate sequencing volume",
   "Without case linkage, no number of genomes can answer severity or outcome questions"], 3,
  "A programme sequencing 100 genomes a month with complete case linkage can answer severity, outcome and vaccine-effectiveness questions. A programme sequencing 1,000 with laboratory data alone can answer none of them, at any volume."),
 ("What should sit at the top of a genomic surveillance system's evaluation metrics?",
  ["Genomes produced per month, as the primary output measure",
   "Median turnaround time from collection to database deposition",
   "Decisions changed, logged with date and counterfactual",
   "Percentage of genomes exceeding the completeness threshold"], 2,
  "The other three are inputs. A programme that cannot name decisions it changed is producing data rather than surveillance, and the decisions log is also its best protection when it is asked to justify its budget."),
]

Q["lesson-14"] = [
 ("Why are the 2026 Bundibugyo genomes deposited under a restricted licence with named contacts?",
  ["Because filovirus sequences are considered dual-use research of concern and are therefore subject to biosecurity export controls",
   "Because Pathoplexus does not support fully open deposition for risk group 4 pathogens",
   "Because national law in the DRC prohibits the open deposition of pathogen sequence data derived from human samples",
   "So the institution that generated them retains control until it publishes its own analysis"], 3,
  "The restricted period addresses the helicopter-research problem: a team doing the fieldwork can be scooped by better-resourced analysts. The analysis itself was posted publicly during the outbreak — the design delivers most of both openness and equity."),
 ("What is the principal scientific cost of GISAID's model relative to INSDC?",
  ["Sequences are deposited later, because the terms of use must be accepted before submission is possible",
   "Redistribution is prohibited, making reproducible analyses harder to build",
   "Metadata fields are fewer, limiting phylogeographic inference",
   "Sequence quality is not validated before deposition"], 1,
  "The prohibition on redistribution means pipelines must handle access control and published analyses cannot ship their input data. That is a real reproducibility cost — set against the achievement of getting sequences shared at speed from countries that would not have used a fully open database."),
 ("What is the status of the WHO Pandemic Agreement's PABS annex as of mid-2026?",
  ["Adopted at the World Health Assembly in May 2026 and now in force",
   "Abandoned after negotiations failed in early 2026, with a network of bilateral agreements now replacing the multilateral approach",
   "Still under negotiation, with a final outcome due at the Assembly in May 2027",
   "Merged into the Convention on Biological Diversity's digital sequence information mechanism agreed at COP16"], 2,
  "Member States extended negotiations through 2026 and decided in May 2026 that a final negotiated outcome would be presented for adoption in May 2027. The unresolved core is mandatory benefit sharing as the condition for rapid pathogen information sharing."),
 ("Why is human read depletion before deposition a legal requirement and not only good practice?",
  ["Host reads inflate file sizes beyond repository submission limits",
   "Sequence repositories automatically reject any submission found to contain off-target host reads",
   "Human genomic data is identifiable and regulated as personal data",
   "Host sequence interferes with automated lineage assignment"], 2,
  "Any clinical sample carries host nucleic acid, and metagenomic data is mostly human. Identifiable human genetic data is regulated in the EU and many other jurisdictions, and the depletion step falls in the gap between the bioinformatician and the data protection officer."),
 ("In what order does this course expect the binding constraints on genomic surveillance capacity to fall?",
  ["Sequencers, then compute, then analysts, then metadata linkage",
   "Metadata linkage, then analysts, then compute, then sequencers",
   "Compute, then sequencers, then metadata linkage, then analysts",
   "Analysts, then sequencers, then metadata linkage, then compute"], 1,
  "Instruments are purchasable, analysts are trainable but slowly, and linking sequences to case records requires organisational change no grant buys. Most funding is allocated in the reverse order, which is why sequencing capacity has expanded faster than the ability to use it."),
]

Q["lesson-15"] = [
 ("Which question does this course say most genomic surveillance activities fail?",
  ["What decision could this change, and who makes it",
   "By when must the answer arrive",
   "What confidence is needed, and does the sampling support it",
   "What result would change the decision, and in which direction"], 3,
  "Most activities can gesture at a decision; almost none pre-specify the result that would change it. Deciding the threshold before seeing the data is what separates surveillance from interpretation after the fact — and failing the decision question at all means the activity is research, which should be funded as research."),
 ("Why should turnaround time be reported as a distribution rather than a mean?",
  ["Means are sensitive to the batch size chosen for each sequencing run",
   "A long tail affects the remote samples where the interesting cases are",
   "Regulatory reporting standards require percentiles rather than averages",
   "Turnaround times are log-normally distributed, so the mean is undefined"], 1,
  "A median of 6 days with a 90th percentile of 40 days is a system that works on average and fails exactly where samples travel furthest — which is where undetected transmission is most likely. The mean conceals precisely the failure that matters."),
 ("A genomic finding for an incident management team should always include which element that papers routinely omit?",
  ["The credible interval attached to every quantitative estimate presented",
   "The substitution model and support values used",
   "An explicit statement of what was not sequenced",
   "The database accession numbers for the sequences"], 2,
  "One clause naming the cases that were not sequenced is the single most important limitation and the easiest to leave out. Model details belong in the methods, not in an operational brief, and credible intervals are usually better expressed as calibrated confidence words for this audience."),
 ("Which is a legitimate reason to conclude that sequencing is the wrong tool for a question?",
  ["The pathogen accumulates too few substitutions per transmission to resolve the question",
   "The laboratory has no experience with the relevant amplicon scheme",
   "Sequences from neighbouring countries are not available for context",
   "The results would take three weeks and the outbreak is expected to last three months"], 0,
  "Lesson 1's arithmetic can rule a question out before any money is spent. The other three are operational obstacles that can be addressed; an inadequate clock cannot be fixed by more sequencing, more depth or a better platform."),
 ("The course argues the opportunity cost of a sequencer is often what?",
  ["A second sequencer of a different platform for cross-validation",
   "Cold chain and connectivity infrastructure at peripheral collection sites, without which samples never arrive",
   "A data manager, who frequently buys more epidemiology per euro",
   "Reagent stock sufficient to keep the instrument saturated"], 2,
  "In a programme where a large fraction of cases have no recorded onset date, fixing the metadata buys more usable epidemiology than sequencing more samples. This is the practical form of the course's spine: sampling and metadata, not the sequencer."),
]

Q["lesson-20"] = [
 ("Why did the Bundibugyo team exclude 32 genomes showing an excess of T-to-C changes?",
  ["They were duplicate submissions taken from the same patients at different timepoints during their admission",
   "They fell below the genome completeness threshold used for the analysis",
   "ADAR host editing is not viral evolution, and it biases the clock the analysis depends on",
   "They originated from the single Nord-Kivu health zone and were geographically unrepresentative"], 2,
  "ADAR-edited sites are host-imposed damage, not the virus's replication history. Left in, they inflate the substitution rate, create spurious long branches that distort the coalescent growth estimates, and appear homoplastically across unrelated tips. The clock is the parameter the filter protects."),
 ("The analysis reports a root-to-tip regression slope of 7.9e-4 and a Bayesian clock rate of 8.5e-4. Why report both?",
  ["The regression provides the prior from which the Bayesian estimate is drawn",
   "Agreement between a quick heuristic and a full model is genuine cross-validation",
   "The two apply to different subsets: 626 genomes and 525 genomes respectively",
   "Regression estimates the mutation rate while the Bayesian model estimates the substitution rate"], 1,
  "The regression is a diagnostic, not an estimator — its tips are non-independent and it understates uncertainty. Its value is as an independent sanity check on the expensive model. A heuristic validating itself would be circular; two methods agreeing is reassurance."),
 ("What did the iterative cutoff analysis with datasets ending 23 June, 3 July, 16 July and 9 August establish?",
  ["That the substitution model chosen by ModelFinder remained stable as further sequences accumulated in each successive dataset",
   "That sequencing coverage was adequate in every health zone across the period",
   "That the outbreak was declining, since later datasets showed lower growth rates",
   "That the conclusions were not an artefact of curation or of where the data were cut"], 3,
  "Clock rates converged to about 8.5e-4 across later datasets and the tMRCA was stable from July onward. That earns the claim that recent inferences reflect real dynamics rather than the reduced sampling after mid-July — but it cannot rescue bias that ran throughout in one direction, and the authors say so."),
 ("Why is 'no fitness-altering mutations and no lineage dominance' described as one of the study's most operationally useful findings?",
  ["It confirms that the sequencing pipeline used across the outbreak was free of systematic error",
   "It permits the phylogeny to be built under a strict rather than relaxed clock",
   "With no licensed countermeasure, the response depends entirely on diagnostics and tracing",
   "It establishes that the outbreak originated from a single spillover event"], 2,
  "There is no licensed vaccine or therapeutic for Bundibugyo virus, so the entire response rests on diagnostics, isolation and contact tracing. A negative finding on viral change is what tells the response those assumptions still hold — and it costs as much work as a positive one."),
 ("Which weakness of the post does this deep dive identify as most important to look for in the published version?",
  ["The choice of MAFFT rather than a more recent aligner",
   "The absence of ESS and chain convergence diagnostics",
   "The use of a 32-week rather than a 52-week SkyGrid cutoff",
   "The decision to trim the alignment to 18,900 bases"], 1,
  "Without ESS above 200 per reported parameter and evidence that independent chains converged, the credible intervals are not trustworthy. The omission is understandable in a work-in-progress post and required in a paper. The other three choices are all defended in the post itself."),
 ("What is the reported tMRCA relative to the outbreak's recognition, and how should it be stated?",
  ["Around 22 February 2026 — at least six to eight weeks before recognition, for sequenced cases",
   "Around 24 April 2026, coinciding exactly with the index case that was identified in Bunia",
   "Around 15 May 2026, the date the outbreak was formally declared",
   "Around 16 January 2026, the earliest bound of the credible interval"], 0,
  "The point estimate is 22 February with a 95% HPDI from 16 January to 24 March. The correct sentence uses the interval, says 'at least', and says 'of sequenced cases' — because tMRCA is a lower bound on the outbreak's age conditional on the sequences available."),
]

Q["lesson-21"] = [
 ("Why is APOBEC3 editing treated as a clock in mpox but ADAR editing treated as an artefact in filoviruses?",
  ["APOBEC3 acts on DNA and ADAR on RNA, and only DNA edits are heritable",
   "APOBEC3 edits are randomly distributed whereas ADAR edits cluster in spans",
   "Mpox has no adequate viral clock of its own, whereas filoviruses do",
   "ADAR editing occurs post-mortem in specimens whereas APOBEC3 occurs in living hosts"], 2,
  "Orthopoxviruses accumulate roughly 0.2 substitutions per genome per year — unusable. Filoviruses manage around 16, which is adequate. When the pathogen's own clock is adequate the editing is noise; when it is not, the editing may be your only signal."),
 ("What makes APOBEC3 signature content a direct test of sustained human-to-human transmission?",
  ["APOBEC3 is expressed only in humans and not in the animal reservoir species",
   "The signature accumulates with human passage, so its abundance indexes human transmission",
   "APOBEC3 mutations are always non-synonymous and therefore visible to selection",
   "The enzyme is induced only during symptomatic infection, marking clinical cases"], 1,
  "A genome laden with APOBEC3-type changes has passed through humans repeatedly; one without has not. That answers the sustained-transmission-versus-repeated-spillover question from sequence alone, without contact data — though it speaks to the lineage's cumulative history, not to how this particular case was infected."),
 ("What is the main methodological fragility of an APOBEC3-driven clock?",
  ["The signature cannot be distinguished from sequencing error at low coverage",
   "APOBEC3 mutations revert at a high rate, erasing the signal over time",
   "The mutations are context-dependent and bursty, violating standard substitution models",
   "The enzyme edits only the terminal regions of the genome, which are usually trimmed"], 2,
  "Every standard model assumes substitutions are independent draws from a common process. APOBEC3 mutations are concentrated in TC context, occur in bursts and depend on strand exposure. Fitting a conventional model works well enough to be useful and is a known, open problem."),
 ("Clade Ib shows low overall genetic diversity plus a shared large deletion. What does that combination indicate?",
  ["A slowly evolving virus sampled over a short window",
   "Extensive recombination between co-circulating lineages homogenising the population",
   "Repeated independent introductions from a common animal source",
   "A single successful introduction into human networks followed by expansion"], 3,
  "Low diversity with a shared structural marker is the signature of recent common ancestry and rapid expansion from one introduction. Distinguishing this from 'slowly evolving virus' requires the clock — which is what APOBEC3 supplies."),
]

Q["lesson-22"] = [
 ("Cattle H5N1 sequences form a single monophyletic clade descending from a bird-derived ancestor. What does this establish?",
  ["A single spillover into cattle followed by cattle-to-cattle transmission",
   "Repeated spillovers from a single geographically restricted bird population",
   "That cattle are a dead-end host with no onward transmission",
   "That bird and cattle viruses have been co-evolving in the same ecosystem"], 0,
  "Repeated independent spillovers would place cattle sequences scattered among bird sequences, each with its own recent bird ancestor. One clade means one successful jump — and it redirected the response from environmental biosecurity to cattle movement control."),
 ("Why could the H5N1 cattle finding not be expressed as 'H5N1 spilled into cattle'?",
  ["H5N1 is a serological designation and cannot be assigned from sequence data",
   "Subtype names are conventionally reserved for influenza viruses circulating in avian rather than mammalian hosts",
   "Thousands of distinct viruses share that subtype, so it cannot identify one reassortant",
   "H5N1 refers to the whole genome whereas the finding concerned only the polymerase genes"], 2,
  "H5N1 names two surface proteins; clade 2.3.4.4b names a haemagglutinin clade. The finding is about one specific combination of lineages across all eight segments, which only a genotype name — B3.13 — can carry."),
 ("A second, independent H5N1 genotype (D1.1) entered dairy cattle in January 2025. What does this show about the earlier single-spillover finding?",
  ["It was incorrect, and the cattle clade must have contained multiple introductions",
   "It was correct as a description of the past but did not bound future spillovers",
   "It was an artefact of insufficient wild bird sequencing at the time",
   "It applied only to the herds in the states affected during the first wave, and not to subsequent introductions"], 1,
  "Phylogenetic reconstruction describes what happened. Reading 'one spillover' as 'spillover is rare' is the error — and continued genomic surveillance is what caught the second event. A programme that stood down after the first finding would have missed it."),
 ("What bounds the confidence in the single-spillover conclusion?",
  ["The number of cattle sequences generated during the response",
   "The choice of discrete trait rather than structured coalescent phylogeography",
   "The completeness of wild bird reservoir sequencing",
   "The absence of a molecular clock calibration for bovine-adapted lineages"], 2,
  "Under-sampling the source population makes multiple similar introductions collapse into one apparent clade. Bird surveillance is far less dense than cattle response sequencing became, so the honest reading is one dominant introduction that established, plus any that did not establish or were not sampled."),
]

Q["lesson-23"] = [
 ("Why is malaria genomic surveillance mostly a marker discipline rather than a tree discipline?",
  ["Plasmodium genomes are too large to align across many samples",
   "Sexual recombination in the mosquito means no single tree describes the genome",
   "Parasite DNA cannot be recovered at sufficient depth from routine blood samples",
   "Malaria transmission is too slow for phylogenetic resolution at outbreak scale"], 1,
  "Recombination every transmission cycle shreds linkage, so different genomic regions have different histories. Combined with frequent multi-clone infections, consensus-based tree reasoning is compromised at the root — while the urgent questions are answerable from a handful of positions."),
 ("What makes the WHO TB mutation catalogue the model artefact for marker surveillance?",
  ["It is updated continuously, incorporating each new resistance mutation as it is reported anywhere in the literature",
   "It covers every anti-TB medicine in current clinical use worldwide, including those still in trial phases",
   "It is a genotype-phenotype association study at scale, with graded confidence per mutation",
   "It replaces phenotypic drug susceptibility testing entirely for the drugs it covers"], 2,
  "Built from over 52,000 isolates with matched whole genome sequencing and phenotypic testing, grading mutations for 13 medicines, it constructs the mutation-to-phenotype bridge explicitly and once, for everyone. It does not replace phenotypic testing, which remains needed for discordance and discovery."),
 ("Why does a 'susceptible' genotypic result not guarantee a susceptible organism?",
  ["Consensus genomes average across the bacterial population and cannot detect resistance mutations at all",
   "Catalogues are updated too infrequently to include recent mutations",
   "Genotypic testing has lower analytical sensitivity than culture-based methods",
   "Resistance mechanisms not yet in the catalogue produce resistant organisms with susceptible genotypes"], 3,
  "Efflux, unknown loci and epistatic combinations all produce phenotypic resistance invisible to a marker panel. Genotypic susceptibility prediction has sensitivity below 1, which is precisely why phenotypic testing is not obsolete."),
 ("A national survey reports 8% pfhrp2/3 double deletions among isolates from a referral hospital treating suspected treatment failures. What is the problem with using this to trigger a national RDT switch?",
  ["Referral isolates are not a random sample, so the national prevalence is likely inflated",
   "Eight percent is below all published action thresholds for RDT replacement",
   "Reliable deletion calling requires whole genome rather than targeted sequencing, which this survey did not perform",
   "Double deletions must always be confirmed by protein-level testing before any programmatic action is taken"], 0,
  "A frequency is a proportion and needs a representative sampling frame. Isolates enriched for treatment failure are enriched for exactly the phenotype under study, and using them for a national estimate can trigger an expensive and unnecessary procurement change."),
 ("What is the principal advantage of targeted NGS from sputum over whole genome sequencing from culture in TB?",
  ["It detects a broader set of resistance mechanisms including unknown loci",
   "It produces a complete closed genome that is also suitable for downstream transmission analysis",
   "No culture wait, works on paucibacillary specimens, and detects minority resistant populations",
   "It requires no reference catalogue for interpretation of results"], 2,
  "tNGS amplifies a defined panel directly from specimen and sequences it deeply. That removes the culture delay, works where bacillary load is low, and reaches heteroresistance that a consensus genome hides. It covers fewer loci than WGS, not more."),
]

Q["lesson-24"] = [
 ("Why is a consensus genome meaningless for a wastewater sample?",
  ["RNA degradation during transit through the sewer network makes individual base calls unreliable at any sequencing depth",
   "The majority base across co-circulating lineages produces a sequence matching no real virus",
   "Sewage samples contain too little viral material to reach consensus depth",
   "Inhibitors carried through from wastewater bias the polymerase systematically toward incorporating reference bases"], 1,
  "The sample is a mixture from everyone infected in the catchment. Position-by-position majority calling across several lineages yields a chimera corresponding to no actual virus. The analytical object must change to deconvolution — which mixture of known lineages explains the observed allele frequencies."),
 ("What is the central limitation of lineage deconvolution tools such as Freyja?",
  ["They require uniform coverage across the whole genome, which degraded wastewater RNA can very rarely provide",
   "They cannot distinguish lineages differing by fewer than five defining mutations",
   "They are restricted to SARS-CoV-2 and cannot be extended to other pathogens",
   "They assign abundance against a reference set, so genuinely novel lineages are missed"], 3,
  "Deconvolution matches observed mutation frequencies against profiles of known lineages. A novel lineage with no profile appears as unexplained variation or gets misassigned to its nearest known relative — so wastewater detects arrival of the known well and emergence of the unknown poorly."),
 ("Why is poliovirus environmental surveillance described as the template for wastewater genomics?",
  ["It was the first application to use next-generation sequencing on sewage",
   "Poliovirus sheds at higher and more consistent rates than other pathogens",
   "The pathway from detection to public health action is fully built and used",
   "Poliovirus deconvolution is the one application that requires no reference lineage set"], 2,
  "The technical achievement matters less than the operational one: detection of circulating vaccine-derived poliovirus in populations with no paralytic cases leads to a defined response. Most newer multi-pathogen wastewater applications have no agreed action threshold and no named decision-maker, which by this course's test makes them research."),
 ("What most limits routine use of metagenomic sequencing for surveillance, as opposed to diagnosis?",
  ["The sequencing depth achievable per sample on current short-read platforms",
   "The absence of a defined sampling frame, plus cost and interpretation difficulty",
   "Regulatory prohibition on sequencing without a named target organism",
   "Inability to detect RNA and DNA pathogens in the same run"], 1,
  "Sequencing whatever arrives from whoever was investigated is a case series, not surveillance. Add consumables costs of hundreds to thousands per sample and the difficulty of separating pathogen from commensal, contaminant and index-hopped read, and the obstacle is not the sequencing."),
]


Q["lesson-25"] = [
 ("Tbg1 is clonal, monophyletic and genetically homogeneous. Which of the four questions does that rule out?",
  ["Only question 3, since growth rate estimation is the most data-hungry of the four",
   "Questions 1 and 3 — linkage and chains, and phylodynamic growth estimation",
   "None of them; low diversity is a sampling problem that deeper sequencing resolves",
   "Question 4, because marker detection requires background population diversity"], 1,
  "Linkage and phylodynamics both need diversity that this population does not have, at any sequencing depth. Question 4 — subspecies identification, resistance markers, diagnostic-target integrity — is where the value is, and question 2 works only against a historical baseline."),
 ("Trypanosome DNA was found in the blood of 9% of unconfirmed seropositive individuals but in the skin of 41% of them. What does that imply for surveillance?",
  ["Serological screening is producing a high false-positive rate that skin sampling corrects",
   "Skin sampling should replace parasitological confirmation in the diagnostic algorithm",
   "The standard specimen misses much of the reservoir in exactly the untreated group",
   "Dermal parasites are a post-treatment phenomenon and do not affect transmission"], 2,
  "Unconfirmed seropositives are not treated, and blood — the standard specimen — misses most of them while skin finds a large fraction. The sampling frame and the reservoir sit in different tissues, which is a Lesson 3 problem of the first order."),
 ("Why is a discrete trait analysis the wrong tool for the gHAT animal reservoir question?",
  ["Host species is a categorical variable and DTA requires continuous traits",
   "Cross-species transitions violate the time-reversibility assumption of the trait model",
   "Animal isolates come from too many species to form a single deme",
   "Human sampling vastly outnumbers animal sampling, so it will infer a human origin regardless"], 3,
  "DTA knows only how many sequences you supplied, not how many infections exist in each host. With decades of human screening against sparse animal surveys, the result is determined by the sample sizes before the data are examined. A structured coalescent, or an honest bound, is the alternative."),
 ("What is described as the highest-value genomic act available for gHAT today?",
  ["Whole genome sequencing of every confirmed case to build a transmission network",
   "Systematically archiving isolates and extracts from remaining foci, with metadata",
   "Re-sequencing the kinetoplast to expand the minicircle assay's target set",
   "Running a structured coalescent analysis on existing human and animal isolates"], 1,
  "Once a focus reaches zero, the only question that matters is whether a new case is an importation or residual transmission — and that is answerable only against a baseline collected before elimination. You cannot go back and sequence transmission you have successfully stopped."),
 ("Molecular identification of T. b. gambiense in pigs, dogs and duikers establishes what, precisely?",
  ["That an animal transmission cycle is maintained independently of human cases",
   "That these species are competent vectors for onward transmission to humans",
   "That animals can be infected — maintenance is a separate claim needing separate evidence",
   "That elimination of transmission by 2030 is no longer achievable"], 2,
  "Detection in a host is not maintenance by that host. Establishing a maintained cycle needs infectivity to tsetse, duration of infection, vector contact rates, and ideally transmission demonstrated in the absence of human cases. The experimental animal-Glossina-animal work is part of that argument, not all of it."),
 ("Why is acoziborole singled out as a resistance-surveillance priority?",
  ["It is the first oral treatment, and oral drugs select for resistance faster than injectables",
   "Its mechanism of action is unknown, so resistance cannot be predicted from the target",
   "Existing melarsoprol resistance markers are known to confer cross-resistance to it",
   "A single-dose drug given widely at very low case numbers hides emerging resistance in outcomes"], 3,
  "With a handful of cases per focus per year, treatment-outcome monitoring has almost no power to detect emerging resistance. That is precisely the situation where a marker programme, built on the graded genotype-phenotype catalogue model, earns its cost."),
]

# ---------------------------------------------------------------- exercises
# Procedure #11's graduated ladder, adapted for a course where execution is not
# the point. The recorded ladder is A conceptual · B read-the-output · C three-of-six
# with negative marking · D guided-and-scaffolded · E connect-to-your-work.
#
# One adaptation, stated so it is a choice rather than a drift: rung D in the
# recorded procedure is "guided R, scaffolded". This course explicitly does not
# teach execution — tool names appear so they are recognisable in a methods
# section, not so the reader runs them. So D here is a scaffolded *reading or
# arithmetic* task on the same material: most of the work is given, the learner
# changes or completes one specific thing and interprets it. Rung B is unchanged
# and is the most important one: in real work you meet somebody else's output
# long before you produce any of your own.
#
# E reuses each lesson's `practical`, so the open-ended rung is never missing.

EX = {}

EX["lesson-13"] = [
 {"type":"A","label":"Conceptual","prompt":"A programme sequences 300 samples a month and states it can detect a variant at 1% prevalence. Say why that is wrong in a knowable direction, and write the defensible version.",
  "guidance":"n \u2248 3/p gives ~300 for 1% \u2014 but only under simple random sampling from all infections. You sample from detected cases, so ascertainment enters; a new variant emerges locally rather than uniformly; and the Ct gate plus the coverage threshold remove low-load samples non-randomly. The defensible version states the assumed ascertainment fraction and sequencing success rate and reports detectable prevalence as a range rather than a point."},
 {"type":"B","label":"Read the output","prompt":"A surveillance system evaluation table. Answer the three questions.",
  "output":"stratum        cases   sequenced   seq/case   collection date   case ID link   outcome\n---------------------------------------------------------------------------------------\nCapital         1,204        601      0.499        100%             94%          88%\nProvince B        890         71      0.080         97%             31%          12%\nProvince C      2,140         44      0.021         62%              8%           2%\nProvince D        410          9      0.022         41%              0%           0%\n---------------------------------------------------------------------------------------\nNational        4,644        725      0.156         88%             62%          55%\n\nturnaround, collection to result:  median 9 d    75th 21 d    90th 48 d",
  "questions":[
   "The national metadata figures look tolerable. What do the strata show that the national row hides?",
   "Which single metadata column would most increase what this system can answer, and what class of question does it unlock?",
   "Interpret the turnaround distribution against a decision requiring an answer within two weeks."],
  "guidance":"The national row is dominated by the capital, which supplied 83% of sequences but 26% of cases. Everything degrades with distance from the capital, and the degradation is correlated across columns \u2014 the places with the fewest sequences also have the worst dates and no case linkage at all. Case ID link is the column to fix: it unlocks every clinical question \u2014 severity, outcome, vaccine effectiveness \u2014 none of which any number of genomes can answer without it. On turnaround: a 9-day median meets a two-week requirement, but the 90th percentile of 48 days does not, and the late tail will be the remote provinces, which are exactly where undetected transmission is most likely. Report the distribution, never the mean."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Targeted risk-based sampling is efficient for detection and unusable for estimating proportions.","correct":True},
   {"text":"Recording the sampling frame on each sequence is among the highest-value metadata additions.","correct":True},
   {"text":"Substituting the laboratory receipt date for the collection date shifts all tips equally and cancels out.","correct":False},
   {"text":"Detecting a variant at 0.1% prevalence needs roughly 3,000 sequences under random sampling.","correct":True},
   {"text":"A system's representativeness is best summarised by the total number of genomes produced.","correct":False},
   {"text":"Sentinel sampling supports valid national lineage proportion estimates.","correct":False}],
  "guidance":"1, 2 and 4. The receipt-date shift is longer for remote areas, so it makes them appear systematically later and manufactures a centre-to-periphery spread pattern. Representativeness is sequences per case by stratum \u2014 the ratio, not the count. And sentinel sampling represents its catchments, so it is good for detecting change over time and poor for national proportions."},
 {"type":"D","label":"Scaffolded","prompt":"Match each objective to its frame and to the metadata field that most constrains it. Two rows are done.",
  "output":"objective                          frame                 constraining field\n-------------------------------------------------------------------------------\nnational lineage proportions       representative random  sampling frame  \u2713\ndetect a new variant early         targeted + sentinel    ______________\noutbreak reconstruction            ______________         ______________\nseverity of a lineage              ______________         outcome, vaccination  \u2713\nreservoir / One Health             ______________         ______________",
  "guidance":"Detect early: date and location, plus the clinical or diagnostic anomaly that triggered selection. Outbreak reconstruction: universal within the outbreak, constrained by collection date at real precision plus the case ID link. Severity: representative sampling plus case linkage \u2014 the frame matters as much as the outcome field, because a targeted set inflates severity. Reservoir: targeted across hosts, constrained by host species and geography, and the deciding issue is comparable intensity across hosts rather than absolute numbers."},
]

EX["lesson-14"] = [
 {"type":"A","label":"Conceptual","prompt":"Give the strongest argument you can for immediate open deposition, then the strongest against, then say what the 2026 Bundibugyo team actually did and why it gets most of both.",
  "guidance":"For: unsequenced or unshared regions do not merely leave gaps \u2014 they make phylogeographic inference actively wrong for everyone, so withholding degrades the science globally. Against: a researcher who does the fieldwork can be scooped by better-resourced analysts, local analytical capacity never develops, and sequences derive from human samples under national law and specific consent. What they did: posted the full analysis publicly on virological.org during the outbreak, while depositing the sequences under a restricted licence with named institutional contacts. The world could see the methods, the trees and the numbers in real time; control of the data stayed with the institution that generated it."},
 {"type":"B","label":"Read the output","prompt":"A database record for an outbreak dataset. Answer the three questions.",
  "output":"Platform         Pathoplexus\nDataset          BDBV_DRC_20260820   (PP_SS_3400.1)\nSequences        525\nLicence          RESTRICTED \u2014 contact required prior to use in advance of publication\nContacts         Dr T. Wawina-Bokalanga; Prof. P. Mbala-Kingebeni (INRB, Kinshasa)\nMetadata fields  collection_date, health_zone, host, specimen_type, ct_value\nHost reads       depleted (verified)\nRedistribution   permitted after restriction lifts",
  "questions":[
   "Compare this record's redistribution term with GISAID's, and say what each choice costs.",
   "'Host reads depleted (verified)' is a technical line with a legal meaning. What is it?",
   "Two metadata fields here are unusual and useful. Which, and what do they let a reader do?"],
  "guidance":"Pathoplexus permits redistribution once the restriction lifts, so reproducible analyses can eventually ship their input data; GISAID prohibits it permanently, which is a real reproducibility cost paid in exchange for having got data shared at speed from countries that would not have used a fully open database. Host read depletion matters because clinical samples contain human nucleic acid, which is identifiable and regulated as personal data \u2014 depositing without depletion is a data-protection incident, and the step falls in the gap between the bioinformatician and the data protection officer. The unusual fields are specimen_type and ct_value: specimen type reveals that oral fluid from deceased patients is in the dataset, and Ct lets a reader reconstruct the load-based selection rather than take the sampling frame on trust."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"The Cali Fund is a multilateral mechanism for benefit sharing from use of digital sequence information.","correct":True},
   {"text":"The WHO Pandemic Agreement's PABS annex was adopted in May 2026 and is in force.","correct":False},
   {"text":"Public research and academic institutions are not expected to make monetary contributions to the Cali Fund.","correct":True},
   {"text":"Sequencing equity is an ethical consideration layered on top of otherwise sound methods.","correct":False},
   {"text":"Africa CDC's Africa PGI expanded sequencing capacity from 7 African Union member states in 2019 to 46 by late 2025.","correct":True},
   {"text":"Rich metadata reduces re-identification risk by diluting any single identifying field.","correct":False}],
  "guidance":"1, 3 and 5. PABS negotiations were extended through 2026 with a final outcome due at the World Health Assembly in May 2027. Equity is a precondition for correct inference, not a supplement to it \u2014 empty regions make the model wrong, not merely incomplete. And rich metadata increases re-identification risk: in a small health zone, sex, age, village and onset date together are identifying."},
 {"type":"D","label":"Scaffolded","prompt":"A submission checklist with three items completed. Fill the rest, then answer the last line.",
  "output":"  1. Platform chosen ......... ______________  because ______________\n  2. Metadata deposited ...... collection_date, location, host, specimen  \u2713\n  3. Human reads ............. depleted and verified  \u2713\n  4. Terms stated ............ ______________\n  5. Generators cited ........ yes, originating and submitting laboratories  \u2713\n  6. Analysis published ...... ______________\n\n  If a group in another country analyses and publishes this tomorrow,\n  my institution's position is: ______________",
  "guidance":"Platform: for outbreak sequences you need to control while your own team analyses them, Pathoplexus with a restricted period; for routine or retrospective work, INSDC. Terms: state the restriction, state until when, and name a contact. Analysis: publish it even while sequences are restricted \u2014 virological.org, a preprint, a Nextstrain build, a national bulletin. The last line is the one to answer before it happens rather than after; an institution that has not decided will decide badly and under pressure."},
]

EX["lesson-15"] = [
 {"type":"A","label":"Conceptual","prompt":"Name three genomic surveillance activities you have seen proposed or funded that would fail question 1 of the so-what test, and say what should have happened to each.",
  "guidance":"The pattern to look for is any activity whose stated purpose is \u2018improve understanding\u2019, \u2018build capacity\u2019 or \u2018characterise circulating diversity\u2019 with no named decision and no named decision-maker. None of those is illegitimate \u2014 they are research, or infrastructure \u2014 and each should have been funded, staffed and evaluated as such, with research outputs rather than surveillance metrics."},
 {"type":"B","label":"Read the output","prompt":"An annual report from a genomic surveillance programme. Answer the three questions.",
  "output":"GENOMIC SURVEILLANCE PROGRAMME \u2014 ANNUAL SUMMARY\n\n  Genomes sequenced ................ 8,412   (\u219131% on previous year)\n  Median turnaround ................ 6 days\n  Sequences deposited .............. 8,201 (97.5%)\n  Publications ..................... 4 peer-reviewed, 11 preprints\n  Staff trained .................... 26\n  Cost per genome .................. \u20ac41  (\u219318%)\n\n  Decisions changed ................ not recorded",
  "questions":[
   "Every metric here is an input except one absence. Rewrite the top line of this report as it should read.",
   "Cost per genome fell 18% and is presented as a success. Under what circumstance is that a failure?",
   "The programme is asked to justify its budget in a contracting fiscal year. Which single artefact, started a year ago, would have protected it?"],
  "guidance":"The top line should be decisions changed, logged with date, the genomic finding, and what would have happened otherwise. Everything above it is throughput. Falling cost per genome is a failure when it was achieved by sequencing more of the easy samples \u2014 high-load, capital-city, already-well-covered \u2014 because that improves the denominator while making representativeness worse; the honest denominator is cost per decision-relevant result, which is a much larger and much more useful number. The protective artefact is the decisions log: it is a small ongoing task and it is the only thing that answers the budget question in the programme's own terms."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Timeliness requirements should be derived backwards from the decision, not asserted generally.","correct":True},
   {"text":"A finding for an incident manager should always state what was not sequenced.","correct":True},
   {"text":"A mature programme rarely has to say that sequencing cannot answer a question.","correct":False},
   {"text":"Cost per genome is the appropriate denominator for judging programme value.","correct":False},
   {"text":"'No lineage dominance and no fitness-altering mutations' is a result that justifies continuing the current response.","correct":True},
   {"text":"If a result would arrive after the decision point, it retains most of its value as a retrospective record.","correct":False}],
  "guidance":"1, 2 and 5. A mature programme declines questions regularly; one that always finds something is over-interpreting. Cost per genome rewards volume. And a result arriving after the decision has zero value for that decision and non-zero cost \u2014 retrospective value is a different and much weaker claim that should be argued, not assumed."},
 {"type":"D","label":"Scaffolded","prompt":"Turn a finding into an incident-management brief. The finding is given; write the four sentences.",
  "output":"Finding: 47 sequences from Health Zone A form a single cluster within two\n         substitutions, dating to mid-June. 12 of the 59 reported cases in\n         that zone were not sequenced. Sequences from neighbouring Health\n         Zone B are sparse (n=6).\n\n  1. What we found: ______________________\n  2. What it means: ______________________\n  3. What it does NOT mean: ______________________\n  4. Recommendation and confidence: ______________________",
  "guidance":"1: the 47 sequenced cases from Health Zone A form a single closely related group dating to mid-June. 2: consistent with a single introduction followed by local transmission, rather than repeated importation from Health Zone B. 3: it does not identify who infected whom, and 12 of 59 reported cases in the zone were not sequenced. 4: concentrate contact tracing within Health Zone A rather than at the boundary; moderate confidence, because the conclusion depends on Health Zone B sequences, of which there are six. Note that the confidence word is calibrated and the reason for it is given in the same sentence."},
]

EX["lesson-20"] = [
 {"type":"A","label":"Conceptual","prompt":"The Bundibugyo analysis reports a negative finding \u2014 no fitness-altering mutations, no lineage dominance. Explain to a response coordinator why that took as much work as a positive finding, and what it licenses them to do.",
  "guidance":"Establishing that nothing changed requires the same curation, the same clock, the same tree and the same diversity analysis as establishing that something did \u2014 plus the sensitivity analysis to show the result is not an artefact of curation or sampling. It licenses the response to keep doing what it is doing: with no licensed vaccine or therapeutic for this species, the response rests entirely on diagnostics, isolation and contact tracing, and this is the finding that says those three assumptions still hold."},
 {"type":"B","label":"Read the output","prompt":"The nested-truncation sensitivity analysis, as a table.",
  "output":"dataset ends   genomes   clock rate (subs/site/yr)   tMRCA (median)   HPD width (days)\n---------------------------------------------------------------------------------------\n2026-06-23        318            1.10e-3               2026-03-09            52\n2026-07-03        401            9.1e-4                2026-02-27            61\n2026-07-16        478            8.6e-4                2026-02-24            65\n2026-08-09        525            8.5e-4                2026-02-22            67",
  "questions":[
   "Describe what happens to the clock rate across the four datasets and give the reason.",
   "The HPD width grows as more data are added. Is that the wrong way round?",
   "What does this table license the authors to say, and what does it not license?"],
  "guidance":"The clock rate falls from 1.10e-3 and converges on ~8.5e-4. A short sampling window over-estimates the rate, because the temporal signal is thin and the estimate is dominated by whatever divergence happens to be in the earliest and latest tips; adding weeks of range stabilises it. The widening HPD is not wrong: as the tMRCA is pushed earlier, it moves further from the data, and a longer extrapolation carries more uncertainty \u2014 the point estimate stabilising while the interval honestly widens is exactly what you want to see. It licenses the claim that the recent inferences are not an artefact of where the data were cut. It does not license any claim about bias that ran in the same direction throughout, which is why the authors separately flag possible missing diversity in the first two months of 2026."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"The 32 excluded genomes were removed for a mechanistic reason, before the statistical outlier filter ran.","correct":True},
   {"text":"The root-to-tip slope of 7.9e-4 was used as the prior for the Bayesian clock estimate.","correct":False},
   {"text":"525 of 3,748 reported cases were analysed, and reported cases are themselves a fraction of infections.","correct":True},
   {"text":"Bundibugyo virus is a variant of Zaire ebolavirus, so ERVEBO offers partial protection.","correct":False},
   {"text":"SkyGrid's 31 transition points at weekly intervals were chosen to match the serial interval scale.","correct":True},
   {"text":"The post reports ESS values and chain convergence diagnostics.","correct":False}],
  "guidance":"1, 3 and 5. The root-to-tip slope was an independent cross-check, not a prior \u2014 a heuristic validating itself would be circular. Bundibugyo virus is a distinct SPECIES, which is precisely why there is no licensed vaccine or specific therapeutic for it. And ESS and convergence are not reported, which is understandable in a work-in-progress post and is the first thing to look for in the published version."},
 {"type":"D","label":"Scaffolded","prompt":"Each phrase from the post is paired with the lesson that decodes it. Three are filled in; complete the rest and add what it would cost to get each wrong.",
  "output":"  phrase                                   lesson   cost of getting it wrong\n  ------------------------------------------------------------------------------\n  all PCR-positive with Ct < 31              L3      unstated load-based selection\n  32 excluded for ADAR signatures            L2      inflated clock, spurious branches\n  GTR+F+R3 via ModelFinder                   L8      biased branch lengths\n  tree rooted to minimise residuals          ___     ______________________\n  small branches collapsed to zero           ___     ______________________\n  SkyGrid, 31 points, 32-week cutoff         ___     ______________________\n  Pathoplexus, restricted licence            ___     ______________________",
  "guidance":"Rooting \u2192 L8; get it wrong and you invert the direction of time, so the source becomes the destination. Collapsed branches \u2192 L7; get it wrong and you draw a fully resolved tree from branches resting on no evidence, then argue from its fine structure. SkyGrid \u2192 L10; too coarse and you smooth away the feature, too fine and the smoothing prior rather than the data draws the curve. Pathoplexus \u2192 L14; get it wrong and you either lose control of your own outbreak data or withhold it in a way that degrades everyone's phylogeography."},
]

EX["lesson-21"] = [
 {"type":"A","label":"Conceptual","prompt":"State the general rule for deciding whether a host editing process is your clock or your artefact, then apply it to a hypothetical: a virus with a viral substitution rate of 4 substitutions per genome per year showing a clear APOBEC3 signature.",
  "guidance":"Ask first whether the pathogen's own clock is adequate for the question. If it is, the editing is noise and you filter it; if it is not, the editing may be your only signal and you must model it, or at minimum say out loud that you did not. At 4 substitutions per genome per year and, say, a two-week serial interval, that is ~0.15 per transmission \u2014 marginal. You would probably filter for the tree and report the editing separately as evidence of host passage, rather than letting it drive the clock."},
 {"type":"B","label":"Read the output","prompt":"Mutation spectra for four mpox genomes relative to a clade I reference.",
  "output":"genome    total   C>T(TC ctx)   C>T(other)   other subs   large deletions\n-------------------------------------------------------------------------\nMPX-101     64         51             6            7        1 (1,142 bp)\nMPX-102     58         46             5            7        1 (1,142 bp)\nMPX-103      3          0             1            2        none\nMPX-104     71         55             8            8        1 (1,142 bp) + terminal",
  "questions":[
   "What does the C>T(TC context) column let you say about MPX-101, 102 and 104 that no epidemiological data was needed for?",
   "MPX-103 has three substitutions total. Give the two competing interpretations.",
   "The 1,142 bp deletion is shared by three of the four. What kind of marker is that, and why is it more informative here than most individual substitutions?"],
  "guidance":"The APOBEC3 signature is a direct sequence-only test of human passage: a genome carrying many TC-context C>T changes has been transmitting person to person rather than sitting in an animal reservoir. That answered the question that mattered in eastern DRC without contact data. MPX-103 is either a recent zoonotic introduction that has passed through few or no humans, or a sequencing or sampling artefact \u2014 check coverage and controls before concluding the former. The deletion is a structural lineage marker, and in a large genome with a very low point-mutation rate a shared structural variant carries more phylogenetic information than most individual substitutions do."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"APOBEC3 deaminates cytosine in single-stranded DNA, producing C>T changes enriched in TC context.","correct":True},
   {"text":"An APOBEC3-driven clock rate is a property of the virus and transfers between transmission networks.","correct":False},
   {"text":"Standard substitution models assume independence that APOBEC3 mutations violate.","correct":True},
   {"text":"Clade Ib's low genetic diversity indicates a slowly evolving virus rather than a recent expansion.","correct":False},
   {"text":"High APOBEC3 content shows the lineage has passed through humans, not how this case was infected.","correct":True},
   {"text":"Orthopoxvirus baseline substitution rates are adequate for outbreak-scale epidemiology.","correct":False}],
  "guidance":"1, 3 and 5. The rate reflects host APOBEC3 exposure, which may differ by transmission route, tissue and individual. Low diversity plus a shared deletion is the signature of recent common ancestry and rapid expansion from a single introduction \u2014 and distinguishing that from \u2018slowly evolving\u2019 is exactly what the clock is needed for. Baseline orthopoxvirus rates are ~0.2 substitutions per genome per year, which is unusable."},
 {"type":"D","label":"Scaffolded","prompt":"Complete the comparison table, then write the one-sentence rule it encodes.",
  "output":"                        mpox / APOBEC3        filovirus / ADAR\n  host process          ______________        ______________\n  signature             C>T (TC context)      ______________\n  viral clock without   ~0.2 subs/genome/yr   ______________\n  therefore             ______________        ______________\n\n  Rule: ______________________",
  "guidance":"APOBEC3: cytosine deamination in ssDNA. ADAR: adenosine deamination in dsRNA, appearing as T>C in short consecutive spans on the strand filovirus genomes are written on. Filovirus viral clock: ~16 substitutions per genome per year, which is adequate. Therefore: use APOBEC3 as the clock and as a test of human passage; remove ADAR as an artefact before estimating anything. Rule: the same class of host biology is signal or noise depending entirely on whether the pathogen has an adequate clock of its own."},
]

EX["lesson-22"] = [
 {"type":"A","label":"Conceptual","prompt":"The single-spillover finding was correct and a programme that stood down after it would have missed the second introduction. Explain the reasoning error in one sentence, then say what it implies about how surveillance findings should be worded.",
  "guidance":"Reading \u2018one spillover happened\u2019 as \u2018spillover is rare\u2019 confuses a reconstruction of the past with a bound on the future. Findings should be worded with their tense visible \u2014 \u2018the cattle sequences descend from a single introduction in late 2023\u2019 rather than \u2018H5N1 entered cattle once\u2019 \u2014 because the second phrasing quietly licenses a decision to stop looking."},
 {"type":"B","label":"Read the output","prompt":"Segment-level lineage assignments for six influenza A isolates.",
  "output":"isolate   host     PB2    PB1    PA     HA        NP    NA    M     NS    genotype\n-------------------------------------------------------------------------------------\nA-001     cattle   am1.1  am1.2  am2.1  2.3.4.4b  am3   ea1   am4   am5   B3.13\nA-002     cattle   am1.1  am1.2  am2.1  2.3.4.4b  am3   ea1   am4   am5   B3.13\nA-003     cattle   am1.1  am1.2  am2.1  2.3.4.4b  am3   ea1   am4   am5   B3.13\nA-004     cat      am1.1  am1.2  am2.1  2.3.4.4b  am3   ea1   am4   am5   B3.13\nA-005     cattle   am6.2  am7.1  am8.3  2.3.4.4b  am9   ea1   am10  am11  D1.1\nA-006     wild bird am6.2 am7.1  am8.3  2.3.4.4b  am9   ea1   am10  am11  D1.1",
  "questions":[
   "All six are H5N1 clade 2.3.4.4b. Why is that name useless for the epidemiological question here?",
   "A-004 is from a cat and carries B3.13. What does that represent, and what does it change about the risk assessment?",
   "A-005 and A-006 share a genotype and differ in host. What are the two readings, and what would distinguish them?"],
  "guidance":"Every isolate here shares the subtype and the HA clade, so neither name distinguishes the two events \u2014 only the genotype, a combination across all eight segments, can. A-004 is spillback: a lineage exiting the cattle clade into another species, which means cattle have become a source rather than only a sink, and that is a change in the risk assessment rather than a detail. A-005 and A-006 could represent a fresh bird-to-cattle introduction (the D1.1 event of January 2025) or cattle-to-bird transmission; the tree topology distinguishes them \u2014 whether the cattle sequence is nested inside bird diversity or sits basal to it \u2014 and the confidence depends entirely on how densely the bird reservoir was sampled."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"A single monophyletic clade of cattle sequences is consistent with one successful cross-species jump.","correct":True},
   {"text":"Genotype names are needed for influenza because segments reassort independently.","correct":True},
   {"text":"PB2 M631L being fixed across the cattle clade proves it increases mammalian transmissibility.","correct":False},
   {"text":"Dense sampling of the cattle population is what bounds confidence in the single-spillover conclusion.","correct":False},
   {"text":"The virus spread between states through movement of asymptomatic or presymptomatic animals.","correct":True},
   {"text":"Host-state reconstruction is a fundamentally different method from geographic phylogeography.","correct":False}],
  "guidance":"1, 2 and 5. A fixed adaptation marker is a hypothesis about phenotype; the inference that it matters rests on experimental work in cells and animals, not on its presence in a tree. Statement 4 inverts the real limitation: it is sampling of the SOURCE population, the wild birds, that bounds the conclusion, because under-sampling there makes several similar introductions collapse into one apparent clade. Cattle were sequenced densely and that is not what constrains the inference. And host-state reconstruction is the same machinery as geographic phylogeography with host substituted for location."},
 {"type":"D","label":"Scaffolded","prompt":"Apply the one-clade-versus-many logic to a reservoir question of your own. The frame is given.",
  "output":"  Pathogen: ______________   Suspected reservoir host: ______________\n\n  If maintained in the reservoir, I expect the tree to show: ______________\n  If repeated spillover from humans, I expect: ______________\n  Sampling I would need before either conclusion is safe: ______________\n  The bound I could honestly report with the sampling I actually have: ______________",
  "guidance":"Maintained: a monophyletic clade of reservoir-host sequences with its own internal diversity, and human sequences nested within or descending from it. Repeated spillback from humans: reservoir-host sequences scattered across human diversity, each with a recent human ancestor. The sampling you need is comparable intensity across hosts in the same foci over the same period \u2014 absolute numbers matter far less than the ratio. And the last line is the honest one: with human-dominated sampling, the report is a bound, not a point estimate."},
]

EX["lesson-23"] = [
 {"type":"A","label":"Conceptual","prompt":"Why is a curated, graded genotype-phenotype catalogue described as more valuable than any individual study in a marker programme, and what does its absence cost a pathogen that lacks one?",
  "guidance":"Because it builds the mutation-to-phenotype bridge once, explicitly, with stated confidence, for everyone \u2014 converting a sequence into a susceptibility prediction with a known evidence level. Without one, resistance markers are scattered across the literature at varying evidence quality with no grading, so every programme rebuilds the interpretation layer privately and inconsistently. Building the catalogue is the rate-limiting step for extending marker surveillance to a new pathogen, and it is unglamorous, expensive and worth more than another sequencer."},
 {"type":"B","label":"Read the output","prompt":"A targeted NGS resistance report from sputum. Answer the three questions.",
  "output":"Sample TB-2214    tNGS panel v3    mean depth 1,842x\n\ngene     variant        freq     WHO catalogue grade          drug\n---------------------------------------------------------------------\nrpoB     S450L          0.98     Assoc w R                    rifampicin\ninhA     -15C>T         0.96     Assoc w R                    isoniazid\nkatG     S315T          0.11     Assoc w R                    isoniazid\npncA     no variant       \u2014      \u2014                            pyrazinamide\nrrs      no variant       \u2014      \u2014                            amikacin\nRv0678   L117R          0.34     Uncertain significance       bedaquiline",
  "questions":[
   "katG S315T is present at 11%. What would a consensus genome have reported, and why does the difference matter clinically?",
   "Rv0678 L117R is graded 'uncertain significance'. What are you entitled to do with it?",
   "pncA shows no variant. State precisely what that does and does not tell you about pyrazinamide."],
  "guidance":"A consensus genome reports the majority base, so at 11% katG S315T would have been discarded entirely and the sample called katG-wild-type \u2014 while a resistant subpopulation is present and under treatment pressure will be selected. Heteroresistance is the clinical reason deep targeted sequencing exists. An uncertain-significance variant is not a resistance call: report it, flag it for phenotypic testing, and do not change the regimen on it alone \u2014 the graded confidence in the catalogue exists precisely to stop that. And absence of a known pncA variant means no catalogued resistance mechanism was detected; it does not mean the isolate is susceptible, because genotypic prediction has sensitivity below 1 and mechanisms outside the catalogue produce resistant organisms with 'susceptible' genotypes."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Recombination in the mosquito is why tree-based reasoning is weak for P. falciparum.","correct":True},
   {"text":"pfhrp2/3 deletions make parasites invisible to most HRP2-based rapid diagnostic tests.","correct":True},
   {"text":"The WHO TB mutation catalogue removes the need for phenotypic drug susceptibility testing.","correct":False},
   {"text":"WHO 2025 guidance places tNGS after initial automated NAATs, reserving WGS for discordance and surveillance.","correct":True},
   {"text":"A marker frequency from referral-hospital isolates is a valid national prevalence estimate.","correct":False},
   {"text":"Validated and candidate kelch13 mutations can be treated equivalently in a surveillance report.","correct":False}],
  "guidance":"1, 2 and 4. Phenotypic testing remains necessary for discordance resolution and for discovering what the catalogue lacks. Referral isolates from suspected treatment failures are enriched for the phenotype under study, so using them nationally inflates the estimate and can trigger an unnecessary and expensive procurement change. And the validated/candidate distinction is the operational content of the marker list \u2014 only validated markers trigger policy."},
 {"type":"D","label":"Scaffolded","prompt":"Complete the decision rule for a national programme. Two rows are done.",
  "output":"  marker            decision it feeds                     threshold  who decides\n  ----------------------------------------------------------------------------\n  pfhrp2/3 del      switch from HRP2 to pLDH RDTs          WHO-rec'd  NMCP  \u2713\n  kelch13 (valid.)  ______________________                 ______     ______\n  pfdhfr/pfdhps     ______________________                 ______     ______\n  rpoB (Assoc w R)  regimen selection for this patient     n/a        clinician  \u2713\n\n  For any marker, the result that would change the decision must be\n  stated ______________________",
  "guidance":"kelch13: change of first-line treatment, deployment of multiple first-line therapies or triple ACTs, and where to concentrate therapeutic efficacy studies \u2014 threshold set nationally against WHO guidance, decided by the national malaria control programme with the treatment policy committee. pfdhfr/pfdhps: whether intermittent preventive treatment in pregnancy with sulfadoxine-pyrimethamine remains viable \u2014 again a national policy decision. And the last line: stated in advance, before the data are seen. Deciding the threshold afterwards is interpretation, not surveillance."},
]

EX["lesson-24"] = [
 {"type":"A","label":"Conceptual","prompt":"Explain why wastewater surveillance is good at detecting the arrival of something known and poor at detecting the emergence of something new \u2014 which is close to the inverse of what most people assume.",
  "guidance":"Because the analysis is deconvolution against a reference set of lineage-defining mutation profiles. A lineage already in that set is matched and quantified well. A genuinely novel lineage has no profile, so it appears as unexplained variation, a poor fit, or gets misassigned to its nearest known relative. And the reference set is built from clinical sequencing, so wastewater inherits the clinical system's blind spots in its database even while escaping the clinical system's sampling cascade in its sample."},
 {"type":"B","label":"Read the output","prompt":"A Freyja demix result for one wastewater sample.",
  "output":"site WW-07   collection 2026-08-19   coverage 61.4% at >=10x\n\nlineage        abundance   95% CI\n---------------------------------------\nXBB.1.5           0.412     0.35-0.47\nXBB.1.16          0.238     0.18-0.30\nBA.2.86           0.161     0.10-0.22\nJN.1              0.094     0.04-0.15\nresidual          0.095       \u2014\n\nfit summary: sum of squared residuals 0.031 (site median 0.008)",
  "questions":[
   "The residual is 9.5% and the fit is roughly four times worse than this site's median. Give two explanations and say which is more concerning.",
   "Coverage is 61.4%. What does that do to the confidence intervals, and why is low coverage normal here rather than a failure?",
   "Someone asks how many people in the catchment are infected. What do you say?"],
  "guidance":"Either a lineage present in the sample has no profile in the reference set \u2014 which is the interesting and concerning case, because it is what an emerging lineage looks like from the inside \u2014 or the data are simply noisy at this coverage. The elevated squared residual against the site's own median is what makes the first explanation worth chasing; a single sample cannot settle it, so look at the next few collections from the same site. Low coverage widens the intervals and is normal because wastewater RNA is degraded and coverage is patchy by nature, which is exactly why Freyja 2's robustness to low coverage matters. And on the last question: you say the signal is a trend instrument, not a counting instrument \u2014 shedding rates, dilution, rainfall, industrial discharge, temperature and transit time all stand between the measurement and a prevalence, and none is calibratable in practice."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Consensus calling on a wastewater sample produces a sequence corresponding to no real virus.","correct":True},
   {"text":"Poliovirus environmental surveillance is the template because its detection-to-action pathway is built and used.","correct":True},
   {"text":"Metagenomic sequencing is more sensitive than targeted PCR for pathogens the panel covers.","correct":False},
   {"text":"Wastewater surveillance escapes the clinical sampling cascade entirely, including in its reference database.","correct":False},
   {"text":"Separating a true pathogen from a commensal or reagent contaminant is the hard part of clinical metagenomics.","correct":True},
   {"text":"Pathogen-agnostic diagnosis and pathogen-agnostic surveillance are the same activity at different scales.","correct":False}],
  "guidance":"1, 2 and 5. Metagenomics is markedly less sensitive than targeted methods for targets those methods cover \u2014 its advantage is entirely in what they do not cover. The sample escapes the clinical cascade; the reference lineage set does not, because it is built from clinical sequencing. And diagnosis is a clinical service on whoever was investigated, while surveillance needs a defined sampling frame \u2014 sequencing whatever arrives is a case series."},
 {"type":"D","label":"Scaffolded","prompt":"Assess a proposal using the so-what test adapted for a new modality. Two lines are filled.",
  "output":"  Proposal: multi-pathogen wastewater sequencing at 12 sites, monthly\n\n  1. Decision it could change ......... ______________________\n  2. Result that would change it ...... ______________________\n  3. By when ......................... within one reporting month  \u2713\n  4. Confidence and sampling ......... trend only, not prevalence  \u2713\n\n  Verdict: surveillance or research? ______________  because ______________",
  "guidance":"If lines 1 and 2 can be filled \u2014 for example, 'detection of poliovirus in any site triggers a supplementary immunisation assessment within 14 days, decided by the national EPI programme' \u2014 it is surveillance. If they cannot, it is research, which is legitimate and should be funded and evaluated as research. For most multi-pathogen wastewater applications today there is no agreed action threshold and no named decision-maker, which is the honest verdict: technically demonstrated, operationally immature."},
]

EX["lesson-25"] = [
 {"type":"A","label":"Conceptual","prompt":"A funder proposes sequencing every remaining gHAT case to reconstruct the transmission network in the last endemic foci. Respond in three sentences: what you would say no to, what you would say yes to, and why the arithmetic settles it before any money is spent.",
  "guidance":"No to the transmission network: Tbg1 is clonal and monophyletic, so there is not enough diversity to resolve chains or clusters at any sequencing depth, and no amount of money changes that. Yes to a resistance-marker programme as acoziborole scales, to subspecies confirmation, and above all to systematic archiving from every remaining focus. The arithmetic settles it because rate \u00d7 genome length \u00d7 serial interval, or in this case simply the observed absence of population structure, tells you the resolution limit before the first sample is collected."},
 {"type":"B","label":"Read the output","prompt":"An inventory of what one national programme currently holds for a focus approaching zero.",
  "output":"Focus: Bandundu-N     last reported case 2024-11    active screening: suspended 2025-06\n\n  material held            n      earliest   latest    metadata completeness\n  --------------------------------------------------------------------------\n  CATT/RDT serology cards  4,410   2009      2024      date 96%, village 91%\n  Thick blood films        1,882   2009      2024      date 88%, village 74%\n  Dried blood spots          311   2019      2024      date 92%, village 88%\n  Skin snips                   0      \u2014         \u2014      \u2014\n  Cryopreserved isolates       6   2011      2016      date 100%, village 100%\n  Extracted DNA               47   2019      2024      date 90%, village 85%\n  Sequences (any)              0      \u2014         \u2014      \u2014",
  "questions":[
   "A case appears in this focus in 2029. Which row decides whether you can answer 'import or residual', and is it sufficient?",
   "One row is zero and, given what is known about where the parasite sits, that is the most consequential gap. Which, and why?",
   "What would you change about collection practice tomorrow, given that active screening is suspended?"],
  "guidance":"The extracted DNA and dried blood spots are the only material from which a baseline could still be generated, and 47 extracts plus 311 spots from a five-year window is thin but not nothing \u2014 the six cryopreserved isolates are older and too few. It is not sufficient, and the answer in 2029 will be a weak one. The zero that matters is skin snips: the dermal reservoir carries parasites in up to 41% of unconfirmed seropositives whose blood is negative, so a blood-only bank misses the compartment most relevant to the infections that sustained transmission. Tomorrow: sequence the 47 extracts now rather than banking them unsequenced, add skin snips to any residual passive case detection, and attach the Lesson 13 minimum metadata \u2014 because with screening suspended, the number of future opportunities to collect is small and falling."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Tbg1 forms a monophyletic, genetically homogeneous group on genome-wide SNPs.","correct":True},
   {"text":"Detection of T. b. gambiense in pigs and duikers establishes an animal-maintained transmission cycle.","correct":False},
   {"text":"The kinetoplast minicircle assay is an example of sequencing used once to design a field PCR.","correct":True},
   {"text":"Trypanosomes can persist in the dermis and be transmitted to tsetse without detectable parasitaemia.","correct":True},
   {"text":"Deeper sequencing would allow transmission chains to be resolved in gHAT.","correct":False},
   {"text":"Whole genome sequencing showed that gHAT relapse is due to reinfection rather than parasite regrowth.","correct":False}],
  "guidance":"1, 3 and 4. Detection in a host establishes infection, not maintenance \u2014 that needs infectivity to tsetse, duration, vector contact rates and ideally transmission in the absence of human cases. Depth cannot create diversity that does not exist. And the WGS finding was the opposite: relapse is regrowth of the original population, which is a statement about drug efficacy and follow-up duration rather than transmission."},
 {"type":"D","label":"Scaffolded","prompt":"Write the archive specification. Three lines are given.",
  "output":"  Purpose: answer 'import or residual' for a case arising after elimination\n\n  Materials to bank ....... ______________________\n  Compartments ............ blood AND ______________  because ______________\n  Metadata (minimum) ...... collection date at real precision, focus,\n                            health zone, host species, specimen type,\n                            link to case record  \u2713\n  Timing .................. while cases still exist  \u2713\n  What is lost each year of delay: one year of baseline, permanently  \u2713\n\n  The single sentence justifying the budget: ______________________",
  "guidance":"Materials: cryopreserved isolates where possible, dried blood spots, extracted DNA, and sequences generated now rather than banked unsequenced \u2014 because a bank nobody has sequenced is a bank whose contents are unknown. Compartments: blood and skin, because the dermal reservoir holds parasites in a large fraction of unconfirmed seropositives whose blood is negative, and those are the untreated infections most likely to have sustained transmission. Budget sentence: 'once this focus is declared free, the only question that will matter is whether a new case is imported or residual, and that question is answerable only against a baseline that has to be collected now \u2014 you cannot go back and sequence transmission you have successfully stopped.'"},
]

EX["lesson-07"] = [
 {"type":"A","label":"Conceptual","prompt":"A colleague points at two tips adjacent on a printed tree and says \u201cthese two must be linked \u2014 look how close they are.\u201d Give the shortest correct correction, then the longer one.",
  "guidance":"Short: vertical position is a drawing convention; the tree can be rotated at any node without changing its meaning, so adjacency on the page carries no information. Longer: what carries information is the branching structure and the branch lengths, and even those give a tree of sequences rather than a tree of people \u2014 so \u2018linked\u2019 needs the local background distance and, ideally, epidemiological evidence."},
 {"type":"B","label":"Read the output","prompt":"A tree figure legend, exactly as submitted with a manuscript. Answer the three questions.",
  "output":"Figure 2. Maximum likelihood phylogeny of 214 genomes from the outbreak\n(IQ-TREE, GTR+F+G4). Tips coloured by health zone. Node support shown for\nselected nodes. Tree midpoint-rooted. Scale bar omitted for clarity.\n\n  Health zone   n sequenced   n cases reported\n  Bunia               141            612\n  Rwampara             48            409\n  Mongbwalu            21            755\n  Other (18 HZ)         4          1,972",
  "questions":[
   "Two things in the legend should stop you drawing any quantitative conclusion from the figure. What are they?",
   "The largest clade in the figure is from Bunia. What are the two competing explanations, and which does the table favour?",
   "The tree is midpoint-rooted. What does that assume, and is the assumption reasonable here?"],
  "guidance":"\u2018Scale bar omitted\u2019 means you cannot read branch lengths at all, so you cannot tell a divergence tree from a cladogram or judge any distance; and \u2018support shown for selected nodes\u2019 means support was reported where it was good. On the clade: intense Bunia transmission, or intense Bunia sequencing. Sequences per case are Bunia 0.23, Rwampara 0.12, Mongbwalu 0.03, elsewhere 0.002 \u2014 a hundredfold range, so sampling is the leading explanation and the figure cannot separate them. Midpoint rooting assumes a roughly constant rate across lineages; for a densely sampled time-stamped outbreak the defensible choice is clock-based rooting that minimises root-to-tip residuals."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"A multiple sequence alignment is a hypothesis of homology, not an observation.","correct":True},
   {"text":"Internal nodes in an outbreak phylogeny usually correspond to sampled index cases.","correct":False},
   {"text":"A polytomy can be an honest statement that the data cannot resolve the branching order.","correct":True},
   {"text":"Within-host diversity means lineages can diverge before the transmission event that separates two hosts.","correct":True},
   {"text":"With perfect sampling, the phylogenetic tree becomes the transmission tree.","correct":False},
   {"text":"Ladderised trees show an evolutionary progression from primitive to derived tips.","correct":False}],
  "guidance":"1, 3 and 4. Internal nodes are inferred ancestors, overwhelmingly from unsampled infections. Even perfect sampling would not make the two trees identical \u2014 the pre-transmission interval and the shortage of mutations per link both remain. And ladderisation is a layout choice; all tips are contemporary with their sampling dates and none is ancestral to another."},
 {"type":"D","label":"Scaffolded","prompt":"Work through the checklist on a tree you are shown. Four items are answered; complete the last two and say which one you would ask for first.",
  "output":"  1. Branch length units? ......... substitutions per site  \u2713\n  2. Rooted how? .................. outgroup (2012 BDBV isolate)  \u2713\n  3. Colours encode? .............. health zone  \u2713\n  4. Support on the key nodes? .... 61\u201374% UFBoot  \u2713\n  5. Sampling fraction by colour? . ______________________\n  6. Near-zero branches collapsed?  ______________________\n\n  Ask for first: ______________________",
  "guidance":"Item 4 is already disqualifying: UFBoot is read with 95% as the threshold, so 61\u201374% on the nodes carrying the argument means the argument is not supported. Item 5 is the one to ask for first anyway, because without sequences-per-case by health zone the geographic pattern may be entirely a sampling pattern, and that undermines the figure regardless of support. Item 6 matters because a fully bifurcating tree drawn from branches resting on a single mutation claims precision the data do not contain. Note also that rooting on a 2012 isolate is decades of divergence, which can distort branch lengths across the whole tree."},
]

EX["lesson-08"] = [
 {"type":"A","label":"Conceptual","prompt":"Why does an observed count of differences underestimate evolutionary distance, and why does that matter much less for a 100-day outbreak than for a cross-species comparison?",
  "guidance":"Multiple hits: a site that changed and changed back reads as no change, and two independent identical changes read as no difference. The longer the elapsed time, the worse the underestimate, until distance saturates. Over 100 days on one virus, almost no site has been hit twice, so the correction is small \u2014 which is why the substitution model matters far less in outbreak analysis than in deep phylogenetics, without ever being nothing."},
 {"type":"B","label":"Read the output","prompt":"The tail of an IQ-TREE log. Answer the three questions.",
  "output":"ModelFinder\n  Best-fit model according to BIC: GTR+F+R3\n  GTR+F+R3      -28114.902   BIC  56701.55\n  GTR+F+G4      -28129.771   BIC  56717.29\n  HKY+F+G4      -28390.114   BIC  57221.98\n  JC            -29874.556   BIC  60142.61\n\nRate parameters:  A-C 1.204  A-G 4.881  A-T 0.997  C-G 0.884  C-T 5.033  G-T 1.000\nBase frequencies: A 0.322  C 0.201  G 0.190  T 0.287\nSite proportion and rates:  (0.612,0.088) (0.310,1.271) (0.078,6.940)\n\nSH-aLRT and ultrafast bootstrap: 1000 replicates\n  Nodes with SH-aLRT >= 80% AND UFBoot >= 95%:  47 / 213",
  "questions":[
   "Read the rate parameters. What general feature of DNA substitution do they show, and which two entries carry it?",
   "The three site-rate classes are given as (proportion, rate). Describe the alignment they imply in one sentence.",
   "Only 47 of 213 nodes meet the joint support criterion. Is that a problem with the analysis?"],
  "guidance":"A-G 4.88 and C-T 5.03 are the two transitions, and they are about five times the transversion rates \u2014 the transition/transversion bias, which is why every substitution model has a parameter for it. The rate classes say 61% of sites are nearly invariant (rate 0.088), 31% evolve at about the average, and 8% evolve about seven times faster than average: a mostly-constrained genome with a small fast-evolving minority, which is exactly what +R3 is for and what a single gamma shape parameter would fit less well. And 47/213 is not a problem with the analysis \u2014 at well under one substitution per transmission, most internal branches rest on no evidence, so poor support is the honest resolution limit. The correct response is to collapse those branches, not to argue from their fine structure."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"GTR allows a separate rate for each of the six reversible base-change types.","correct":True},
   {"text":"An ultrafast bootstrap value of 80% indicates a well-supported branch.","correct":False},
   {"text":"+F takes base frequencies from the alignment rather than estimating them as free parameters.","correct":True},
   {"text":"High bootstrap support indicates the substitution model was correctly specified.","correct":False},
   {"text":"Recombination can produce a tree that is both strongly supported and wrong everywhere.","correct":True},
   {"text":"Likelihood under a time-reversible model returns a rooted tree.","correct":False}],
  "guidance":"1, 3 and 5. UFBoot is read at 95%. Support says how consistently your data under your model recover a split \u2014 nothing about whether the model, alignment or sampling is right. And time-reversibility is precisely why likelihood returns an unrooted tree; rooting is a separate decision."},
 {"type":"D","label":"Scaffolded","prompt":"Decode the model string component by component, then say what the alternative to the last component would have assumed.",
  "output":"GTR + F + R3\n  GTR  = ______________________\n  +F   = ______________________\n  +R3  = ______________________\n\n  The common alternative to +R3 is +G4, which assumes ______________________",
  "guidance":"GTR: all six reversible base-change types have free rates. +F: base frequencies taken empirically from the alignment. +R3: FreeRate site-rate heterogeneity with three freely estimated rate classes and their proportions. +G4 assumes rates follow a gamma distribution, discretised into four categories governed by a single shape parameter \u2014 a stronger assumption about the shape of the rate distribution, which +R does not make."},
]

EX["lesson-09"] = [
 {"type":"A","label":"Conceptual","prompt":"Write the tMRCA finding from a study as a single sentence for an incident manager. The estimate is 22 February (95% HPDI 16 January \u2013 24 March); the outbreak was declared on 15 May. Then say what three things your sentence deliberately does not claim.",
  "guidance":"\u2018The common ancestor of sequenced cases dates to late February 2026 (95% credible interval mid-January to late March), indicating that transmission was established at least six to eight weeks before the outbreak was recognised.\u2019 It does not claim: the date of the index case, the date of spillover, or that this is the age of the outbreak rather than a lower bound conditional on the sequences available."},
 {"type":"B","label":"Read the output","prompt":"A Tracer summary from a BEAST run. Answer the three questions.",
  "output":"Trace file: bdbv_skygrid_run1.log     states 100,000,000    burn-in 10%\n\nparameter                mean      95% HPD interval        ESS\n-------------------------------------------------------------------\nposterior             -18244.1   [-18271.8, -18216.9]      412\nclock.rate             8.5e-4    [7.3e-4, 9.8e-4]          388\ntreeModel.rootHeight    0.481    [0.394, 0.601]            341\nskygrid.precision       9.44     [2.17, 21.88]              96\ngtr.CT                  5.02     [4.41, 5.70]              501\nage(root)          2026-02-22   [2026-01-16, 2026-03-24]   341",
  "questions":[
   "One parameter here should stop you quoting the result it governs. Which, and what does it govern?",
   "What is missing from this output that you would need before believing any of the intervals?",
   "The root height HPD spans 0.394 to 0.601 years. Convert that to a plain sentence and note what the asymmetry around the mean tells you."],
  "guidance":"skygrid.precision has an ESS of 96, below the working threshold of 200 \u2014 and it is the smoothing parameter of the SkyGrid, so the shape of the Ne curve is under-sampled and should not be quoted as though it were resolved. Missing: evidence of convergence between independent chains. A single converged-looking chain can be stuck in a local optimum, and only this one run is shown. The root height means the common ancestor sits roughly 4.7 to 7.2 months before the most recent sample; the interval is longer on the older side, so the data are more compatible with an older origin than with a younger one \u2014 which is the direction that matters, since tMRCA is a lower bound anyway."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"A tMRCA moves earlier when a sequence from an early divergent chain is added.","correct":True},
   {"text":"Sampling from the prior with no data is a way to test whether the data inform the tMRCA.","correct":True},
   {"text":"An HPD interval is a confidence interval computed from the bootstrap distribution.","correct":False},
   {"text":"A strict clock is more powerful than a relaxed clock when a single rate is plausible.","correct":True},
   {"text":"Longer MCMC chains can create temporal signal that the sampling window does not contain.","correct":False},
   {"text":"The tMRCA is the date the pathogen crossed from its animal reservoir into humans.","correct":False}],
  "guidance":"1, 2 and 4. An HPD is a direct probability statement about the parameter given model and priors, not a frequentist confidence interval. Chain length improves sampling of the posterior, never the information content of the data. And spillover sits somewhere on the branch leading to the tMRCA node, which may be long."},
 {"type":"D","label":"Scaffolded","prompt":"The reporting sentence is half-built. Complete it, then delete anything it should not contain.",
  "output":"Estimate: 22 Feb 2026   HPDI: 16 Jan \u2013 24 Mar   Model: SkyGrid coalescent\nFirst recognised case: 24 Apr 2026   Outbreak declared: 15 May 2026\n\n  \u201cThe common ancestor of ____________ dates to ____________ (95% HPDI ____________),\n   under a ____________ tree prior, indicating that transmission was established\n   ____________ before the outbreak was recognised.\u201d",
  "guidance":"\u2018...of the 525 sequenced cases dates to 22 February 2026 (95% HPDI 16 January to 24 March), under a SkyGrid coalescent tree prior, indicating that transmission was established at least six to eight weeks before the outbreak was recognised.\u2019 Three things are load-bearing: \u2018sequenced cases\u2019 (not all cases), the model named alongside the number (the exponential-growth analysis gives a different tMRCA), and \u2018at least\u2019 (it is a lower bound)."},
]

EX["lesson-10"] = [
 {"type":"A","label":"Conceptual","prompt":"A skyline plot shows effective population size rising through May and June then flattening in July. Give three explanations, ranked by how likely you think they are, and say what single extra piece of data would separate them.",
  "guidance":"Most likely: sequencing effort fell in July, so fewer recent coalescences produce an apparent flattening. Next: the epidemic genuinely slowed, from control measures or susceptible depletion. Least likely without other evidence: a change in transmission structure. The separating data is sequences-per-week over the same period, overlaid on the curve \u2014 and the formal version is a nested-truncation analysis with identical curation at each cutoff."},
 {"type":"B","label":"Read the output","prompt":"A SkyGrid result table with the sequencing effort alongside it.",
  "output":"week ending   median Ne\u00b7\u03c4   95% HPD low   95% HPD high   genomes sequenced\n---------------------------------------------------------------------------\n2026-05-24        11.4          6.2           21.8              71\n2026-05-31        18.7         10.1           34.9              88\n2026-06-07        27.2         15.4           49.1              94\n2026-06-14        35.8         19.9           66.0             102\n2026-06-21        39.1         21.0           74.2              77\n2026-06-28        40.4         20.4           82.6              43\n2026-07-05        38.9         18.1           89.3              21\n2026-07-12        36.2         15.0          102.4               9",
  "questions":[
   "Describe what the Ne column alone appears to show, then what the last column does to that reading.",
   "The HPD intervals behave in a specific way over the last four weeks. Describe it and explain the cause.",
   "Can you convert the final Ne\u00b7\u03c4 of 36.2 into a number of infections? What would you need?"],
  "guidance":"The Ne column alone reads as growth to a plateau around late June, i.e. an epidemic being brought under control. The genome column shows sequencing collapsing from 102 to 9 per week over the same period, which is exactly what produces an apparent plateau \u2014 fewer recent coalescences. The HPD intervals widen sharply (74 wide, then 62, then 71, then 87) while the median barely moves: the data are running out, so the smoothing prior rather than the data is increasingly determining the curve. And no: Ne\u00b7\u03c4 is not prevalence. You would need the generation time to divide by, and even then overdispersed transmission and population structure separate effective from census size, usually by a large factor."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Coalescence rate is inversely proportional to effective population size.","correct":True},
   {"text":"Superspreading raises effective population size above the census number infected.","correct":False},
   {"text":"Birth-death models estimate Re directly and model sampling explicitly.","correct":True},
   {"text":"A finer SkyGrid resolution always gives a more informative curve.","correct":False},
   {"text":"Doubling time is ln(2) divided by the exponential growth rate.","correct":True},
   {"text":"Agreement between case-based Rt and phylodynamic Re means one of them is redundant.","correct":False}],
  "guidance":"1, 3 and 5. Overdispersed transmission pushes Ne well below the census size, not above. Too fine a grid leaves each interval with almost no coalescent events, so the smoothing prior rather than the data determines the curve. And agreement between two measurements with largely independent biases is corroboration, which is exactly why both are worth having."},
 {"type":"D","label":"Scaffolded","prompt":"Design the sensitivity analysis. Three of the four steps are given.",
  "output":"Concern: the apparent slowdown after mid-July may be reduced sampling, not real.\n\n  Step 1  Build datasets ending 23 Jun, 3 Jul, 16 Jul, 9 Aug  \u2713\n  Step 2  ______________________________________________\n  Step 3  Run a separate SkyGrid analysis on each  \u2713\n  Step 4  Compare clock rate and tMRCA across them  \u2713\n\n  What the result can show: ______________________\n  What it cannot show: ______________________",
  "guidance":"Step 2: apply identical curation and filtering to each dataset \u2014 without that, differences between the runs are differences in how you treated them. It can show that the conclusion is not an artefact of where you cut the data: in the published case, clock rates converged at ~8.5e-4 across the later datasets and the tMRCA was stable from July onward. It cannot rescue you from bias that ran in the same direction throughout, which is why the authors still flagged possible missing diversity in the two months around and preceding the inferred tMRCA."},
]

EX["lesson-11"] = [
 {"type":"A","label":"Conceptual","prompt":"Explain in two sentences, to someone with no phylogenetics, why a phylogeographic analysis can produce a map of laboratory funding rather than a map of the epidemic.",
  "guidance":"The method reconstructs where each ancestor probably was by looking at where its descendants were sampled \u2014 but it only knows how many sequences you gave it, not how many infections exist in each place. So a country that sequences a lot appears as the origin and a country that sequences little appears to receive, regardless of what actually happened."},
 {"type":"B","label":"Read the output","prompt":"Discrete trait analysis output for a four-country dataset.",
  "output":"Markov jump counts (posterior mean), from \u2192 to\n           A       B       C       D\n  A        \u2014    18.4     9.1     6.2\n  B      1.2       \u2014     0.8     0.4\n  C      0.9     1.1       \u2014     0.3\n  D      0.6     0.2     0.1       \u2014\n\nRoot state posterior:  A 0.91   B 0.05   C 0.03   D 0.01\n\n  country   sequences   reported cases\n  A            4,812         41,200\n  B               58         38,400\n  C               41         29,900\n  D               22        112,600",
  "questions":[
   "The root state posterior for country A is 0.91. How much of that is evidence about the epidemic?",
   "Compute sequences per 1,000 cases for each country. What does the spread do to every number in the jump matrix?",
   "What would you do differently, and what is the one thing no method can fix here?"],
  "guidance":"Almost none of it is evidence about the epidemic. A supplied 4,812 of 4,933 sequences \u2014 98% of the tree is in A, so A is inferred as ancestral more or less by construction. Sequences per 1,000 cases: A 116.8, B 1.5, C 1.4, D 0.2 \u2014 roughly a 600-fold range, and country D has the largest epidemic and the least sequencing. Every jump count out of A is inflated and every jump into A is suppressed. You would use a structured coalescent, which separates deme size from sampling intensity, or subsample toward case counts and repeat across replicates. What no method can fix is a region with zero sequences \u2014 it does not exist to the model, and transmission through it is attributed to whatever was sampled either side."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"An introduction count is jointly a property of the epidemic and of your surveillance.","correct":True},
   {"text":"Structured coalescent methods separate deme population size from sampling intensity.","correct":True},
   {"text":"Subsampling repairs a dataset in which one region contributed no sequences.","correct":False},
   {"text":"Replacing location with host species makes the same machinery answer reservoir questions.","correct":True},
   {"text":"Discrete trait analysis models the number of infections in each location.","correct":False},
   {"text":"Continuous phylogeography avoids the sampling bias that affects discrete trait analysis.","correct":False}],
  "guidance":"1, 2 and 4. Subsampling equalises among the locations you have and cannot conjure one you do not. DTA models location as a trait on the tree and knows only sequence counts. And continuous phylogeography inherits exactly the same sampling problem, in continuous form."},
 {"type":"D","label":"Scaffolded","prompt":"Rewrite the origin claim using the three-part template. The observation is given.",
  "output":"Observation: genomes from Mongbwalu showed substantial diversity and emerged from\n             relatively deep parts of the tree.\n\n  Inference (hedged in proportion to sampling): ______________________\n\n  Alternative that sampling alone could produce: ______________________\n\n  One sentence of sampling context to add: ______________________",
  "guidance":"Inference: this is consistent with Mongbwalu being an early or originating focus for the outbreak. Alternative: Mongbwalu was sampled earlier or more heavily than other zones, and deep-and-diverse is what dense early sampling also produces. Context: give sequences per case by health zone \u2014 if that varies twentyfold, say so in the same paragraph as the claim rather than in a limitations section nobody reaches."},
]

EX["lesson-12"] = [
 {"type":"A","label":"Conceptual","prompt":"An incident manager asks: \u201cdid case 14 infect case 17?\u201d The two genomes are identical. Give the answer you are entitled to give, and then give the answer they were hoping for and explain why you cannot give it.",
  "guidance":"Entitled: the isolates are identical, which is consistent with direct transmission and equally consistent with a short chain through unsampled cases or with two infections from a common source. Hoped for: yes. You cannot give it because at well under one substitution per transmission, identity carries almost no discriminating power \u2014 and sequence data does not give direction even when a link is real."},
 {"type":"B","label":"Read the output","prompt":"A pairwise SNP matrix from a suspected ward outbreak, with the epidemiological summary beneath it.",
  "output":"          P01   P02   P03   P04   P05\n  P01       \u2014     0     1    31     2\n  P02       0     \u2014     1    29     2\n  P03       1     1     \u2014    30     1\n  P04      31    29    30     \u2014    28\n  P05       2     2     1    28     \u2014\n\n  Background: pairwise distance among contemporaneous unlinked isolates\n              in this hospital, median 24 SNPs (IQR 17\u201333)\n\n  Ward overlap:  P01\u2013P02 yes   P01\u2013P03 yes   P04 yes (same ward, same week)\n                 P05 NO \u2014 never admitted to this ward",
  "questions":[
   "Which patient can you exclude from the cluster, and how confident is that statement compared with the others you could make?",
   "P05 has no ward contact but sits within 2 SNPs of the cluster. Which cell of the evidence table is this, and what should happen next?",
   "Write the cluster definition sentence you would put in the report."],
  "guidance":"P04 is excluded: 28\u201331 SNPs, squarely inside the unlinked background distribution, is inconsistent with recent transmission. That is the strongest statement available here \u2014 exclusion is robust to incomplete sampling, because unsampled intermediates would make distances larger, not smaller. P05 is the productive cell: genomically compatible with no known epidemiological link, which points at a missing part of the network \u2014 shared staff, shared equipment, an environmental reservoir, or an unrecognised contact. That is what to investigate, not a reason to dismiss the genomics. Report sentence: \u2018P01, P02, P03 and P05 fall within 2 SNPs of one another against a local background of 24 SNPs (IQR 17\u201333) among contemporaneous unlinked isolates, sampled within a 3-week window; P04 differs by 28\u201331 SNPs and a direct link to this cluster is excluded.\u2019"},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Exclusion is robust to incomplete sampling because unsampled intermediates would increase, not decrease, genetic distance.","correct":True},
   {"text":"Transmission-tree software returns a posterior distribution over transmission trees.","correct":True},
   {"text":"Near-identical isolates from two episodes in one patient indicate reinfection.","correct":False},
   {"text":"Distinguishing importation from residual transmission requires a historical sequence archive from that focus.","correct":True},
   {"text":"The word 'confirmed' is appropriate for a genomic linkage finding supported by identical genomes.","correct":False},
   {"text":"A survivor-associated flare-up typically attaches to a recent part of the tree on a short branch.","correct":False}],
  "guidance":"1, 2 and 4. Near-identity between two episodes in one patient indicates relapse \u2014 the original population persisted \u2014 which is how the question was settled in gambiense HAT and is used routinely in TB and malaria. \u2018Confirmed\u2019 belongs to exclusions only. And a survivor-associated flare-up shows the opposite signature: a long branch attaching to an old part of the tree, sometimes with an unusually low apparent rate."},
 {"type":"D","label":"Scaffolded","prompt":"Convert each finding into the sentence you are entitled to write. The strength is given; supply the sentence.",
  "output":"  Finding                                      Strength        Sentence\n  ------------------------------------------------------------------------\n  27 SNPs apart, rate ~16/genome/yr            exclusion       ____________\n  identical, documented shared exposure        consistency     ____________\n  identical, no known contact                  consistency     ____________\n  71% coverage, differences in dropout region  indeterminacy   ____________",
  "guidance":"Exclusion: \u2018...this is inconsistent with direct transmission during the outbreak period; a direct link is excluded.\u2019 Consistency with epi: \u2018...in isolation this is consistent with direct transmission and with transmission through unsampled intermediates; together with the documented shared exposure the combined evidence supports a link, though direction cannot be determined from sequence data.\u2019 Consistency without epi: \u2018...consistent with a chain passing through unsampled cases; warrants targeted investigation; does not establish direct links between the sampled cases.\u2019 Indeterminacy: \u2018...this sample cannot be placed relative to the cluster at the required resolution.\u2019"},
]

EX["lesson-02"] = [
 {"type":"A","label":"Conceptual","prompt":"Your programme archives consensus FASTA files only, to save storage. Name three questions that decision makes permanently unanswerable, and one it does not affect.",
  "guidance":"Foreclosed: mixed infection, minority resistant subpopulations, and the transmission bottleneck \u2014 all need reads. Unaffected: lineage reassignment when a nomenclature scheme is revised, which works fine from FASTA. The point is that this is a policy decision usually made by default and regretted later."},
 {"type":"B","label":"Read the output","prompt":"A screening script reports the base-change spectrum for four genomes against the outbreak consensus.",
  "output":"genome      A>G   T>C   C>T   G>A   G>T   other   runs_of_>=3   %N\n---------------------------------------------------------------------\n26FHV011      1     2     3     1     0      4          0          1.2\n26FHV054      0    17     1     0     0      2          5          0.9\n26FHV118      2     1     2     2    11      3          0          2.1\n26FHV203      1     3     2     1     0      3          0         31.4",
  "questions":[
   "Which genome shows a host editing signature, which one, and what in the table is the decisive clue rather than the base change alone?",
   "26FHV118 shows 11 G>T changes. What is the most likely source, and is it the patient, the pathogen or the laboratory?",
   "26FHV203 has no unusual spectrum. Should it enter the phylodynamic analysis?"],
  "guidance":"26FHV054 is ADAR: T>C is the signature on the strand filovirus genomes are written on, but the decisive clue is `runs_of_>=3` \u2014 ADAR is processive and edits short consecutive spans, which is what distinguishes it from ordinary substitution. 26FHV118 is oxidative damage from library preparation \u2014 the laboratory\u2019s own signature, not the patient\u2019s and not the virus\u2019s. 26FHV203 is spectrally normal but 31% N: it will fail a completeness threshold, and that exclusion is a load-load-dependent one that removes late presenters and remote health zones preferentially."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"APOBEC3 and ADAR both impose mutations that are host-derived rather than replication error.","correct":True},
   {"text":"A consensus base can change between two serial samples from one patient without the within-host population changing.","correct":True},
   {"text":"Iterative outlier removal is used because it converges faster than single-pass removal.","correct":False},
   {"text":"Homopolymer indels are more suspicious on nanopore data than on Illumina data.","correct":True},
   {"text":"Trimming an alignment removes artefactual signal at no cost to real signal.","correct":False},
   {"text":"Excluding sequences is defensible as long as the final root-to-tip regression fits well.","correct":False}],
  "guidance":"1, 2 and 4. Iteration is used because editing on an internal branch affects multiple tips, so outliers are not independent \u2014 not for speed. Trimming removes positions from every sequence, including those with no artefact there. And removing sequences until the fit improves is fitting the filter to the desired result; the criterion has to be stated before the outcome."},
 {"type":"D","label":"Scaffolded","prompt":"The exclusion cascade below is missing its reasons. Fill each in, then say which of the two filters should run first and why.",
  "output":"626 genomes generated\n   \u2212 32   reason: ______________________   filter type: ______________\n594\n   \u2212 69   reason: ______________________   filter type: ______________\n525 analysed",
  "guidance":"32 removed for ADAR editing signatures \u2014 a mechanistic filter, justified by a known biological process with a known signature. 69 removed as root-to-tip outliers beyond \u00b12 SD, applied iteratively \u2014 a statistical filter. The mechanistic one runs first, because it removes sequences for a stated reason and leaves the blunt statistical filter with less to do; run the other way round, the statistical filter absorbs the edited genomes and you never learn why they were odd."},
]

EX["lesson-03"] = [
 {"type":"A","label":"Conceptual","prompt":"An outbreak presents as \u201cunknown severe illness, high mortality\u201d with no candidate pathogen. Rank the four enrichment strategies for this situation and justify the ranking in one sentence each.",
  "guidance":"Metagenomics first \u2014 it is the only one that can find something nobody hypothesised. Capture second, if a broad viral-family panel plausibly covers it. Culture third, and only for what grows. Amplicon last and effectively unusable, because it needs primers, which need a known target. Once the agent is identified the ranking inverts completely, which is the point."},
 {"type":"B","label":"Read the output","prompt":"A sequencing run manifest from a field laboratory. Answer the three questions.",
  "output":"sample     Ct     specimen      pool   reads(k)   genome_cov_20x   consensus_%N\n-------------------------------------------------------------------------------\nS-041      19.2   EDTA blood     A       412         99.1%             0.4\nS-042      24.8   EDTA blood     A       338         97.6%             1.8\nS-043      30.6   oral fluid     B        61         71.2%            27.5\nS-044      33.1   oral fluid     B        18         38.9%            60.3\nNEG-A       \u2014     water          A         3          0.2%              \u2014\nNEG-B       \u2014     water          B        44          6.1%              \u2014\nPOS-CTL    21.0   synthetic      A       290         98.8%             0.9",
  "questions":[
   "Which sample would a Ct < 31 selection rule have excluded, and which would a 90% coverage rule exclude? Are they the same sample?",
   "Something on this run needs investigating before any of these consensus sequences are used. What, and what does it threaten?",
   "S-043 and S-044 are oral fluid from deceased patients. What does losing them do to the epidemiology, beyond losing two data points?"],
  "guidance":"Ct < 31 excludes S-044 only. The 90% coverage rule excludes both S-043 and S-044 \u2014 so the two filters are not the same, and they compound. The urgent problem is NEG-B: 44,000 reads and 6% genome coverage in a no-template control means contamination or index hopping in pool B, which threatens exactly the Q1 linkage claims that would make two samples look identical. Losing the oral-fluid samples removes people who died in the community \u2014 the group most likely to sit in undetected chains \u2014 so the loss is structured, not random."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Ct values are comparable across laboratories provided the same target gene is used.","correct":False},
   {"text":"A mutation under a primer binding site causes loss of coverage precisely where the pathogen changed.","correct":True},
   {"text":"Bait capture tolerates a divergent target better than tiling amplicon PCR does.","correct":True},
   {"text":"Multiplexing reduces the marginal cost per genome and simultaneously creates the main cross-contamination risk.","correct":True},
   {"text":"A positive control identical to the outbreak strain is preferable because it validates the whole workflow.","correct":False},
   {"text":"Metagenomics is more sensitive than amplicon PCR for a known target at high Ct.","correct":False}],
  "guidance":"2, 3 and 4. Ct depends on assay, extraction volume, instrument and threshold setting, so it is an internally consistent ordering within one workflow and nothing more. An identical positive control makes contamination of a sample by the control invisible. And metagenomics is markedly less sensitive than targeted amplification at low template."},
 {"type":"D","label":"Scaffolded","prompt":"Complete the tiling scheme diagram, then answer what breaks.",
  "output":"genome  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\npool 1  \u2594\u2594\u2594\u2594\u2594\u2594\u2594      \u2594\u2594\u2594\u2594\u2594\u2594\u2594      \u2594\u2594\u2594\u2594\u2594\u2594\u2594      \u2594\u2594\u2594\u2594\u2594\u2594\u2594\npool 2       ?????        ?????        ?????\n\nQ1  Why are neighbouring amplicons never in the same pool?\nQ2  Why must the amplicons overlap rather than abut?\nQ3  A mutation appears under a pool-1 primer. Which two things go wrong?",
  "guidance":"Q1: overlapping products in one reaction amplify each other and produce short junk. Q2: abutting amplicons leave gaps at every junction once the ends are trimmed. Q3: amplicon dropout, giving a run of Ns exactly where the virus changed; and, if primer sequence is not trimmed from the reads, the primer\u2019s reference base is called as consensus \u2014 a manufactured reversion to reference at the variable site."},
]

EX["lesson-04"] = [
 {"type":"A","label":"Conceptual","prompt":"A national laboratory receives 15 samples a week in unpredictable bursts, has intermittent mains power, no service engineer within 2,000 km, and needs results in 72 hours. Argue for a platform, then answer: what happens the day the machine breaks?",
  "guidance":"Nanopore, amplicon, on site. The instrument is cheap enough to hold a spare, runs off a laptop, tolerates the power situation, produces output in real time and works in small frequent batches. A high-throughput short-read instrument is efficient only when saturated, and at 15 samples a week saturating it means batching, which destroys the 72-hour requirement that justified buying it. The breakage question is the one that decides it: a $1,000 device you can replace beats a $300,000 device that becomes a cupboard."},
 {"type":"B","label":"Read the output","prompt":"A nanopore run report. Answer the three questions.",
  "output":"Flow cell   FLO-MIN114 (R10.4.1)      Kit  SQK-NBD114.24\nBasecaller  dorado 0.9.6, model dna_r10.4.1_e8.2_400bps_sup@v5.0.0\nRun time    18h 40m           Pores available at start / end   1,412 / 388\n\nRead stats            simplex        duplex\n  reads              4.42 M          0.31 M\n  median Q            23.1           30.4\n  median length      1,183 b        1,190 b\n  N50                1,204 b        1,201 b",
  "questions":[
   "Median Q23 means roughly what error rate, and why is a consensus genome from these reads still trustworthy?",
   "Two of the fields in this report belong in the sequence metadata. Which two, and why does one of them matter more than people expect?",
   "The read length distribution is tightly clustered at ~1,200 b. What does that tell you about the library, and what would a broad distribution have suggested?"],
  "guidance":"Q23 is about 1 error in 200, i.e. 0.5%. Errors are largely independent between reads, so at adequate depth the chance that a majority agree on the same wrong base is negligible \u2014 depth converts mediocre reads into an excellent consensus, and minimum-depth thresholds rather than read quality are the load-bearing control. The two metadata fields are the basecaller version and model, and the chemistry/kit: re-basecalling the same raw signal with a newer model produces different sequence, so genomes compared across versions differ partly because of software rather than biology. The tight ~1,200 b distribution says this is an amplicon library with a ~1,200 b scheme; a broad distribution would indicate metagenomic or native DNA input."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"Depth compensates for random per-read error but not for systematic error.","correct":True},
   {"text":"Adaptive sampling gives host depletion without additional wet-lab work.","correct":True},
   {"text":"Illumina's dominant error mode is the indel; nanopore's is the substitution.","correct":False},
   {"text":"Basecalling a nanopore run with a super-accurate model typically needs a GPU.","correct":True},
   {"text":"A variant seen on only one of two platforms is most likely a real minority variant.","correct":False},
   {"text":"PacBio HiFi is the appropriate default for routine national viral surveillance.","correct":False}],
  "guidance":"1, 2 and 4. The error modes are the other way round \u2014 Illumina makes substitutions, nanopore historically made indels in homopolymers. A platform-specific variant should first be suspected of being that platform\u2019s systematic error. And PacBio\u2019s cost keeps it out of routine surveillance, whatever its accuracy."},
 {"type":"D","label":"Scaffolded","prompt":"Three of the four numbers that decide a platform are filled in. Supply the fourth, then choose.",
  "output":"Scenario: national Salmonella and Listeria surveillance, cluster detection at 0\u20135 SNP resolution\n\n  1. Samples arriving per week ......... ~60, steady\n  2. Acceptable sample-to-answer ....... 2\u20133 weeks\n  3. Genome size / repeats ............. 4\u20135 Mb, repeats matter for plasmids\n  4. Power, cold chain, compute, service  ______________________\n\n  Platform: __________   Reason: __________",
  "guidance":"A national reference laboratory can be assumed to have stable power, a working cold chain, compute and a service contract \u2014 which is exactly why the answer differs from the field scenario. Illumina: you need per-base accuracy at 0\u20135 SNP resolution and at volume, and weekly batching is acceptable against a 2\u20133 week requirement. Add long reads selectively to close plasmids, which short reads cannot span."},
]

EX["lesson-05"] = [
 {"type":"A","label":"Conceptual","prompt":"Explain to a non-bioinformatician why a coverage hole in a viral genome is worse than a random gap of the same size.",
  "guidance":"Because it is not random. In amplicon data a hole usually means a mutation under a primer stopped that amplicon amplifying \u2014 so you lose data preferentially at the positions where the virus changed, which are the positions you most wanted. The missingness is informative and it points the wrong way."},
 {"type":"B","label":"Read the output","prompt":"Per-amplicon depth for one sample, and the consensus summary.",
  "output":"amplicon  start    end   mean_depth   pct_>=20x\n-------------------------------------------------\n     1        30    1210      2,410      100.0\n     2      1150    2330      1,880      100.0\n     3      2270    3450          6        4.2\n     4      3390    4570      3,102      100.0\n     5      4510    5690      1,455      100.0\n\nconsensus: 4,918 / 5,690 called (86.4%)   N-runs: 1 (2270-3450)\nprimer trimming: NOT APPLIED",
  "questions":[
   "Amplicon 3 has failed. Give the most likely biological cause and say what it implies about that region.",
   "\u2018primer trimming: NOT APPLIED\u2019 \u2014 what specific error will appear in this consensus, and where?",
   "This sample is 86.4% complete. A 90% threshold would drop it. Is dropping it the right call?"],
  "guidance":"Amplicon 3 has almost certainly lost a primer binding site to a mutation \u2014 so the region that failed is likely the region that changed. Without primer trimming, the primer\u2019s reference bases are called as consensus at the start and end of every surviving amplicon, producing false reversions to reference at exactly the variable primer-site positions. On the threshold: the honest answer is that it depends on the question. For lineage assignment 86% may be fine; for a linkage claim that turns on a position inside the dropout it is useless. A single global threshold applied without reference to the question is the thing to avoid \u2014 and either way the loss is not random."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"BAM files retain within-host diversity that consensus FASTA has discarded.","correct":True},
   {"text":"Breadth of coverage is the number of reads at a given position.","correct":False},
   {"text":"Colouring a phylogeny by sequencing run is a fast test for contamination artefacts.","correct":True},
   {"text":"Reference mapping can reveal large insertions that are absent from the reference.","correct":False},
   {"text":"De novo assembly is generally necessary for bacteria because the accessory genome varies between isolates.","correct":True},
   {"text":"A pipeline version is a bureaucratic detail with no effect on the sequences produced.","correct":False}],
  "guidance":"1, 3 and 5. Breadth is the fraction of the genome above a depth threshold; depth is the read count at a position. Mapping can only show you what maps, so large insertions absent from the reference are invisible or misassembled. And pipeline and basecaller versions demonstrably change the genomes you get."},
 {"type":"D","label":"Scaffolded","prompt":"The cascade is drawn with the arrows unlabelled. Label each with its cause, then state the direction of the bias.",
  "output":"   5,200  cases presenting\n      \u2193   ______________________\n   4,100  cases tested\n      \u2193   ______________________\n   3,748  PCR-positive\n      \u2193   ______________________\n     712  selected for sequencing\n      \u2193   ______________________\n     626  genomes produced\n      \u2193   ______________________\n     525  genomes analysed\n\n  Direction of the compound bias: ______________________",
  "guidance":"Testing policy and test availability; test sensitivity and timing relative to onset; sample retained, transported and Ct below threshold; library, run and coverage threshold; editing-signature and outlier filtering. Every arrow removes low-load, late-presenting, remote and milder cases preferentially, so the compound bias runs in one direction throughout: the analysed set over-represents people who presented early, severely, and close to a functioning laboratory."},
]

EX["lesson-06"] = [
 {"type":"A","label":"Conceptual","prompt":"A press office asks you to approve the sentence \u201ca dangerous new variant has been detected.\u201d Rewrite it truthfully for a lineage that has been designated but not phenotypically characterised, and explain what you removed.",
  "guidance":"Something like: \u2018a previously undesignated lineage has been detected; it is defined by its position on the phylogeny, and there is currently no evidence about its transmissibility, severity or effect on diagnostics.\u2019 You removed \u2018dangerous\u2019, which is a phenotypic claim nobody has evidence for, and you replaced \u2018variant\u2019 with \u2018lineage\u2019, which says what was actually observed."},
 {"type":"B","label":"Read the output","prompt":"Nextclade output for four sequences. Answer the three questions.",
  "output":"seqName    clade    lineage    totalMutations  privateMutations  QC.overall  QC.flags\n----------------------------------------------------------------------------------------\nGS-0117    23F      XBB.1.5         41                3            good      \u2014\nGS-0118    23F      XBB.1.5         39                2            good      \u2014\nGS-0119    23F      XBB.1.5        118               71            bad       privateMutations; clusteredSNPs\nGS-0120    ?        ?               12                9            bad       missingData (68.2% N)",
  "questions":[
   "GS-0119 has 71 private mutations and clustered SNPs. Give two explanations, one biological and one technical, and say which you would investigate first.",
   "GS-0120 could not be assigned. Is that a property of the virus or of the sample?",
   "GS-0117 and GS-0118 differ by two mutations. What, if anything, does that say about a transmission link between those two cases?"],
  "guidance":"Biological: a long unsampled chain, or a chronic infection in an immunocompromised host where within-host evolution accelerated. Technical: contamination, co-infection, or index hopping producing a mixture. Investigate the technical explanation first \u2014 it is far more common and it is cheap to check (negative controls, run assignment, allele frequencies at the private sites). GS-0120 is a sample problem: 68% N means insufficient template or a failed run, not an unusual virus. And two mutations between GS-0117 and GS-0118 says very little on its own; you need the local background distance distribution before that number carries any information."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"A WHO variant label is a risk assessment rather than a phylogenetic designation.","correct":True},
   {"text":"cgMLST counts a single SNP and a whole recombined block each as one allele difference.","correct":True},
   {"text":"SNP distances are comparable between studies as long as both used whole genome sequencing.","correct":False},
   {"text":"Single-linkage clustering produces smaller, more conservative clusters than complete linkage.","correct":False},
   {"text":"Influenza requires a genotype rather than a subtype name because its segments reassort.","correct":True},
   {"text":"A serotype is a phylogenetic category.","correct":False}],
  "guidance":"1, 2 and 5. SNP distances depend on the reference and the masking scheme, so they are not comparable across studies that chose differently. Single linkage chains clusters together and grows them without limit; complete linkage is the conservative one. And a serotype is a phenotype \u2014 an antigenic type originally read with antibodies, inferable from sequence but not defined by the tree."},
 {"type":"D","label":"Scaffolded","prompt":"A cluster definition is given with two of its five components. Supply the missing three, then say what you would need in order to defend the threshold.",
  "output":"\u201cCluster A comprises 14 isolates within 5 SNPs of one another.\u201d\n\n  metric ......... SNP distance from a mapped alignment  \u2713\n  threshold ...... 5 SNPs  \u2713\n  linkage rule ... ______________________\n  time window .... ______________________\n  background ..... ______________________\n\n  To defend the threshold I would need: ______________________",
  "guidance":"Linkage rule: single or complete \u2014 unstated in almost every published definition and it materially changes cluster size. Time window: without one, a 2018 and a 2026 isolate 4 SNPs apart will cluster, which is informative about a persistent lineage and not about current transmission. Background: the pairwise distance distribution among contemporaneous unlinked local isolates, without which the threshold carries no information. To defend it you need validation against epidemiologically confirmed links, with sensitivity and specificity reported \u2014 which is what almost nobody has."},
]

EX["lesson-00"] = [
 {"type":"A","label":"Conceptual","prompt":"Three claims, each from a real headline shape. Sort each into one of the four questions, name the classical comparator it must beat, and say what evidence it owes you.",
  "questions":[
   "\u201cSequencing revealed the outbreak began two months earlier than anyone realised.\u201d",
   "\u201cGenomic analysis confirmed the new variant spreads 40% faster.\u201d",
   "\u201cWhole genome sequencing linked the hospital cluster to a single index patient.\u201d"],
  "guidance":"1 is Q3 (dynamics) and owes you the sampling frame plus the interval, not a point estimate. 2 is written as Q4 but is almost always supported only by Q3 evidence \u2014 growth in sequence share \u2014 which is confounded by who got sequenced; it owes a phenotypic or carefully controlled epidemiological link. 3 is Q1 and owes the local background diversity; note also that \u2018linked\u2019 and \u2018identified the index patient\u2019 are different and much stronger claims."},
 {"type":"B","label":"Read the output","prompt":"A national genomic surveillance dashboard reports the figures below for one month. Answer the three questions.",
  "output":"Province      Cases   Sequenced   Lineage A   Lineage B   Lineage C\n------------------------------------------------------------------\nCentral        412        188         61%         27%         12%\nNorthern       377         14         21%         79%          0%\nEastern        851         31         45%         48%          7%\nWestern        119         96         58%         30%         12%\n------------------------------------------------------------------\nNational       1759       329         55%         34%         11%",
  "questions":[
   "What does the national row \u201cLineage A 55%\u201d actually describe, stated precisely?",
   "A colleague concludes that Lineage B is expanding because it dominates in Northern province. What is wrong with that inference, and what would you need to test it?",
   "Compute sequences-per-case for each province. What is the ratio between the highest and the lowest, and what does that do to any national proportion estimate?"],
  "guidance":"The national row describes the 329 sequenced samples, not the 1,759 cases \u2014 and the sequenced set is dominated by Central and Western, which together supplied 86% of sequences but 30% of cases. Northern\u2019s 79% rests on 14 sequences (roughly \u00b111 percentage points at best, and that assumes random sampling within the province). Sequences per case: Central 0.46, Northern 0.04, Eastern 0.04, Western 0.81 \u2014 a twentyfold range. The \u2018national\u2019 proportions are a weighted average of provinces sampled at wildly different intensities, so they are closer to a description of Central and Western than of the country."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"A consensus genome cannot tell you whether a minority drug-resistant subpopulation is present in the patient.","correct":True},
   {"text":"Clade size on a phylogeny is a direct measure of how much transmission that clade caused.","correct":False},
   {"text":"Genomic data excludes transmission links more reliably than it confirms them.","correct":True},
   {"text":"An ancestral-state reconstruction is a statement about the epidemic, independent of where sequencing happened.","correct":False},
   {"text":"A mutation identified in a surveillance dataset is a hypothesis about a phenotype, not a phenotype.","correct":True},
   {"text":"Because the chain from molecule to decision is lossy, sequencing more deeply at the final step recovers what earlier steps discarded.","correct":False}],
  "guidance":"1, 3 and 5. Clade size tracks sampling at least as much as transmission; ancestral-state reconstruction places origins where sequencing is dense; and information lost at an earlier step of the chain is not recoverable at a later one \u2014 depth at the tree stage cannot restore within-host diversity that consensus calling already discarded."},
 {"type":"D","label":"Scaffolded","prompt":"Below is a finished sentence from a report. Rewrite it so it states the observation and the inference separately, and hedges the inference in proportion to the sampling. The structure is given; supply the content.",
  "output":"BEFORE\n  \u201cThe outbreak originated in Mongbwalu health zone.\u201d\n\nAFTER (fill in)\n  Observation:  ____________________________________________\n  Inference:    ____________________________________________\n  Alternative:  ____________________________________________",
  "guidance":"Observation: genomes from Mongbwalu showed substantial diversity and emerged from relatively deep parts of the tree. Inference: this is consistent with Mongbwalu being an early or originating focus. Alternative: Mongbwalu was sampled early and heavily, and deep-and-diverse is exactly what dense early sampling also produces. The published version of this sentence uses \u2018suggesting\u2019 and \u2018possible\u2019, and those hedges are load-bearing rather than decorative."},
]

EX["lesson-01"] = [
 {"type":"A","label":"Conceptual","prompt":"A colleague proposes sequencing to reconstruct who-infected-whom in a hepatitis B outbreak in a dialysis unit. Before looking at any data, what do you need to know, and what would make you say no?",
  "guidance":"You need the evolutionary rate, the genome length (~3.2 kb, which is small enough that rate \u00d7 length is low) and the interval between infections. HBV is a slowly evolving DNA virus with a chronic course. Multiply and you will get well under one substitution per transmission, which rules out ordering individual links. Genomics can still exclude links and identify a common source, which in a dialysis unit is usually the question that matters."},
 {"type":"B","label":"Read the output","prompt":"A root-to-tip regression, as TempEst reports it. Answer the three questions.",
  "output":"Dataset A                          Dataset B\n  slope      8.1e-4 subs/site/yr     slope      -2.0e-5 subs/site/yr\n  x-intercept 2026-02-19             x-intercept 1974-06-03\n  correlation 0.86                   correlation 0.04\n  R-squared   0.74                   R-squared   0.002\n  residual mean sq 1.1e-8            residual mean sq 9.4e-7\n  tips 525                           tips 61",
  "questions":[
   "For dataset A, what do the slope and the x-intercept each estimate?",
   "Dataset B was run through the same pipeline and produced a tMRCA with a tight credible interval. Should you believe it?",
   "What is the one thing the correlation coefficient here does NOT justify, given how the points were generated?"],
  "guidance":"A: the slope estimates the evolutionary rate in substitutions per site per year; the x-intercept estimates the date of the root. B: no \u2014 a near-zero slope, a correlation of 0.04 and an x-intercept fifty years before sampling are the signature of no temporal signal. The software still returned a tMRCA, and that tMRCA is the prior restated with a credible interval that looks like evidence. Third: the tips share ancestry, so they are not independent observations; the correlation is a diagnostic that dating is possible, not a significance test, and ordinary least squares understates the uncertainty."},
 {"type":"C","label":"Three of six","prompt":"Exactly three of these statements are correct.",
  "statements":[
   {"text":"The substitution rate is lower than the mutation rate because selection and bottlenecks remove most mutations before they are observed.","correct":True},
   {"text":"A pathogen with 0.05 substitutions per transmission can resolve individual transmission links given sufficient sequencing depth.","correct":False},
   {"text":"Coronaviruses evolve more slowly per site than influenza partly because they carry a proofreading exonuclease.","correct":True},
   {"text":"Influenza reassortment means a single phylogeny cannot describe the whole virus.","correct":True},
   {"text":"If a root-to-tip regression shows no temporal signal, using a relaxed clock will recover the ability to date the tree.","correct":False},
   {"text":"Evolutionary rates quoted per site per year are directly comparable between pathogens without reference to genome length.","correct":False}],
  "guidance":"1, 3 and 4. Depth cannot create mutations that never happened; a relaxed clock accommodates rate variation but does not manufacture signal; and a per-site rate must be multiplied by genome length before two pathogens can be compared \u2014 the same rate on a 30 kb and a 3 kb genome gives tenfold different resolution."},
 {"type":"D","label":"Scaffolded","prompt":"The arithmetic is set out below with one step missing for each pathogen. Complete it, then write the resolution verdict.",
  "output":"                  rate (/site/yr)  length (b)   subs/genome/yr   serial int.   subs/transmission\nBundibugyo virus     8.5e-4          18,900         16.1             15 d           0.66\nSARS-CoV-2           8.0e-4          29,900         ____             5 d            ____\nMeasles              6.0e-4          15,900         ____            14 d            ____\nM. tuberculosis        \u2014               \u2014           0.4            550 d            ____",
  "guidance":"SARS-CoV-2: 23.9 per year, 0.33 per transmission. Measles: 9.5 per year, 0.37. TB: 0.4 \u00d7 550/365 = 0.60. All three sit in the productive 0.3\u20130.7 band, which is why clusters resolve and individual links do not \u2014 and note that TB gets there by a completely different route, a very slow clock against a very long serial interval."},
]


# ---------------------------------------------------------------- assemble
here = pathlib.Path(__file__).parent
phase_title = {p: t for p, t, _ in PHASES}

modules = [{"module": m, "section": s, "title": t, "bloom_level": b, "hours": h}
           for m, s, t, b, h in MODULES]

# Option order carries no meaning, so it is shuffled with a fixed seed. This is
# the one rebalancing that is free of side effects: unlike padding an option,
# reordering cannot create a length or phrasing tell. Seeded, so the manifest is
# reproducible and a learner cannot see the shuffle change between builds.
rng = random.Random(20260828)

lessons = []
for (lid, order, section, phase, day, emoji, mins, optional, fname,
     title, subtitle, desc, topics, key_terms, practical) in META:
    quiz = []
    for q, o, c, e in Q[lid]:
        idxs = list(range(len(o)))
        rng.shuffle(idxs)
        quiz.append({
            "question": q,
            "options": [o[i] for i in idxs],
            "correct": idxs.index(c),
            "explanation": e,
        })
    lessons.append({
        "id": lid, "order": order, "section": section,
        "phase": phase, "phase_title": phase_title[phase],
        "day": day, "emoji": emoji, "time": mins, "optional": optional,
        "title": title, "subtitle": subtitle, "description": desc,
        "file": f"lessons/{fname}",
        "topics": topics, "key_terms": key_terms,
        "practical": practical, "quiz": quiz,
        "exercises": [
            dict(e, correct_indices=[i + 1 for i, st in enumerate(e["statements"]) if st["correct"]])
            if e.get("statements") else e
            for e in EX.get(lid, [])
        ] + [{
            "type": "E", "label": "Connect to your work",
            "prompt": practical,
            "guidance": "No single right answer. The value is in doing it on data you actually "
                        "have, where you know what the numbers mean and can tell when an answer "
                        "is implausible.",
        }],
    })


# ---- exercise validation, at build time ------------------------------------
# Three defects shipped into the first exercise build and none was visible by
# reading the source: lesson-20's C rung had four correct statements of six,
# lesson-22's statement 4 was true as written while marked false, and 74 fields
# carried literal backslash-u escapes because a paste used raw strings. A
# three-of-six exercise with four correct answers is not a hard exercise, it is
# a broken one, and with negative marking it is actively unfair. The build now
# refuses to write a manifest containing any of the three.
problems = []
for _l in lessons:
    for _e in _l["exercises"]:
        _t = _e["type"]
        if not _e.get("prompt"):
            problems.append(f"{_l['id']} [{_t}] no prompt")
        if _t == "B" and not (_e.get("output") and _e.get("questions")):
            problems.append(f"{_l['id']} [B] missing output or questions")
        if _t == "C":
            _st = _e.get("statements") or []
            _n = sum(1 for x in _st if x["correct"])
            if len(_st) != 6 or _n != 3:
                problems.append(f"{_l['id']} [C] {len(_st)} statements, {_n} correct (need 6 and 3)")
        if _t in "ABCD" and not _e.get("guidance"):
            problems.append(f"{_l['id']} [{_t}] no guidance")
        _text = " ".join([_e.get("prompt") or "", _e.get("guidance") or "", _e.get("output") or ""]
                         + list(_e.get("questions") or [])
                         + [x["text"] for x in (_e.get("statements") or [])])
        if "\\u" in _text or "\\n" in _text:
            problems.append(f"{_l['id']} [{_t}] literal backslash escape survived into the text")
        for _tell in ("is true as written", "intended trap", "arguably correct"):
            if _tell in (_e.get("guidance") or ""):
                problems.append(f"{_l['id']} [{_t}] guidance concedes the exercise is broken")
if problems:
    print("EXERCISE VALIDATION FAILED - manifest not written:")
    for _p in problems:
        print("  " + _p)
    raise SystemExit(1)

(here / "lessons.json").write_text(
    json.dumps({"modules": modules, "lessons": lessons}, indent=2, ensure_ascii=False) + "\n")


# ---- keep course.json's phases block in step with the manifest ---------------
# It was hand-written and drifted the moment lesson-25 was added, still listing
# 21 of 22 lessons. Nothing in the app reads it, so the drift was invisible —
# which is exactly why it is worth deriving rather than maintaining.
_cj = here / "course.json"
if _cj.exists():
    _c = json.loads(_cj.read_text())
    _titles, _order = {}, []
    for _l in lessons:
        if _l["phase"] not in _titles:
            _titles[_l["phase"]] = _l["phase_title"]; _order.append(_l["phase"])
    _derived = [{"phase": _p, "title": _titles[_p],
                 "lessons": [x["id"] for x in lessons if x["phase"] == _p]}
                for _p in sorted(_order)]
    if _c.get("phases") != _derived:
        _c["phases"] = _derived
        _cj.write_text(json.dumps(_c, indent=2, ensure_ascii=False) + "\n")
        print("course.json phases block refreshed from the manifest")

# -------- audit-friendly report
pos = [0, 0, 0, 0]
longest = 0
total = 0
for l in lessons:
    for q in l["quiz"]:
        pos[q["correct"]] += 1
        total += 1
        lens = [len(o) for o in q["options"]]
        if lens[q["correct"]] == max(lens) and lens.count(max(lens)) == 1:
            longest += 1
ex_total = sum(len(l["exercises"]) for l in lessons)
ex_types = {}
for l in lessons:
    for e in l["exercises"]:
        ex_types[e["type"]] = ex_types.get(e["type"], 0) + 1
no_ex = [l["id"] for l in lessons if len(l["exercises"]) < 2]
print(f"lessons: {len(lessons)}  modules: {len(modules)}  questions: {total}")
rung_str = " ".join(f"{k}={ex_types[k]}" for k in sorted(ex_types))
print(f"exercises: {ex_total} across {len(lessons)} lessons  by rung: {rung_str}")
print(f"lessons with only the E rung: {len(no_ex)}" + (f" -> {no_ex}" if no_ex else ""))
print(f"correct-answer positions: {pos}  ({[round(100*p/total,1) for p in pos]}%)")
print(f"longest-is-correct: {longest}/{total} = {round(100*longest/total,1)}%  (chance 25%)")
missing = [l["file"] for l in lessons if not (here / l["file"]).exists()]
print("missing files:", missing or "none")
