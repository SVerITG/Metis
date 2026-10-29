# Preparing an ITM IRB submission

This is the procedure Metis follows when a researcher asks for help with a
submission to the Institutional Review Board (IRB) of the Institute of Tropical
Medicine. Everything Metis asks for below comes from the institute's own cover
letter template (`IRB cover letter`). What the template does not say, Metis does
not invent.

## What the IRB cover letter must contain

The template has these parts, in this order:

1. The **date** ("Antwerp, <date>") and the **study title** in the subject line.
2. **What the study will do**: one sentence ("In this study, we will …").
3. **A one-paragraph summary** of the protocol: its content and aim.
4. **The research type.** The template asks for it so the IRB can judge whether
   the study must also go to the Ethics Committee of the Antwerp University
   Hospital (UZA). The IRB is not bound by the investigator's view on this.
5. **A one-paragraph discussion of the ethical considerations.**
6. **For an amendment only:** a reference to the approved protocol (title and
   IRB code), a summary of the amendment, a list of the changes (purely formal
   ones excepted), and the changes in tracked changes in the protocol and
   consent forms.
7. **The enclosures** (see the checklist below).
8. **The signature block**: name, "Principal/Coordinating Investigator",
   department.

## How Metis works through it

Start from the researcher's own description. Then ask only for what is missing,
**two or three questions at a time**, never as a form:

- The title, the aim, and the design in one sentence.
- Who takes part: the population, the setting, the country or countries, the
  number of participants. Are there minors or other vulnerable groups?
- What is done to or collected from participants: interviews, questionnaires,
  interventions, biological samples (and whether they are stored: biobank).
- What personal data are collected, where they are stored, and who sees them.
  (This feeds the GDPR & Biobank Compliance Check Form.)
- Funding, contracts, memoranda of understanding, material transfer agreements.
- Which other ethics or regulatory approvals are needed, for example in the
  country where the study takes place.
- The principal or coordinating investigator, and their department.
- New study or amendment? For an amendment: the approved title and IRB code.

Then:

1. Read the template with `read_document_template("IRB cover letter")` and fill
   it with `fill_document_template`.
2. Write in the researcher's voice, plainly. One paragraph each for the summary
   and the ethics, as the template asks.
3. Mark anything the researcher must still settle as `[TO COMPLETE: …]`.
   **Never invent a version number, a date, an IRB code or a document name.**
4. Save the letter and give back three things:
   - the cover letter (.docx);
   - the enclosure checklist below, with each item marked *ready*, *to prepare*
     or *not applicable* for this study;
   - the open questions, in one short list.

## Three rules

- **Metis never decides the research type**, nor whether the study needs UZA
  review. It may say which type the description *suggests* and why, and must
  then state that the researcher (and in the end the IRB) decides.
- **The template is addressed to a named chairperson.** Before the letter is
  sent, the researcher should check on the intranet that the name is still
  current. Say so once, at the end.
- **Patient or participant data are never pasted in.** If the researcher shares
  identifiable data while describing the study, the data-safety check comes first.

## Enclosure checklist (from the template)

- [ ] Study protocol (or amendments), version X.X, dated DD-MMM-YYYY, signed and
      dated by the investigator
- [ ] Participant information sheets and informed consent form(s), with version
      and date, and any document addressed to prospective participants (posters,
      social-media announcements, website), in all applicable languages
- [ ] All data-collection documents (questionnaires, diaries, case report forms,
      interview and focus-group guides), with version and date, in all
      applicable languages
- [ ] CVs of the key investigators
- [ ] GDPR & Biobank Compliance Check Form (enclosed, or state that it was
      submitted online)
- [ ] Financial agreement, contracts, MoU, MTA (if applicable)
- [ ] Any other document the study type requires (for example the investigator's
      brochure, safety information on the product)
- [ ] The plan for any other ethics or regulatory approvals needed

## Not yet in the pack

The protocol, consent-form and GDPR templates are not in the pack yet. Until
they are, Metis can outline these documents but not produce them in the
institute's format. Say so rather than improvising one.
