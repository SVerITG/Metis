# Data Collection and Flow

## Learning objectives
- Map surveillance data flow from point of detection to decision-maker.
- Identify where delays, data loss, duplication, and feedback failure commonly emerge.
- Explain why identifiers, governance rules, and reconciliation matter.
- Recognize that surveillance data flow is a design problem, not only an IT problem.

## Prerequisites
- What is surveillance.

## Content

### Section 1: Why data flow matters
Surveillance is only as strong as the path its data take from detection to decision. Cases may be recognized in communities, facilities, laboratories, or event-based channels, but unless those signals move reliably through the system, they cannot support action.

Data flow matters because every handoff creates opportunities for:

- delay
- duplication
- data loss
- inconsistent interpretation
- failure of feedback

This is why surveillance architecture should be designed deliberately rather than assumed to "just happen" through reporting forms.

### Section 2: Typical reporting chains
In many systems, data move through several levels:

- point of detection, such as community worker, clinic, or laboratory
- district or intermediate level
- provincial or regional level
- national programme
- sometimes international reporting layers

Each level may add value through aggregation, verification, analysis, or escalation. But each level can also introduce bottlenecks if roles are unclear or reporting standards differ.

### Section 3: Feedback is part of the flow
One of the most common weaknesses in surveillance systems is one-way data extraction. Facilities send data upward, but little useful information returns.

This damages:

- acceptability
- data quality
- motivation to report on time

Frontline reporters need feedback to know whether:

- reports were received
- thresholds were crossed
- data quality problems need correction
- their reporting resulted in action

Without feedback, reporting becomes a burden rather than a functioning part of a learning system.

### Section 4: Reconciliation across sources
Surveillance data often come from multiple streams:

- facility notifications
- laboratory confirmation
- case investigation records
- deaths or outcome registers
- digital alert systems

If these streams are not reconciled, the system can produce undercounts, overcounts, or contradictory signals. For example, laboratory-confirmed cases that never link back to the original facility notification may disappear from response planning or be counted twice.

This is why reconciliation is not an administrative detail. It is part of surveillance validity.

### Section 5: The role of identifiers and standards
Reliable data flow depends on stable identifiers and consistent metadata. Useful examples include:

- case IDs
- facility codes
- district or province codes
- specimen IDs
- dates with standard formats

Without standard identifiers, linking records across time and system levels becomes error-prone. This is especially important for case-based surveillance, laboratory integration, and post-elimination follow-up.

### Section 6: Worked example - lab and facility mismatch
Imagine a surveillance system in which a district hospital sends suspected cases to a reference laboratory. The laboratory confirms several cases, but the results do not reliably link back to the original facility reports because identifiers are inconsistent.

The consequences may include:

- delayed response
- duplicated counting
- missing case-based follow-up
- poor confidence in final tallies

This example shows how data flow problems can produce epidemiologic errors even when laboratory quality is good.

### Section 7: Governance and timeliness
Data flow is shaped by governance choices such as:

- who is authorized to edit or validate records
- who receives alerts
- what deadlines apply
- how often reconciliation occurs
- what triggers escalation

Timeliness is not only a property of software. It depends on roles, responsibilities, escalation rules, staffing, and communication culture.

That is why surveillance design should specify not only the data fields, but also the operational path those data take.

### Section 8: Common failure points
Several failure points recur often.

- delayed facility submission
- weak internet or transport infrastructure
- missing zero reports
- inconsistent coding across levels
- no reconciliation between lab and case databases
- dashboards that display data without usable feedback loops

The system can still look technically modern and fail operationally if these points are not addressed.

## Key takeaways
- Data flow is a core part of surveillance design because action depends on reliable movement of information through the system.
- Each reporting step can introduce delay, duplication, or data loss.
- Feedback to frontline reporters is essential for acceptability and quality.
- Stable identifiers and reconciliation across data streams are central to valid surveillance counts.
- Governance decisions shape timeliness and completeness as much as technology does.

## Self-check questions
1. Where do reporting delays commonly emerge in a surveillance system?
2. Why does lack of feedback damage acceptability?
3. What is the value of standard identifiers?
4. Why is reconciliation between laboratory and facility data important?
5. Why is data flow a design problem rather than only an IT problem?
6. What can happen if confirmed cases cannot be linked back to their original reports?

## Answer key
1. At any handoff point, including detection, reporting, validation, aggregation, laboratory linkage, and escalation.
2. Because reporters do not see whether their work was received, corrected, or used, which reduces motivation and data discipline.
3. They allow records to be linked reliably across levels, time points, and data systems.
4. Because without it the system may undercount, double-count, or fail to trigger the correct response pathway.
5. Because roles, incentives, governance rules, deadlines, and communication processes determine whether information moves effectively.
6. Delayed response, duplicate counting, failed follow-up, and poor confidence in the surveillance outputs.

## Further reading
- [CDC surveillance evaluation guidelines](https://www.cdc.gov/mmwr/preview/mmwrhtml/rr5013a1.htm)
- [WHO AFRO IDSR resources](https://www.afro.who.int/health-topics/integrated-disease-surveillance-and-response)
- [WHO public health surveillance overview](https://www.who.int/health-topics/public-health-surveillance)

## Links to Metis library
- `06_library/methods/data-management.md`
- `06_library/methods/surveillance-systems.md`
- `06_library/methods/diagnostic-test-evaluation.md`
