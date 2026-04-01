# Descriptive Statistics

## Learning objectives
- Distinguish common data types and choose suitable summary measures for each.
- Summarize central tendency, spread, and distribution shape.
- Use tables and plots to detect skew, outliers, subgroup differences, and data-quality problems.
- Explain why careful descriptive work should come before formal modeling or hypothesis testing.

## Prerequisites
- None.

## Content

### Section 1: Why descriptive statistics matter
Descriptive statistics are the first disciplined look at a dataset. Before asking whether an association is significant or whether a model converges, you need to know what the data actually look like. How many observations are there? What types of variables are present? Are the values plausible? Is the distribution symmetric, skewed, clustered, or full of impossible codes?

This is not a trivial preliminary step. Good descriptive work often catches problems that would otherwise contaminate the rest of the analysis: unit mix-ups, miscoding, duplicated observations, extreme outliers, missingness patterns, and subgroup differences that should shape the analytic plan.

In epidemiology and public-health practice, descriptive statistics also provide the first substantive picture of the population under study. They help you understand who is in the dataset, how outcomes are distributed, and whether the sample resembles the target population.

### Section 2: Start with variable type
The right summary depends on what kind of variable you are describing.

Common variable types include:

- **categorical nominal** variables, such as sex, district, or diagnostic category
- **categorical ordinal** variables, such as disease severity or Likert-scale responses
- **binary** variables, such as yes/no treatment status
- **continuous** variables, such as age, blood pressure, or parasite density
- **count** variables, such as number of visits or number of cases

You should not summarize all of these in the same way. A mean makes sense for systolic blood pressure but not for district of residence. Frequencies and proportions are natural for categories. Means, medians, standard deviations, and interquartile ranges are more natural for continuous variables.

Choosing the wrong summary is more than a stylistic mistake. It can hide the structure of the data and mislead interpretation.

### Section 3: Central tendency
Measures of central tendency describe the "middle" of a variable, but different measures answer slightly different questions.

**Mean** is the arithmetic average. It uses all observations and is useful when the distribution is roughly symmetric and outliers are not dominating the result.

**Median** is the 50th percentile. It is often more informative for skewed variables because it is less sensitive to extreme values.

**Mode** is the most common value or category. It is more useful for categorical variables or distributions with obvious peaks.

For example, if age at diagnosis is strongly right-skewed because most patients are young but a few are very old, the mean may be pulled upward. In that case, the median usually gives a better sense of the typical patient.

### Section 4: Spread and variability
Two datasets can have the same mean but very different variability. That is why measures of spread are essential.

Common measures include:

- **range:** minimum to maximum
- **interquartile range (IQR):** distance between the 25th and 75th percentiles
- **variance:** average squared deviation from the mean
- **standard deviation (SD):** square root of the variance

The SD is widely used with symmetric continuous data. The IQR is often better for skewed data because it summarizes the middle half of observations without being heavily influenced by extremes.

When reporting a variable, the central measure and spread measure should match the distribution. Mean with SD is common for roughly symmetric variables. Median with IQR is often better for skewed variables.

### Section 5: Shape matters
Distribution shape affects what summaries are sensible and what models may later be appropriate.

Important features include:

- **symmetry**
- **skewness**
- **multimodality**
- **outliers**
- **heaping or digit preference**

In epidemiologic data, skewness is common. Length of hospital stay, parasite counts, time to diagnosis, and expenditure data are often right-skewed. Some variables have ceiling or floor effects. Others show heaping because people round ages or dates.

This is why you should look at the distribution, not just the average.

### Section 6: Tables and graphics
Graphics are not optional decoration. They are part of statistical reasoning.

Useful displays include:

- **frequency tables** for categorical variables
- **histograms** for continuous distributions
- **boxplots** for center, spread, and outliers
- **bar charts** for comparing categories
- **scatterplots** for relationships between two continuous variables

A histogram can show skew or multiple peaks immediately. A boxplot can reveal extreme values or asymmetry. A scatterplot can expose nonlinear relationships, clustering, or miscoded points that a correlation coefficient alone would hide.

In practice, visual inspection often identifies problems faster than formal diagnostics.

### Section 7: Worked example - age at diagnosis
Imagine a surveillance dataset with ages at diagnosis for 12 patients:

`18, 20, 22, 24, 25, 26, 27, 29, 31, 33, 35, 72`

The mean age is:

\[
\frac{18+20+22+24+25+26+27+29+31+33+35+72}{12} = 30.2
\]

The median is the average of the 6th and 7th values:

\[
\frac{26+27}{2} = 26.5
\]

Interpretation:
- The mean is higher than the median because the value `72` pulls the average upward.
- The median is probably a better summary of the typical age in this small, skewed set.

A boxplot or histogram would make that pattern obvious immediately. This is a simple example, but the same logic applies to real surveillance data with long right tails.

### Section 8: Stratified description
Descriptive statistics should often be stratified rather than pooled.

If you summarize all patients together, you may miss meaningful structure by sex, district, year, age group, facility type, or intervention status. Stratification can reveal that one subgroup has a very different distribution, more missing data, or a distinct pattern of outliers.

For example, overall consultation delay may look moderate, but stratification may show much longer delays in remote districts. That is not a minor technical detail. It may change the entire interpretation of the dataset and the programmatic response.

### Section 9: Data quality and plausibility checks
Descriptive statistics are also a quality-control tool.

Questions to ask early include:

- Are there impossible values, such as negative ages or dates in the future?
- Are units consistent across sources?
- Are missing values concentrated in one site or one subgroup?
- Do some facilities report implausibly identical values?
- Are repeated records or duplicate IDs present?

If you skip descriptive review and jump straight to regression, you risk building a polished analysis on flawed data.

## Key takeaways
- Descriptive statistics are the first structured way to understand a dataset and check its quality.
- Summary measures should match the variable type and distribution.
- Mean and SD are often useful for symmetric continuous data; median and IQR are often better for skewed data.
- Tables and graphics are essential for detecting skew, outliers, miscoding, and subgroup differences.
- Stratified descriptive work often reveals patterns that pooled summaries hide.

## Self-check questions
1. Why might the median be preferable to the mean for a right-skewed variable?
2. What does the standard deviation summarize?
3. Why is a histogram often more informative than a mean alone?
4. What kind of variable is best summarized with counts and proportions?
5. Why should descriptive summaries often be stratified by subgroup?
6. Give one example of a data-quality problem that descriptive statistics can reveal quickly.

## Answer key
1. Because the median is less influenced by extreme high values and often better represents the typical observation in a skewed distribution.
2. The spread of values around the mean, measured as the square root of the variance.
3. Because it shows distribution shape, skewness, clustering, and outliers that a single average cannot reveal.
4. Categorical variables, including nominal, ordinal, and binary variables.
5. Because pooled summaries can hide meaningful differences across sex, age group, district, time period, or exposure status.
6. Examples include impossible values, heaping, duplicate records, extreme outliers, inconsistent units, or subgroup-specific missingness.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy statistics](https://www.khanacademy.org/math/statistics-probability)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/data-management.md`
- `06_library/methods/study-designs.md`
