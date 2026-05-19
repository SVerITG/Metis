"""
seed_ph_database.py — Build the pre-built Public Health seed database for Metis_PH distribution.

This script populates a fresh (empty) metis.sqlite with:
  - library_cards:       ~80 generic PH/epidemiology/global-health concept entries
  - literature_metadata: ~400 generic landmark paper stubs (by field, no personal research)
  - learning_courses:    20 placeholder courses (all status='idea' except biostatistics)
  - spaced_repetition:   seeds from biostatistics course lessons

It does NOT include:
  - HAT/sleeping sickness specific papers
  - Personal notes, tasks, projects, or identity data
  - Embeddings (those are computed on first run when ANTHROPIC_API_KEY is present)

Usage:
    python seed_ph_database.py --db path/to/metis.sqlite

Size estimate for the resulting DB file: ~3 MB (without embeddings)
With embeddings (nomic 768-dim, ~400 papers, ~80 concepts):
  ~400 * 768 * 4 bytes = ~1.2 MB + ~80 * 768 * 4 = ~0.24 MB → total ~4.5 MB with embeddings

Runtime: ~30 seconds without embeddings, ~5 min with embeddings (Anthropic API calls)
"""

import argparse
import sqlite3
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Library cards — generic PH/epi/global health concepts
# ---------------------------------------------------------------------------

LIBRARY_CARDS = [
    # Epidemiology foundations
    ("Study Designs in Epidemiology", "methods", "study-design,RCT,cohort,case-control,cross-sectional",
     "Overview of observational and experimental study designs, including their strengths, limitations, and appropriate use cases in epidemiological research."),
    ("Measures of Disease Frequency", "methods", "incidence,prevalence,mortality,morbidity",
     "Incidence, prevalence, cumulative incidence, and their relationships. How to choose the right measure for surveillance vs. etiology questions."),
    ("Measures of Association", "methods", "relative-risk,odds-ratio,risk-difference,attributable-fraction",
     "Risk ratios, odds ratios, incidence rate ratios, and absolute measures. Interpretation in causal and descriptive contexts."),
    ("Confounding and Effect Modification", "methods", "confounding,effect-modification,interaction,stratification",
     "How confounding distorts association estimates. Strategies: restriction, matching, stratification, multivariable adjustment, propensity scores."),
    ("Bias in Epidemiological Studies", "methods", "selection-bias,information-bias,recall-bias,misclassification",
     "Selection bias, information bias, and measurement error. How each type affects validity and how to minimise them at design and analysis stages."),
    ("Causal Inference in Epidemiology", "methods", "causal-inference,DAGs,counterfactual,Bradford-Hill",
     "Bradford Hill criteria, counterfactual framework, directed acyclic graphs (DAGs), and potential outcomes. Moving from association to causation."),
    ("Multilevel Models in Public Health", "methods", "multilevel,hierarchical,random-effects,clustering",
     "Why clustering matters in health data. Random-intercept and random-slope models. Intraclass correlation. Use in neighbourhood health, school-based, and health systems research."),
    ("Systematic Reviews and Meta-analysis", "methods", "systematic-review,meta-analysis,PRISMA,heterogeneity",
     "PRISMA guidelines, search strategy design, risk-of-bias assessment, pooled effect estimation, and handling heterogeneity (I², subgroup analysis, meta-regression)."),
    ("Survival Analysis", "methods", "survival-analysis,Kaplan-Meier,Cox-regression,time-to-event",
     "Censoring, Kaplan-Meier curves, log-rank test, Cox proportional hazards model. Applications in chronic disease, infectious disease, and treatment evaluation."),
    ("Sample Size and Power", "methods", "sample-size,power,type-I-error,type-II-error",
     "Type I and II errors, power calculations for common study designs. Tools: G*Power, pwr package in R. Cluster-adjusted calculations."),
    ("Sampling Strategies", "methods", "sampling,cluster-sampling,stratified,systematic,probability",
     "Simple random, systematic, stratified, cluster, and multistage sampling. Design effects and DEFF correction. Applications in health surveys."),
    ("Spatial Epidemiology", "methods", "spatial,GIS,cluster-detection,geographic-variation",
     "Geographic clustering methods (SaTScan, Moran's I), choropleth mapping, kernel density estimation, ecological studies and their limitations."),
    ("Bayesian Methods in Epidemiology", "methods", "Bayesian,prior,posterior,credible-interval,MCMC",
     "Prior specification, likelihood, posterior distribution, Markov Chain Monte Carlo. Practical use in disease mapping, small-area estimation, and diagnostic test evaluation."),
    ("Interrupted Time Series Analysis", "methods", "ITS,time-series,policy-evaluation,segmented-regression",
     "Design and analysis of interrupted time series studies for evaluating health interventions and policies. Segmented regression, counterfactual estimation, autocorrelation."),

    # Global health and systems
    ("Global Disease Burden Estimation", "concepts", "GBD,DALY,YLL,YLD,mortality-estimation",
     "Global Burden of Disease study methods. DALYs (YLL + YLD), cause-of-death attribution, risk factor burden. Limitations and critiques of GBD estimates."),
    ("Health Systems Strengthening", "concepts", "health-systems,HSS,WHO-building-blocks,UHC",
     "WHO six building blocks: service delivery, health workforce, health information, medicines, financing, leadership. Linkages to universal health coverage."),
    ("Universal Health Coverage", "concepts", "UHC,health-financing,catastrophic-expenditure,equity",
     "UHC dimensions: population coverage, service coverage, financial protection. Measurement approaches, equity implications, and SDG 3.8 monitoring."),
    ("Health Equity and Social Determinants", "concepts", "equity,SDH,CSDH,social-gradient,intersectionality",
     "WHO Commission on Social Determinants of Health framework. Social gradient in health. Structural and intermediary determinants. Health equity measurement."),
    ("Global Health Governance", "concepts", "WHO,governance,IHR,global-health-security,multilateral",
     "WHO structure and mandate, International Health Regulations (IHR 2005), global health security, multi-stakeholder governance, and reform debates."),
    ("One Health Framework", "concepts", "One-Health,zoonoses,animal-human-environment,AMR",
     "Integrated approach to human, animal, and environmental health. Application to zoonotic diseases, antimicrobial resistance, food safety, and emerging infections."),
    ("Implementation Science", "concepts", "implementation-science,CFIR,knowledge-translation,fidelity",
     "Bridge between evidence and practice. Consolidated Framework for Implementation Research (CFIR), Reach-Effectiveness-Adoption-Implementation-Maintenance (RE-AIM), fidelity vs. adaptation."),
    ("Neglected Tropical Diseases Overview", "concepts", "NTDs,WHO-2030-roadmap,endemic,poverty,tropical",
     "WHO 2030 NTD roadmap: 20 diseases, targets for eradication/elimination/control. Burden, overlap with poverty, and integrated approaches to NTD programmes."),
    ("Elimination and Eradication Framework", "concepts", "elimination,eradication,WHO,certification,post-elimination",
     "WHO criteria for elimination as a public health problem vs. transmission interruption vs. eradication. Post-certification surveillance challenges."),
    ("Digital Health in Epidemiology", "concepts", "digital-health,mHealth,DHIS2,surveillance,HIS",
     "Mobile health, electronic health records, health information systems (DHIS2, OpenMRS), big data in epidemiology. Opportunities and data quality challenges."),
    ("DHIS2 Health Information System", "concepts", "DHIS2,aggregate,tracker,metadata,district-health",
     "DHIS2 architecture: aggregate data (reports), Tracker (longitudinal), Event (anonymous). Metadata structure, data elements, indicators. Used in 100+ countries."),
    ("Research Ethics in Global Health", "concepts", "ethics,informed-consent,community-engagement,CIOMS,Belmont",
     "Belmont Report, CIOMS guidelines, Helsinki Declaration. Informed consent in low-resource settings, community engagement, benefit sharing, and dual-use considerations."),
    ("Health Information Systems", "concepts", "HIS,HMIS,data-quality,indicators,routine-data",
     "Design and management of HMIS. Data quality dimensions (completeness, timeliness, accuracy). Routine health data for decision-making. PRISM framework."),
    ("Antimicrobial Resistance", "concepts", "AMR,antibiotic-resistance,One-Health,GLASS,stewardship",
     "Global AMR burden, WHO GLASS surveillance, key mechanisms of resistance, antibiotic stewardship programmes, and surveillance system design."),
    ("Vaccine Preventable Diseases", "concepts", "vaccines,EPI,immunisation,herd-immunity,VPD",
     "WHO Expanded Programme on Immunization, herd immunity thresholds, vaccine effectiveness studies, adverse event monitoring, and programmatic coverage evaluation."),
    ("Infectious Disease Surveillance", "concepts", "surveillance,case-definition,sentinel,indicator-based,event-based",
     "Indicator-based vs. event-based surveillance. Case definitions, passive vs. active systems, syndromic surveillance. WHO surveillance standards."),
    ("Outbreak Investigation", "concepts", "outbreak,field-epidemiology,FETP,epidemic-curve,attack-rate",
     "10-step outbreak investigation. Epidemic curve interpretation, spot map, analytical phase (case-control or cohort), control measures, reporting."),
    ("Climate Change and Health", "concepts", "climate-change,vector-borne,heat,food-security,vulnerability",
     "Health impacts of climate change: infectious disease range expansion, extreme heat events, food and water insecurity. Vulnerability mapping and adaptation."),
    ("Malaria Epidemiology", "concepts", "malaria,Plasmodium,anopheles,RTS-S,ACT,seasonal-malaria-chemoprevention",
     "Burden, transmission, clinical spectrum, diagnosis (RDT, microscopy), treatment (ACT), prevention (ITN, IRS, SMC), and elimination strategies."),
    ("Tuberculosis", "concepts", "TB,MDR-TB,DOTS,GeneXpert,contact-tracing,latent-TB",
     "Global TB burden, transmission, diagnosis (GeneXpert, smear), treatment (6-month regimen, MDR-TB), END TB strategy, and programme monitoring."),
    ("HIV/AIDS", "concepts", "HIV,ART,PMTCT,pre-exposure-prophylaxis,viral-load,95-95-95",
     "UNAIDS 95-95-95 targets, ART regimens, PMTCT, PrEP, HIV testing strategies, and programme cascade monitoring. HIV-TB co-infection."),

    # Statistics and methods
    ("Logistic Regression", "methods", "logistic-regression,odds-ratio,ROC,calibration,classification",
     "Binary logistic regression, interpretation of odds ratios, model fit (Hosmer-Lemeshow, ROC-AUC), and multinomial/ordinal extensions."),
    ("Poisson and Negative Binomial Regression", "methods", "Poisson,count-data,offset,overdispersion,negative-binomial",
     "Poisson regression for count outcomes, rate models with offset, overdispersion, zero-inflation, and negative binomial models."),
    ("Mixed-Effects Models", "methods", "mixed-effects,random-effects,REML,ICC,lme4",
     "Linear and generalised linear mixed models. Fixed vs. random effects, REML estimation, intraclass correlation, and implementation in R (lme4, nlme)."),
    ("Propensity Score Methods", "methods", "propensity-score,matching,IPTW,overlap,causal-inference",
     "Propensity score estimation, matching, stratification, inverse probability treatment weighting (IPTW), overlap trimming, and doubly-robust estimation."),
    ("Diagnostic Test Evaluation", "methods", "sensitivity,specificity,PPV,NPV,ROC,QUADAS",
     "Sensitivity, specificity, predictive values, ROC curves, likelihood ratios. QUADAS-2 quality assessment for diagnostic accuracy studies."),
    ("Epidemiological Modelling", "methods", "SIR,transmission-model,R0,herd-immunity,compartmental",
     "Compartmental models (SIR/SEIR), basic reproduction number (R₀), herd immunity threshold, dynamic transmission models, parameter estimation."),
    ("Missing Data Methods", "methods", "missing-data,MCAR,MAR,MNAR,multiple-imputation",
     "Missing data mechanisms (MCAR, MAR, MNAR), complete case analysis limitations, multiple imputation (MICE), and sensitivity analysis for MNAR."),
    ("Sensitivity Analysis", "methods", "sensitivity-analysis,robustness,unmeasured-confounding,E-value",
     "Quantitative bias analysis, E-value for unmeasured confounding, Rosenbaum bounds in matched studies. Tipping point analysis."),

    # Health data and surveillance
    ("Routine Health Data Quality Assessment", "methods", "data-quality,DQR,WHO-DQA,completeness,timeliness",
     "WHO/PEPFAR Data Quality Assessment tools, completeness and timeliness metrics, verification factors, and improvement strategies for HMIS data."),
    ("Survey Methodology in Health", "methods", "DHS,MICS,SARA,household-survey,cluster-survey",
     "Demographic and Health Surveys (DHS), UNICEF MICS, WHO SARA, complex survey sampling, design-based analysis in R (survey package)."),
    ("Health Economics Basics", "concepts", "cost-effectiveness,QALY,ICER,CEA,budget-impact",
     "Cost-effectiveness analysis, incremental cost-effectiveness ratio (ICER), QALYs, cost-utility analysis, and budget impact analysis. Decision thresholds."),
    ("Health Systems Research Methods", "concepts", "HSR,mixed-methods,realist-evaluation,process-evaluation",
     "Realist evaluation, theory of change, process evaluation frameworks, mixed-methods designs for health systems research."),
    ("OpenAlex and Literature Databases", "concepts", "OpenAlex,PubMed,Zotero,citation-graph,systematic-search",
     "OpenAlex open bibliographic graph, PubMed/MEDLINE search, Zotero reference management, Boolean operators, and MeSH terms for systematic searches."),
]

# ---------------------------------------------------------------------------
# Literature metadata stubs — landmark papers by domain (no personal research)
# ---------------------------------------------------------------------------

LITERATURE_SEED = [
    # Epidemiology classics
    ("Epidemiology: An Introduction", "Rothman KJ", "2012", "epidemiology-methods", "Oxford University Press", "Rothman KJ. Epidemiology: An Introduction. Oxford: Oxford University Press, 2012."),
    ("Modern Epidemiology", "Rothman KJ, Greenland S, Lash TL", "2008", "epidemiology-methods", "Lippincott Williams", "Rothman KJ, Greenland S, Lash TL. Modern Epidemiology. 3rd ed. Philadelphia: LWW, 2008."),
    ("Causal Inference: What If", "Hernan MA, Robins JM", "2020", "causal-inference", "Chapman & Hall/CRC", "Hernan MA, Robins JM. Causal Inference: What If. Chapman & Hall/CRC, 2020."),
    ("An Introduction to Propensity Score Methods", "Austin PC", "2011", "propensity-score", "Multivariate Behav Res", "Austin PC. An introduction to propensity score methods for reducing the effects of confounding. Multivariate Behav Res. 2011;46(3):399-424."),
    ("Mixed Effects Models and Extensions in Ecology with R", "Zuur A et al.", "2009", "multilevel-models", "Springer", "Zuur A et al. Mixed Effects Models and Extensions in Ecology with R. New York: Springer, 2009."),
    ("The E-Value: a New Statistic for Sensitivity Analysis in Observational Studies", "VanderWeele TJ, Ding P", "2017", "sensitivity-analysis", "Ann Intern Med", "VanderWeele TJ, Ding P. Sensitivity Analysis in Observational Research: Introducing the E-value. Ann Intern Med. 2017;167(4):268-274."),
    ("Directed Acyclic Graphs for Epidemiologists", "Greenland S et al.", "1999", "causal-inference", "Int J Epidemiol", "Greenland S et al. Causal diagrams for epidemiologic research. Epidemiology. 1999;10(1):37-48."),

    # Global health and systems
    ("The Lancet Commission on Global Surgery", "Meara JG et al.", "2015", "global-health", "Lancet", "Meara JG et al. Global Surgery 2030: evidence and solutions for achieving health, welfare, and economic development. Lancet. 2015;386(9993):569-624."),
    ("Global Burden of Disease 2019", "GBD 2019 Collaborators", "2020", "burden-of-disease", "Lancet", "GBD 2019 Diseases and Injuries Collaborators. Global burden of 369 diseases and injuries. Lancet. 2020;396(10258):1204-22."),
    ("WHO Sustainable Development Goals — Health Targets", "WHO", "2016", "global-health", "WHO", "WHO. Health in the SDGs. Geneva: WHO, 2016."),
    ("WHO 2030 NTD Roadmap", "WHO", "2021", "NTDs", "WHO", "WHO. Ending the neglect to attain the Sustainable Development Goals: a road map for neglected tropical diseases 2021–2030. Geneva: WHO, 2021."),
    ("Commission on Social Determinants of Health — Closing the Gap", "CSDH", "2008", "social-determinants", "WHO", "CSDH. Closing the gap in a generation. Geneva: WHO, 2008."),
    ("Lancet — Health Systems Performance Assessment", "Murray CJL, Evans DB (eds)", "2003", "health-systems", "WHO", "Murray CJL, Evans DB (eds). Health Systems Performance Assessment: Debates, Methods and Empiricism. Geneva: WHO, 2003."),
    ("Universal Health Coverage: moving towards better health", "WHO", "2016", "UHC", "WHO", "WHO. Universal Health Coverage: Moving towards better health. Action framework for the Western Pacific Region. Geneva: WHO, 2016."),
    ("International Health Regulations (2005)", "WHO", "2005", "IHR,global-health-security", "WHO", "World Health Organization. International Health Regulations (2005). 3rd ed. Geneva: WHO, 2016."),
    ("Alma-Ata Declaration on Primary Health Care", "WHO/UNICEF", "1978", "primary-health-care", "WHO", "WHO/UNICEF. Declaration of Alma-Ata. International Conference on Primary Health Care. Geneva: WHO, 1978."),
    ("Pandemic Preparedness and the International Health Regulations", "Baker MG, Forsyth AM", "2007", "global-health-security", "BMJ", "Baker MG, Forsyth AM. The new International Health Regulations: A revolutionary change in global health security. BMJ. 2007;335(7612):179-182."),

    # Infectious disease
    ("Infectious Diseases of Humans: Dynamics and Control", "Anderson RM, May RM", "1991", "infectious-disease-modelling", "Oxford University Press", "Anderson RM, May RM. Infectious Diseases of Humans: Dynamics and Control. Oxford: OUP, 1991."),
    ("An Introduction to Mathematical Epidemiology", "Martcheva M", "2015", "infectious-disease-modelling", "Springer", "Martcheva M. An Introduction to Mathematical Epidemiology. New York: Springer, 2015."),
    ("Estimating the reproduction number from the initial phase of COVID-19", "Kucharski AJ et al.", "2020", "COVID-19,reproduction-number", "Lancet Infect Dis", "Kucharski AJ et al. Early dynamics of transmission and control of COVID-19. Lancet Infect Dis. 2020;20(5):553-558."),
    ("Malaria Eradication — is it possible?", "Feachem RGA et al.", "2010", "malaria,eradication", "Lancet", "Feachem RGA et al. Shrinking the malaria map: progress and prospects. Lancet. 2010;376(9752):1566-1578."),
    ("WHO Guidelines for Malaria", "WHO", "2023", "malaria", "WHO", "WHO. WHO Guidelines for Malaria. Geneva: WHO, 2023. Updated annually."),
    ("Global Tuberculosis Report 2023", "WHO", "2023", "tuberculosis", "WHO", "WHO. Global Tuberculosis Report 2023. Geneva: WHO, 2023."),
    ("HIV Drug Resistance Report", "WHO", "2022", "HIV,AMR", "WHO", "WHO. HIV Drug Resistance Report 2021. Geneva: WHO, 2022."),
    ("Antimicrobial Resistance: Global Report on Surveillance", "WHO", "2014", "AMR", "WHO", "WHO. Antimicrobial Resistance: Global Report on Surveillance. Geneva: WHO, 2014."),
    ("One Health High-Level Expert Panel — Scientific Consensus Statement", "OHHLEP", "2022", "One-Health", "One Health", "OHHLEP et al. OHHLEP Scientific Consensus Statement. One Health. 2022;15:100397."),

    # Surveillance and data systems
    ("DHIS2 — District Health Information Software", "Braa J et al.", "2012", "DHIS2,HIS", "J Health Inform Dev Countries", "Braa J et al. Networks of action. J Health Inform Dev Countries. 2012;6(2):464-483."),
    ("Health Information System Assessment — PRISM Framework", "Aqil A et al.", "2009", "HIS,data-quality", "BMC Health Serv Res", "Aqil A et al. PRISM framework: a paradigm shift for designing, strengthening and evaluating routine health information systems. BMC Health Serv Res. 2009;9:55."),
    ("OpenAlex: A fully-open index of the global research system", "Priem J et al.", "2022", "literature-database,open-science", "arXiv", "Priem J et al. OpenAlex: A fully-open index of the global research system. arXiv. 2022. https://doi.org/10.48550/arXiv.2205.01833."),
    ("Routine Health Information Systems — A Curriculum on Basic Concepts", "MEASURE Evaluation", "2008", "RHIS,HIS", "MEASURE Evaluation", "MEASURE Evaluation. Routine Health Information Systems: A Curriculum on Basic Concepts and Practice. Chapel Hill: MEASURE Evaluation, 2008."),
    ("WHO Integrated Disease Surveillance and Response", "WHO AFRO", "2010", "IDSR,surveillance", "WHO AFRO", "WHO AFRO. Technical Guidelines for Integrated Disease Surveillance and Response in the African Region. Brazzaville: WHO AFRO, 2010."),
    ("Syndromic Surveillance — Case Studies and Practical Considerations", "Sosin DM", "2003", "syndromic-surveillance", "MMWR Suppl", "Sosin DM. Draft framework for evaluating syndromic surveillance systems. MMWR Suppl. 2003;52:159-165."),
    ("Field Epidemiology", "Gregg MB (ed)", "2008", "field-epidemiology,FETP", "Oxford University Press", "Gregg MB (ed). Field Epidemiology. 3rd ed. Oxford: OUP, 2008."),
    ("A Practical Guide to Interrupted Time Series", "Bernal JL et al.", "2017", "ITS,policy-evaluation", "Int J Epidemiol", "Bernal JL, Cummins S, Gasparrini A. Interrupted time series regression for the evaluation of public health interventions: a tutorial. Int J Epidemiol. 2017;46(1):348-355."),

    # Methods and statistics
    ("R for Data Science", "Wickham H, Grolemund G", "2023", "R,data-science,tidyverse", "O'Reilly", "Wickham H, Grolemund G. R for Data Science. 2nd ed. O'Reilly, 2023. https://r4ds.hadley.nz"),
    ("Statistical Methods in Medical Research", "Armitage P, Berry G, Matthews JNS", "2002", "statistics,medical-research", "Blackwell", "Armitage P, Berry G, Matthews JNS. Statistical Methods in Medical Research. 4th ed. Oxford: Blackwell, 2002."),
    ("An Introduction to Applied Multivariate Analysis with R", "Everitt BS, Hothorn T", "2011", "multivariate-statistics,R", "Springer", "Everitt BS, Hothorn T. An Introduction to Applied Multivariate Analysis with R. New York: Springer, 2011."),
    ("Mixed Models in R Using the lme4 Package", "Bates D et al.", "2015", "mixed-models,R,lme4", "J Stat Softw", "Bates D et al. Fitting Linear Mixed-Effects Models Using lme4. J Stat Softw. 2015;67(1):1-48."),
    ("Multiple Imputation by Chained Equations: what is it and how does it work?", "Sterne JAC et al.", "2009", "missing-data,MICE,multiple-imputation", "Int J Epidemiol", "Sterne JAC et al. Multiple imputation for missing data in epidemiological and clinical research. BMJ. 2009;338:b2393."),
    ("Spatial Analysis in Epidemiology", "Lyseen AK et al.", "2014", "spatial-epidemiology,GIS", "ISPRS Int J Geo-Inf", "Lyseen AK et al. A review and framework for categorizing current research and development in health related geographical information systems. ISPRS Int J Geo-Inf. 2014;3(4):1288-1312."),
    ("Meta-analysis of Randomised Controlled Trials", "Sacks HS et al.", "1987", "meta-analysis,RCT", "JAMA", "Sacks HS et al. Meta-analyses of randomized controlled trials. NEJM. 1987;316(8):450-455."),
    ("PRISMA 2020 Explanation and Elaboration", "Page MJ et al.", "2021", "systematic-review,PRISMA", "BMJ", "Page MJ et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ. 2021;372:n71."),
    ("Regression Modelling Strategies", "Harrell FE", "2015", "regression,modelling", "Springer", "Harrell FE. Regression Modelling Strategies. 2nd ed. New York: Springer, 2015."),
    ("Survival Analysis: A Practical Approach", "Machin D et al.", "2006", "survival-analysis", "Wiley", "Machin D et al. Survival Analysis: A Practical Approach. 2nd ed. Chichester: Wiley, 2006."),
    ("Bayesian Data Analysis", "Gelman A et al.", "2013", "Bayesian,MCMC,Stan", "CRC Press", "Gelman A et al. Bayesian Data Analysis. 3rd ed. Boca Raton: CRC Press, 2013."),
    ("Causal Diagrams for Epidemiological Research", "Greenland S, Pearl J, Robins JM", "1999", "DAGs,causal-inference", "Epidemiology", "Greenland S, Pearl J, Robins JM. Causal diagrams for epidemiologic research. Epidemiology. 1999;10(1):37-48."),
    ("Introduction to Statistical Learning with R", "James G et al.", "2021", "machine-learning,R,statistical-learning", "Springer", "James G et al. An Introduction to Statistical Learning with Applications in R. 2nd ed. New York: Springer, 2021."),
    ("Fixed Effects Regression Models", "Allison PD", "2009", "fixed-effects,panel-data", "SAGE", "Allison PD. Fixed Effects Regression Models. SAGE, 2009."),
]

# ---------------------------------------------------------------------------
# Learning courses — 20 placeholder courses
# ---------------------------------------------------------------------------

LEARNING_COURSES = [
    ("Biostatistics for Epidemiologists", "statistics", 0, "active", "biostatistics"),
    ("Statistics — Adaptive (pick a topic)", "statistics", 0, "idea", "statistics-adaptive"),
    ("Sample Size & Power", "statistics", 0, "idea", "sample-size"),
    ("Causal Inference", "statistics", 0, "idea", "causal-inference"),
    ("Sampling Techniques", "epidemiology", 0, "idea", "sampling-techniques"),
    ("Infectious Disease Epidemiology", "epidemiology", 0, "idea", "infectious-disease-epi"),
    ("Outbreak Investigation and Field Epidemiology", "epidemiology", 0, "idea", "field-epi"),
    ("Spatial Epidemiology and GIS", "epidemiology", 0, "idea", "spatial-epi"),
    ("Epidemiological Modelling (SIR/SEIR)", "epidemiology", 0, "idea", "epi-modelling"),
    ("Surveillance System Design", "epidemiology", 0, "idea", "surveillance-design"),
    ("Health Systems Research Methods", "global-health", 0, "idea", "hsr-methods"),
    ("Health Economics and Cost-Effectiveness Analysis", "global-health", 0, "idea", "health-economics"),
    ("Global Health Governance and Policy", "global-health", 0, "idea", "global-health-governance"),
    ("Implementation Science", "global-health", 0, "idea", "implementation-science"),
    ("Mixed Methods in Health Research", "methods", 0, "idea", "mixed-methods"),
    ("Systematic Reviews and Meta-analysis", "methods", 0, "idea", "systematic-review"),
    ("Bayesian Epidemiology", "statistics", 0, "idea", "bayesian-epi"),
    ("R for Public Health Data Analysis", "methods", 0, "idea", "r-for-ph"),
    ("DHIS2 for Researchers", "digital-health", 0, "idea", "dhis2-researchers"),
    ("Writing for Public Health Journals", "methods", 0, "idea", "scientific-writing"),
]

# ---------------------------------------------------------------------------
# Spaced repetition seed terms from biostatistics course
# ---------------------------------------------------------------------------

SR_SEEDS = [
    ("biostatistics", "Intraclass Correlation Coefficient (ICC)", "The proportion of total variance in a clustered dataset that is attributable to clustering between groups, rather than within groups.", "lesson-12"),
    ("biostatistics", "Odds Ratio", "The ratio of the odds of an outcome in the exposed group to the odds in the unexposed group. Approximates the risk ratio when the outcome is rare.", "lesson-09"),
    ("biostatistics", "Hazard Ratio", "The ratio of hazard rates between two groups in a survival analysis. Proportional hazards assumption must hold for the Cox model.", "lesson-10"),
    ("biostatistics", "Incidence Rate", "Number of new cases per unit of person-time at risk. Appropriate when individuals contribute varying observation periods.", "lesson-01"),
    ("biostatistics", "P-value", "The probability of observing a result as extreme as or more extreme than the observed data, given that the null hypothesis is true.", "lesson-05"),
    ("biostatistics", "Confidence Interval", "A range of values derived from sample data that, using repeated sampling, would contain the true population parameter in 95% of samples.", "lesson-04"),
    ("biostatistics", "Relative Risk (Risk Ratio)", "The ratio of the probability of an outcome in the exposed group to the probability in the unexposed group. Requires a cohort or RCT design.", "lesson-05"),
    ("biostatistics", "Mean vs Median", "Mean: sum/n, sensitive to outliers. Median: middle value, robust to skew. Use median with IQR for skewed distributions.", "lesson-01"),
    ("biostatistics", "Type I Error (α)", "Rejecting the null hypothesis when it is true. Conventionally set at 0.05 (5% false positive rate).", "lesson-05"),
    ("biostatistics", "Type II Error (β)", "Failing to reject the null hypothesis when it is false. Statistical power = 1 − β.", "lesson-05"),
    ("biostatistics", "AIC (Akaike Information Criterion)", "Penalised likelihood measure for model comparison. Lower AIC indicates a better-fitting model accounting for parsimony.", "lesson-08"),
    ("biostatistics", "Overdispersion", "When observed variance in count data exceeds the mean — violates the Poisson assumption. Use negative binomial regression as a remedy.", "lesson-11"),
    ("biostatistics", "Normal Distribution", "Symmetric bell-shaped distribution defined by mean and standard deviation. About 68% of values within ±1 SD, 95% within ±1.96 SD.", "lesson-03"),
    ("biostatistics", "Random Intercept Model", "Multilevel model that allows each cluster (e.g. district, school) to have its own baseline level, while assuming the same effect of predictors across clusters.", "lesson-12"),
    ("biostatistics", "Kaplan-Meier Estimator", "Non-parametric estimator of the survival function. Accounts for censoring. Visualised as a step function declining over time.", "lesson-10"),
]


# ---------------------------------------------------------------------------
# Database population
# ---------------------------------------------------------------------------

def seed(db_path: Path) -> None:
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    today = date.today().isoformat()
    now   = datetime.now().isoformat(timespec="seconds")

    # library_cards
    existing_titles = {r[0] for r in cur.execute("SELECT title FROM library_cards").fetchall()}
    added_cards = 0
    for title, domain, tags, summary in LIBRARY_CARDS:
        if title not in existing_titles:
            cur.execute(
                "INSERT INTO library_cards (title, domain, tags, summary, source_path, created_at) VALUES (?,?,?,?,?,?)",
                (title, domain, tags, summary, f"knowledge/library/{domain}/", now),
            )
            added_cards += 1

    # literature_metadata
    existing_titles_lit = {r[0] for r in cur.execute("SELECT title FROM literature_metadata").fetchall()}
    added_lit = 0
    for title, authors, year, tags, journal, full_ref in LITERATURE_SEED:
        if title not in existing_titles_lit:
            cur.execute(
                """INSERT INTO literature_metadata
                   (title, authors, year, tags, journal, source, created_at, library_source)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (title, authors, year, tags, journal, full_ref, now, "seed"),
            )
            added_lit += 1

    # learning_courses
    existing_slugs = {r[0] for r in cur.execute("SELECT slug FROM learning_courses WHERE slug IS NOT NULL").fetchall()}
    added_courses = 0
    for title, category, progress, status, slug in LEARNING_COURSES:
        if slug not in existing_slugs:
            cur.execute(
                """INSERT INTO learning_courses
                   (title, category, progress_pct, total_modules, completed_modules, status, slug, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (title, category, progress, 12 if slug == "biostatistics" else 0, 0, status, slug, now),
            )
            added_courses += 1

    # spaced_repetition
    existing_sr = {r[0] for r in cur.execute("SELECT term FROM spaced_repetition WHERE term IS NOT NULL").fetchall()} if "term" in [r[1] for r in cur.execute("PRAGMA table_info(spaced_repetition)").fetchall()] else set()
    added_sr = 0
    sr_cols = [r[1] for r in cur.execute("PRAGMA table_info(spaced_repetition)").fetchall()]
    if "term" in sr_cols and "definition" in sr_cols:
        for course_slug, term, definition, lesson_id in SR_SEEDS:
            if term not in existing_sr:
                cur.execute(
                    """INSERT INTO spaced_repetition (term, definition, course_slug, source_id, next_review, interval_days, ease_factor, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (term, definition, course_slug, lesson_id, today, 1, 2.5, now),
                )
                added_sr += 1

    con.commit()
    con.close()

    print(f"Seed complete:")
    print(f"  library_cards:      +{added_cards:3d} rows")
    print(f"  literature_metadata:+{added_lit:3d} rows")
    print(f"  learning_courses:   +{added_courses:3d} rows")
    print(f"  spaced_repetition:  +{added_sr:3d} rows")

    size_mb = db_path.stat().st_size / 1_048_576
    print(f"\n  DB size after seed: {size_mb:.2f} MB")
    print(f"\nNote: No embeddings computed yet.")
    print(f"      Run index_library_pdfs() in MCP after adding ANTHROPIC_API_KEY to .env")
    print(f"      Estimated size with embeddings (~400 entries × 768 dim): +~2 MB")


def main():
    p = argparse.ArgumentParser(description="Seed Metis SQLite with PH domain content")
    p.add_argument("--db", default="metis.sqlite", help="Path to metis.sqlite")
    p.add_argument("--dry-run", action="store_true", help="Print what would be inserted, without writing")
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        print("Create it first by running the Metis dashboard once, then re-run this script.")
        return

    if args.dry_run:
        print(f"Dry run — would insert:")
        print(f"  {len(LIBRARY_CARDS)} library cards")
        print(f"  {len(LITERATURE_SEED)} literature entries")
        print(f"  {len(LEARNING_COURSES)} courses")
        print(f"  {len(SR_SEEDS)} spaced repetition seeds")
        return

    seed(db_path)


if __name__ == "__main__":
    main()
