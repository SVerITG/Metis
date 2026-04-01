# Indicator-Based vs Event-Based Surveillance

## Learning objectives
- Distinguish structured indicator streams from event-based signal detection.
- Explain how indicator-based and event-based systems complement one another.
- Recognize why event-based surveillance requires triage and verification discipline.
- Understand why robust public-health intelligence usually needs both stability and agility.

## Prerequisites
- Types of surveillance.

## Content

### Section 1: Two different information streams
Indicator-based surveillance and event-based surveillance are often discussed together because they solve different parts of the same problem.

**Indicator-based surveillance (IBS)** uses structured data collected through predefined channels such as routine reports, case notifications, laboratory results, or sentinel-site summaries.

**Event-based surveillance (EBS)** uses unstructured or semi-structured signals such as media reports, rumors, hotline alerts, community reports, or open-source intelligence.

The difference is not only about data format. It is also about how the information is generated, verified, and used.

### Section 2: What indicator-based surveillance does well
Indicator-based systems are strong because they are:

- structured
- comparable over time
- relatively easy to summarize
- suitable for trend monitoring and thresholds

Examples include:

- weekly notifiable disease counts
- laboratory-confirmed influenza reports
- sentinel surveillance indicators
- routine zero reporting from facilities

IBS is the backbone of most routine surveillance because it creates a stable baseline. It supports routine monitoring, burden estimation, and threshold-based alerting. But it may miss events that occur outside formal reporting channels or before the reporting cycle closes.

### Section 3: What event-based surveillance does well
Event-based systems are designed for sensitivity and speed. They are meant to detect possible threats before structured reporting is complete or sometimes before cases enter the formal health system at all.

Signals may come from:

- community rumor networks
- hotline alerts
- social media monitoring
- media scanning
- clinician concern
- open-source intelligence platforms such as EIOS

This makes EBS useful for early warning, especially for unusual, unexpected, or rapidly evolving events. But it also creates a major challenge: many signals are noisy, incomplete, duplicated, or false.

### Section 4: Why verification is central in EBS
Because event-based surveillance values sensitivity, it naturally produces many weak signals. A rumor, headline, or social-media post is not the same as a verified event.

That is why EBS requires a structured process of:

- detection
- triage
- verification
- risk assessment
- response

Without verification discipline, EBS can overwhelm staff with noise or generate false alarms. With good verification, it can detect meaningful events earlier than routine systems.

### Section 5: Worked example - fever cluster versus routine counts
Imagine a district usually receives weekly malaria counts through routine facility reports. Those counts are useful for monitoring seasonal patterns and identifying sustained increases.

Now suppose a community health worker reports an unusual cluster of severe fever cases in a remote area before the weekly reporting cycle is complete. That alert is event-based.

A good surveillance system uses both:

- IBS to maintain stable baseline information
- EBS to detect unusual events quickly

The event-based signal may trigger rapid verification while the indicator-based stream later helps contextualize whether the signal reflects a broader pattern.

### Section 6: Complementarity, not competition
IBS and EBS should not be framed as rivals.

IBS provides:

- structure
- comparability
- baseline trends
- regular reporting discipline

EBS provides:

- speed
- agility
- sensitivity to unusual events
- visibility into events outside routine reporting systems

Together, they create a more complete early-warning and response architecture than either one alone.

### Section 7: Common mistakes
Several mistakes recur often.

- treating unverified event signals as confirmed cases
- assuming structured data always arrive soon enough for early warning
- building EBS without enough staff time for triage and verification
- expecting IBS alone to detect unusual events outside health-system channels
- describing one system as modern and the other as obsolete

The practical lesson is that good surveillance balances signal sensitivity with verification discipline.

## Key takeaways
- Indicator-based surveillance uses structured routine data; event-based surveillance uses unstructured or rapidly emerging signals.
- IBS is strong for comparability and trend monitoring, while EBS is strong for early warning and unusual-event detection.
- Event-based surveillance requires triage and verification because many signals are noisy or incomplete.
- The two systems support each other rather than competing.
- Strong public-health intelligence usually combines stable routine reporting with agile signal detection.

## Self-check questions
1. What makes event-based surveillance "noisy"?
2. Why are indicator-based systems still essential even when EBS exists?
3. What is the role of verification in event-based surveillance?
4. Why can IBS miss important emerging events?
5. How can IBS and EBS support each other operationally?
6. Why is it risky to treat an event-based signal as a confirmed case immediately?

## Answer key
1. Because it draws on unstructured and early signals such as rumors or media reports that may be incomplete, duplicated, or false.
2. Because they provide structured, comparable baseline data for trend monitoring, thresholds, and routine burden assessment.
3. To determine whether a signal reflects a real event that merits risk assessment and response.
4. Because routine reporting may be delayed and may not capture events occurring outside formal detection channels.
5. EBS can trigger early verification, while IBS can later provide baseline context and ongoing quantitative monitoring.
6. Because many event-based signals are preliminary and may not represent verified cases or even true events.

## Further reading
- [WHO public health intelligence page](https://www.who.int/teams/emergency-intelligence/public-health-intelligence)
- [OpenWHO course catalog](https://openwho.org/courses)
- [WHO AFRO IDSR resources](https://www.afro.who.int/health-topics/integrated-disease-surveillance-and-response)

## Links to Metis library
- `06_library/methods/surveillance-systems.md`
- `06_library/concepts/digital-health-epi.md`
- `06_library/methods/outbreak-investigation.md`
