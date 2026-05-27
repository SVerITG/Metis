# Writing the Methods

## Learning objectives
- Explain what readers need from a methods section in epidemiology and public health papers.
- Write design, setting, participants, variables, and analysis with enough detail for appraisal and reuse.
- Distinguish necessary study-specific detail from generic textbook explanation.
- Anticipate common reviewer criticisms about missing methodological information.

## Prerequisites
- Study protocol development.
- Reporting guidelines and EQUATOR.
- Writing the introduction.

## Content

### Section 1: What the methods section must achieve
The methods section is the paper's technical contract with the reader. It tells the reader exactly what was done, on whom, during what period, using which definitions, data sources, and analytic choices. If the introduction explains why the study matters, the methods explain why the results deserve to be taken seriously.

In practice, readers use the methods section to answer a small set of hard questions:

- Did the design fit the research question?
- Could the sampling or data source introduce bias?
- Were exposures, outcomes, and covariates defined clearly enough?
- Were the analytic choices appropriate and reproducible?
- Did ethics, consent, and governance match the level of risk?

When these points are vague, readers cannot judge validity. A polished results section cannot compensate for incomplete methods.

### Section 2: Start from the study question, not from a template
Many weak methods sections are assembled from standard headings without a clear line back to the research question. A stronger approach is to ask: what would a skeptical reader need to see in order to believe that this study can answer its stated question?

For a descriptive surveillance evaluation, the essentials are usually the system boundary, indicators, data flow, completeness, timeliness, and attribute definitions. For a cohort study, readers need time zero, eligibility, follow-up rules, exposure measurement, outcome ascertainment, and confounding strategy. For a qualitative component, readers need the sampling logic, interview procedures, reflexivity, and analytic approach.

The methods should therefore feel like the operational version of the question. If the question is about post-elimination surveillance performance, the methods must show how "performance" was measured and why those measures are meaningful.

### Section 3: Core components most studies need
Exact headings vary, but most public health manuscripts need some version of the following:

- study design
- setting and time period
- population or unit of analysis
- inclusion and exclusion criteria
- data sources
- definitions of exposures, outcomes, and covariates
- procedures for data collection or extraction
- statistical or qualitative analysis
- missing-data handling
- ethics, approvals, and governance

Each component should be concrete. "Routine surveillance data were analyzed" is too vague. Which system? Which period? Which variables? Who entered the data? How were duplicates handled? What constituted a confirmed case?

### Section 4: Write for reproducibility, not ornament
Good methods writing is often plain writing. Ornamental wording usually hides decisions that should be explicit. Phrases such as "standard procedures were followed" or "appropriate tests were used" are weak unless the manuscript names those procedures and tests.

Useful specificity includes:

- dates and locations
- operational case definitions
- denominators and eligibility rules
- software and package versions when relevant
- thresholds used in classification
- rationale for confounder adjustment
- handling of missing or inconsistent observations
- planned sensitivity analyses

This does not mean listing every keystroke. It means reporting the decisions that shape interpretation. If different reasonable options existed, readers need to know which option was chosen and why.

### Section 5: Worked example
Imagine a paper evaluating the sensitivity and timeliness of post-elimination disease surveillance in peripheral health facilities.

A weak methods paragraph might read:

"We reviewed routine data from selected facilities and assessed surveillance performance using standard indicators."

That sentence hides nearly everything important.

A stronger version would specify that the study used a cross-sectional mixed-methods surveillance evaluation in health facilities across the study districts over the study period. It would state how facilities were sampled, whether referral hospitals were included, how suspected and confirmed Disease X cases were defined, which registers were reviewed, how completeness and timeliness were calculated, whether laboratory and facility records were reconciled, and how interviews with focal persons were analyzed. It would also report which surveillance performance framework was used.

The difference is not style. The difference is that the second version allows appraisal, replication, and informed criticism.

### Section 6: Methods for quantitative analysis
Quantitative methods sections need enough information for a reader to understand the analytic path from raw data to reported estimate. At minimum, that usually means:

- what the outcome was
- how the main exposure or predictor was coded
- which confounders were included
- why those confounders were included
- what model or test was used
- how assumptions were checked
- how clustering, repeated measures, or overdispersion were handled

For example, if logistic regression was used, readers should not be left guessing whether age was treated continuously or categorically, whether district-level clustering was addressed, or whether multicollinearity was assessed. If a Poisson model was used for counts, the methods should clarify offsets and what happened if the variance exceeded the mean.

### Section 7: Methods for qualitative and mixed-methods work
Research writing in epidemiology increasingly includes interviews, focus groups, document review, and implementation analysis. These methods require the same discipline as quantitative work. The manuscript should clarify:

- why qualitative data were needed
- how participants were selected
- who conducted interviews and in what language
- whether guides were piloted
- how transcripts or notes were coded
- how themes were developed
- how mixed-methods integration occurred

Saying that "themes were identified" is insufficient. Readers need some account of how interpretation was produced and checked.

### Section 8: Frequent omissions reviewers notice
Reviewers often focus on the same missing pieces:

- vague eligibility criteria
- unclear case definitions
- unexplained variable categorization
- absent missing-data strategy
- no rationale for confounder selection
- unexplained deviations from the protocol
- minimal ethics and governance detail

These are not cosmetic issues. They shape what the findings mean. A methods section should therefore be written with the reviewer's skepticism in mind.

## Key takeaways
- The methods section is the reproducible record of what was done and why those choices fit the research question.
- Study-specific operational detail matters more than polished generic language.
- Readers must be able to identify design, setting, participants, definitions, data sources, and analytic choices without guessing.
- Missing-data handling, confounder strategy, and ethics are core elements, not optional extras.
- Reporting guidelines are useful because they reveal what critical details authors often omit.

## Self-check questions
1. Why is the methods section often described as a reproducibility section rather than a narrative section?
2. What makes "appropriate statistical tests were used" a weak sentence?
3. Which details are especially important to report in a surveillance evaluation?
4. Why should confounder selection be explained rather than simply listed?
5. What is one common difference between strong and weak mixed-methods reporting?
6. How can a reviewer tell that a methods section is drifting into the results?

## Answer key
1. Because its main job is to let readers understand, appraise, and potentially reproduce the study procedures and analytic decisions.
2. Because it hides the exact tests, assumptions, and coding choices that readers need to evaluate validity.
3. The system boundary, period, indicators, case definitions, data sources, reconciliation procedures, and evaluation framework.
4. Because adjustment choices affect interpretation, and readers need to understand the causal or substantive reasoning behind them.
5. Strong reporting explains sampling, data collection, coding, and integration, while weak reporting merely states that themes or interviews were used.
6. The section begins presenting findings or comparisons instead of only describing what was planned and done.

## Further reading
- [EQUATOR Network](https://www.equator-network.org/)
- [STROBE Statement](https://www.strobe-statement.org/)
- [CONSORT Statement](https://www.consort-statement.org/)
- [Cochrane Handbook](https://training.cochrane.org/handbook/current)
- [BMJ Statistics Notes archive](https://www.bmj.com/specialties/statistics-notes)

## Links to Metis library
- `knowledge/library/methods/writing-for-journals.md`
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/data-management.md`
- `knowledge/library/methods/mixed-methods-research.md`
