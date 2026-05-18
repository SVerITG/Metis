# Probability Distributions

## Learning objectives
- Recognize common probability distributions used in epidemiology and public-health research.
- Match binomial, normal, and Poisson distributions to plausible data-generating processes.
- Distinguish population distributions from sampling distributions.
- Explain why distributional assumptions affect confidence intervals, p-values, and model choice.

## Prerequisites
- Probability basics.

## Content

### Section 1: Why distributions matter
A probability distribution describes how likely different values of a random variable are. In practice, distributions are the bridge between raw data and statistical models. They tell us what kinds of values are plausible, how much variability to expect, and which formulas for uncertainty make sense.

This matters because biostatistics is full of distributional assumptions. Confidence intervals, hypothesis tests, regression models, and simulation methods all depend on assumptions about how data arise. If the assumed distribution is badly mismatched to the data-generating process, inference can become unstable or misleading.

The goal is not to memorize every named distribution. The goal is to recognize the logic behind the most common ones and know when a simple approximation is reasonable.

### Section 2: Discrete versus continuous
Probability distributions are often grouped into **discrete** and **continuous** types.

**Discrete distributions** are used when values are countable, such as the number of cases, the number of positive tests, or the number of deaths in a household cluster.

**Continuous distributions** are used when values can vary along a continuum, such as age, blood pressure, hemoglobin concentration, or BMI.

This distinction matters because discrete variables do not behave like smooth measurements, and count data often need different models from continuous outcomes.

### Section 3: The binomial distribution
The **binomial distribution** applies when there are:

- a fixed number of trials
- two possible outcomes for each trial
- the same probability of success on each trial
- independence between trials

Examples in epidemiology include:

- number of people testing positive out of a fixed sample
- number of vaccinated individuals among a clinic roster
- number of survey respondents reporting an exposure

If 100 people are screened and each has probability `p` of being positive, the number of positives can be modeled as binomial under the usual assumptions.

This distribution underlies many common proportions and confidence intervals for proportions. It is especially useful when working with yes/no outcomes in fixed samples.

### Section 4: The normal distribution
The **normal distribution** is the familiar bell-shaped curve. It is symmetric around the mean, with most values clustered near the center and fewer values appearing far from it.

Many biological measurements are approximately normal, especially after excluding impossible values or when the variable is the result of many small additive influences. Even when the raw data are not perfectly normal, the normal distribution often becomes important because many sampling distributions are approximately normal under large samples.

However, the normal model is not universal. It performs poorly for heavily skewed variables, rare counts, zero-inflated data, and bounded outcomes such as probabilities.

That is why "just assume normality" is not a safe default. It may be a useful approximation, but it should be justified, not automatic.

### Section 5: The Poisson distribution
The **Poisson distribution** is commonly used for counts of events occurring over a defined amount of time, space, or person-time.

It is most plausible when:

- events are relatively rare
- counts are non-negative integers
- the observation window is clearly defined
- events occur independently within the window

Examples include:

- weekly case counts in a district
- number of admissions per day
- incident infections per person-time at risk

Poisson thinking is common in infectious-disease epidemiology, surveillance, and rate modeling. It connects naturally to incidence rates and later to Poisson regression.

One important warning: real public-health count data are often more variable than a pure Poisson model expects. When that happens, overdispersion becomes a concern and alternatives such as negative binomial models may be better.

### Section 6: Worked example - choosing a distribution
Imagine three variables from one health programme dataset:

1. Whether each of 500 participants completed treatment: yes/no
2. Age at enrollment in years
3. Number of new confirmed cases reported per district per month

The natural starting distributions are different:

- treatment completion out of 500 participants fits **binomial** logic
- age may be modeled with a **normal** approximation if the distribution is roughly symmetric
- monthly confirmed case counts often fit **Poisson** logic better than normal thinking, especially when counts are low

This example shows the practical point: different variables call for different distributional assumptions because they arise from different data-generating processes.

### Section 7: Sampling distributions and the central limit idea
One of the most important ideas in statistics is that the distribution of the **sample statistic** is not the same as the distribution of the **raw variable**.

For example, individual patient ages may be skewed. But if you repeatedly take samples and calculate the sample mean, the distribution of those sample means often becomes approximately normal as sample size grows. This is the intuition behind the **central limit theorem**.

The central limit idea matters because many confidence intervals and tests rely on approximate normality of estimators, not necessarily of the original variable itself.

This does not mean sample size fixes everything. With very small samples, strong skewness, or heavy tails, normal approximations can still be poor. But the idea explains why normal-based inference is so common.

### Section 8: Distribution choice and model validity
Distributional assumptions affect more than elegance. They affect:

- standard errors
- confidence interval width
- p-values
- fitted values
- interpretation of regression coefficients

For example, treating low count data as normally distributed may produce nonsensical predictions such as negative case counts. Treating a highly skewed biomarker as perfectly normal may underestimate uncertainty or obscure important structure.

The practical habit to build is to ask: what kind of process generated this variable, and does the proposed distribution match that process reasonably well?

### Section 9: Common beginner mistakes
Several mistakes recur often.

- Using the normal distribution for every numeric variable by default
- Forgetting that counts and proportions are bounded
- Confusing the distribution of the sample with the distribution of the sample mean
- Ignoring overdispersion in count data
- Treating distribution names as labels to memorize rather than models tied to a data-generating process

Good applied biostatistics is not about naming distributions from memory. It is about matching a mathematical model to a plausible epidemiologic process.

## Key takeaways
- Probability distributions describe how values are expected to vary under a given data-generating process.
- Binomial models are natural for fixed numbers of binary trials, normal models for many symmetric measurements and sampling summaries, and Poisson models for event counts over time or space.
- The distribution of a sample statistic is not the same as the distribution of the raw variable.
- The central limit idea helps explain why many estimators are approximately normal in large samples.
- Distributional assumptions affect interval estimation, hypothesis tests, and regression models, so they should be chosen thoughtfully.

## Self-check questions
1. When is the binomial distribution a reasonable model?
2. Why is the normal distribution useful even when the raw data are not perfectly normal?
3. What kind of outcome is the Poisson distribution designed for?
4. What is the difference between the distribution of a variable and the sampling distribution of its mean?
5. Why can treating count data as normally distributed be problematic?
6. What practical issue suggests that a Poisson model may be too simple for real data?

## Answer key
1. When there is a fixed number of independent trials, each with two outcomes and the same probability of success.
2. Because many estimators, especially sample means, are approximately normal in large samples even if the original variable is somewhat skewed.
3. Counts of events occurring over a defined amount of time, space, or person-time.
4. The first describes how individual observations vary; the second describes how the sample mean would vary across repeated samples.
5. Because normal models can fit poorly to non-negative integer counts and may imply impossible negative values.
6. Overdispersion, meaning the observed variability is greater than the Poisson assumption would expect.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy random variables](https://www.khanacademy.org/math/statistics-probability/random-variables-stats-library)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
