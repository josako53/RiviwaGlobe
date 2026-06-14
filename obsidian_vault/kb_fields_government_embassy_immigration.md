---
tags: [industry-kb, field-collection, feedback-fields]
---
# Government Embassy / Immigration — Feedback Collection Fields & Standards

## Industry Identifiers

Embassy, consulate, high commission, visa, immigration, work permit, residence permit, passport, apostille, notarization, diplomatic services, refugee services, UNHCR, travel advisory, visa on arrival, transit visa, EAC passport, biometric enrollment, immigration officer, consular officer, visa application center (VAC), entry clearance, deportation, detention, overstay, visa refusal, Tanzania immigration department, Namanga border, Holili border, JNIA immigration, Julius Nyerere International Airport, diplomatic mission, letter of invitation, temporary residence permit, multiple entry visa, student visa, business visa, tourist visa, EAC integration, stateless person, asylum seeker, refugee status determination, RSD, resettlement, family reunification, naturalization, apostille, authenticated document, certificate of origin, UNHCR registration, camp management, border crossing, immigration fine, work permit class A-G, kibali cha kazi, ruhusa ya makazi, pasi ya kusafiri, uhamiaji, balozi, ubalozi, consulate general

## Why Industry-Specific Fields Matter

Embassy and immigration complaints require the exact visa or permit type, application reference number, and travel urgency date because a delay affecting a person traveling for a medical emergency or a family with a 48-hour travel window demands a fundamentally different response urgency than a general processing complaint. Without these fields the complaint cannot be triaged, urgency cannot be assessed, and the appropriate consular authority cannot be identified.

## Source Standards

- EU Ombudsman Complaint Form and Guide (ombudsman.europa.eu) — structured fields for maladministration including consular and Schengen visa processing
- Danish Embassy Visa Complaint Process (um.dk) — operational fields including urgency framing and prior contact requirement
- World Bank ESF ESS10 GRM Register — project-level standards applicable to World Bank-funded refugee and migration programs
- UNHCR Feedback, Complaints and Response Mechanism (FCRM) Minimum Standards (data.unhcr.org doc 79144) — refugee-specific intake fields
- WFP-UNHCR Joint Feedback Mechanism SOP Template (April 2022) — mandatory fields for humanitarian feedback including refugee and IDP contexts
- IASC AAP Commitments 2017 (reliefweb.int) — accountability standards for protection complaints
- Sphere Handbook 2018 CHS Commitment 5 — confidentiality and complaint mechanism standards for humanitarian contexts
- Tanzania Immigration Department regulations — Ministry of Home Affairs / work permit and residence permit classes
- Transparency International Complaint Mechanisms Reference Guide (2016) — corruption and misconduct field standards

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL embassy/immigration complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| institution_name | Jina la Taasisi / Ubalozi | Yes | Identifies the specific embassy, consulate, or immigration office — routes complaint to the correct authority |
| institution_country | Nchi ya Taasisi | Yes | Foreign embassy of which country, or Tanzania immigration — determines jurisdiction |
| complaint_service_category | Aina ya Huduma Inayolalamikiwa | Yes | Visa / Work Permit / Residence Permit / Passport / Apostille / Border Crossing / Refugee Services / Other — determines sub-fields |
| visa_or_permit_type | Aina ya Visa / Kibali | Yes | Tourist / Business / Student / Work / Transit / Residence / Multiple Entry / Diplomatic / Asylum / Dependent / EAC — determines applicable regulations and processing timeline |
| application_reference_number | Namba ya Maombi / Kumbukumbu | Yes | Required to locate the specific case in the embassy or immigration system |
| date_application_submitted | Tarehe ya Kuwasilisha Maombi | Yes | Establishes how long the application has been pending and whether the SLA has been breached |
| travel_urgency | Uharaka wa Safari | Yes | Yes/No — if Yes, collect travel_urgency_date immediately |
| travel_urgency_date | Tarehe ya Uharaka | Conditional | Required when travel_urgency = Yes; determines whether emergency processing is warranted |
| urgency_reason | Sababu ya Uharaka | Conditional | Medical emergency / Funeral / Court hearing / Business deadline / Other — affects escalation priority |
| issue_type | Aina ya Tatizo | Yes | Processing delay / Unjustified refusal / Incorrect visa issued / Document lost / Bribe demand / Rude conduct / System failure / Appointment not honored / Other |
| prior_contact_with_institution | Mawasiliano ya Awali na Taasisi | Yes | Yes/No — EU Ombudsman and Danish embassy framework require complainant to have already contacted the institution; this determines whether complaint is at the right stage |
| prior_contact_description | Maelezo ya Mawasiliano ya Awali | Conditional | Required when prior_contact_with_institution = Yes; summary of what was communicated and what response was received |
| nationality_of_applicant | Utaifa wa Mwombaji | Yes | Determines which bilateral agreements, visa regimes, and EAC provisions apply |
| legal_representative | Mwakilishi wa Kisheria | Conditional | Yes/No; name and contact — required if an immigration lawyer or authorized representative is filing |
| desired_outcome | Matokeo Yanayotarajiwa | Yes | Visa approval / Expedited processing / Reason for refusal / Refund of fees / Correction of error / Apology / Compensation for losses / Other |
| evidence_available | Ushahidi Unaopatikana | Recommended | Checkbox: Refusal letter / Fee receipt / Prior correspondence with embassy / Booking confirmation / Medical certificate / Other |
| complainant_full_name | Jina Kamili | Yes | Required by EU Ombudsman and Tanzania immigration standards for all formal complaints |
| complainant_nationality | Utaifa wa Mlalamikaji | Yes | Determines which consular protections and bilateral frameworks apply |
| complainant_email | Barua Pepe | Yes | Primary contact for written decisions and follow-up |
| complainant_phone | Namba ya Simu | Yes | For urgent contact when travel date is approaching |
| complainant_postal_address | Anwani ya Barua | Conditional | Required by EU Ombudsman for formal correspondence |
| anonymous_submission | Wasilisho la Siri | Yes | Yes/No — anonymous complaints cannot receive direct response but are recorded for institutional pattern analysis |
| consent_to_data_use | Idhini ya Kutumia Taarifa | Yes | Required for processing, referral, and cross-agency coordination |

### Conditional Fields (collect based on issue type)

**If issue_type = Unjustified Refusal:**
- refusal_reason_given — what reason was provided in the refusal letter, if any
- refusal_letter_date — date of the refusal letter
- reapplication_plan — does the applicant intend to reapply; if so, what will change
- losses_incurred — financial losses from the refusal (non-refundable flights/hotel — amount in TZS or USD)

**If issue_type = Incorrect Visa Issued (wrong dates, wrong type, wrong name):**
- error_description — exactly what is incorrect on the issued visa
- correct_information_should_be — what it should say
- date_passport_returned — when passport was returned with the incorrect visa
- urgency_to_correct — Yes/No; travel date approaching

**If issue_type = Bribe Demand / Corruption:**
- corrupt_official_description — name, badge number, or physical description
- amount_demanded_or_paid — amount in TZS or USD
- location_of_incident — specific counter, border post, or office location
- witnesses_present — Yes/No; if yes, names/contacts
- evidence_of_payment — Yes/No; receipt or mobile money transaction reference

**If issue_type = Border Crossing Incident (Detention / Abuse / Confiscation):**
- border_crossing_name — Namanga / JNIA / Holili / Sirari / Tunduma / Kasumulu / Other
- date_and_time_of_incident — date and approximate time
- detention_duration — how long detained, if applicable
- items_confiscated — Yes/No; description of what was taken
- written_notice_provided — Yes/No — legal requirement; if No, this is a rights violation
- physical_harm — Yes/No; description if yes

**If complaint_service_category = Refugee Services:**
- unhcr_registration_number — UNHCR case number or group case number
- refugee_camp_or_settlement — name of camp or settlement
- protection_concern — Yes/No; description if yes (safety, GBV, family separation)
- consent_to_referral — Yes/No — required before referring to UNHCR or partner agencies
- number_of_family_members_affected — for household-level complaints

### Issue Type Classification

| Code | Issue Type | Legal/Regulatory Context |
|------|------------|--------------------------|
| EMB-01 | Processing delay — application pending beyond published SLA | Tanzania Immigration: work permit 60 days; EU: Schengen visa 15 working days |
| EMB-02 | Unjustified refusal — application denied without adequate reason | EU Ombudsman jurisdiction; right to know reason required |
| EMB-03 | Incorrect visa / permit issued — wrong type, dates, name, or duration | Document correction; may require emergency processing |
| EMB-04 | Document lost or damaged — originals submitted and not returned in good condition | Institutional liability; replacement of originals at institution's cost |
| EMB-05 | Bribe or corrupt solicitation — unofficial payment demanded for service | PCCB referral; anti-corruption protocol |
| EMB-06 | Abusive, discriminatory, or disrespectful officer conduct | Staff conduct investigation; HR action |
| EMB-07 | System or appointment failure — portal down, appointments unavailable, or misinformation | Technical escalation; emergency alternative processing |
| EMB-08 | Unauthorized detention or rights violation at border — no written notice, excessive force | Emergency legal escalation; notify Legal Aid; UNHCR if refugee involved |
| EMB-09 | Financial loss from institutional error — non-refundable costs caused by embassy or immigration mistake | Compensation claim; legal review |
| EMB-10 | Refugee or asylum case stalled — RSD, resettlement, or protection case with no movement | UNHCR escalation; protection flagging |
| EMB-11 | Fee paid but service not delivered — payment confirmed but no acknowledgment or processing | Finance reconciliation request |
| EMB-12 | Information contradiction — embassy website, officer, and email providing different requirements | Formal clarification request to head of section |
| EMB-13 | Other | General consular complaint routing |

### Resolution Standards for This Industry

Per EU Ombudsman, Danish Embassy visa complaint framework, and Tanzania Immigration Department:
- **Acknowledgment**: Within 3 working days (EU standard); 5 working days (Tanzania immigration)
- **Schengen/EU visa decisions**: Maximum 15 working days (Schengen Code Art. 23); up to 45 in exceptional cases
- **Tanzania work permit**: 60 working days from complete application submission
- **Emergency / urgent travel cases**: Same-day or next-business-day response required when travel_urgency_date is within 5 days
- **Corruption complaints**: Referred to relevant anti-corruption body within 48 hours
- **Refugee protection concerns** (ongoing GBV, trafficking, security threat): Response within 24 hours per WFP-UNHCR SOP (Highly Sensitive tier)
- **General refugee/asylum inquiries**: 5 working days per WFP-UNHCR SOP
- EU Ombudsman rule: complaint must be filed within **2 years** of becoming aware of the facts; prior contact with institution required

### Escalation Triggers (field values requiring immediate escalation)

- `travel_urgency = Yes` AND `travel_urgency_date` within 5 days → Priority-1; attempt same-day contact with institution
- `issue_type = EMB-08` (detention / rights violation) → Emergency legal escalation; notify Tanzania Legal Aid Authority or relevant consular protection body within 24 hours
- `protection_concern = Yes` (refugee) → Refer to UNHCR Protection Officer within 24 hours; do not delay for documentation
- `issue_type = EMB-05` (Bribe demand at border) + `location_of_incident` (border post) → refer to PCCB/TAKUKURU and relevant border authority
- Person in immigration detention claiming unlawful basis → contact UNHCR or Legal Aid immediately regardless of documentation status
- Asylum seeker facing imminent deportation to country of feared persecution → activate protection emergency protocol; UNHCR + legal counsel
- Child separated from family at border → emergency child protection escalation; UNICEF and Ministry of Social Welfare
- `physical_harm = Yes` during border crossing → report to police and human rights commission
- `document_type = Passport` AND lost by institution → urgent — traveler may be stranded; expedite replacement document process

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| target_institution | Taasisi Inayolengwa | Yes | Specific embassy, consulate, or immigration office the suggestion is directed to |
| process_to_improve | Mchakato wa Kuboresha | Yes | Visa booking / Document submission / Status tracking / Border processing / Communication / Refugee registration / Other |
| improvement_category | Aina ya Uboreshaji | Yes | Digital services / Processing efficiency / Staff training / Communication transparency / Physical access / Anti-corruption / Other |
| affected_applicant_group | Kundi la Waombaji Linaoathiriwa | Recommended | All applicants / Students / Workers / Refugees / Business travelers / EAC citizens / Elderly / PWD |
| proposed_change_description | Maelezo ya Mabadiliko Yanayopendekezwa | Yes | Full description of the improvement |
| expected_benefit | Faida Inayotarajiwa | Recommended | What would improve and for how many people |
| submitter_contact | Mawasiliano ya Mtoa Mapendekezo | Optional | For follow-up |

### Industry-Specific Improvement Categories

- **Online status tracking**: Application tracking portal with SMS/WhatsApp notifications at each stage
- **Document checklist accuracy**: Published, up-to-date checklists per visa/permit type to prevent wasted fees
- **Appointment systems**: Electronic booking with SMS confirmation; multiple enrollment centers outside capital
- **Processing time transparency**: Published and enforced SLAs per category; proactive delay notifications
- **Anti-corruption at border**: Visible complaint mechanism at border crossing points; anonymous reporting channel
- **Language accessibility**: Swahili FAQ sections; multilingual support for refugee communities
- **Emergency fast-track**: Documented emergency processing for medical, bereavement, and humanitarian travel
- **Digital fee payment**: Online payment with instant receipt; payment reconciliation for failed transactions

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution | Taasisi | Yes | Routes inquiry to the correct consular or immigration office |
| visa_or_permit_type | Aina ya Visa / Kibali | Yes | Determines which rules and fee schedule apply |
| specific_question | Swali Maalum | Yes | The exact information being requested |
| application_reference_number | Namba ya Maombi | Conditional | Required for status inquiries on specific applications |
| date_application_submitted | Tarehe ya Wasilisho | Conditional | Required for status inquiries |
| nationality_of_applicant | Utaifa wa Mwombaji | Yes | Determines bilateral visa regime and applicable requirements |
| travel_date_approaching | Safari Inakaribia? | Recommended | Yes/No — enables urgency triage |
| submitter_phone | Namba ya Simu | Yes | For urgent response if travel date is near |
| submitter_email | Barua Pepe | Yes | For written response |
| preferred_response_channel | Njia Inayopendelewa ya Majibu | Yes | SMS / WhatsApp / Email / Phone call |

### Common Inquiry Types & Required Data Per Type

**Visa requirements inquiry:**
- institution + visa_or_permit_type + nationality_of_applicant + travel_date_approaching — provide requirements information directly if in KB

**Application status inquiry:**
- institution + visa_or_permit_type + application_reference_number + date_application_submitted + submitter_full_name

**Work / residence permit process inquiry:**
- institution + visa_or_permit_type + nationality_of_applicant + employment_sector (if work permit) + specific_question

**Refugee / asylum process inquiry:**
- unhcr_registration_number (if already registered) + specific_question — route to UNHCR information desk

**Fee inquiry:**
- institution + visa_or_permit_type + specific_question — provide published fee information; flag if website fee differs from what officer quoted

**Refusal appeal inquiry:**
- institution + visa_or_permit_type + refusal_date + specific_question — advise on reapplication vs. appeal process based on institution type

**Border crossing entry requirements:**
- border_crossing_name + nationality_of_applicant + specific_question (health requirements, prohibited items, hours)

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution_being_commended | Taasisi Inayopongezwa | Yes | Routes compliment to the correct embassy, consulate, or immigration office |
| specific_officer_name_or_section | Jina la Afisa au Kitengo | Recommended | Enables individual or team recognition — valuable for institutions with high staff turnover |
| service_or_interaction | Huduma / Mwingiliano Uliofanya Vizuri | Yes | What specifically worked well — used for internal recognition and service benchmarking |
| date_of_positive_experience | Tarehe ya Uzoefu Mzuri | Recommended | Helps correlate with specific staff, process changes, or system upgrades |
| what_made_it_exceptional | Kilichoifanya Kuwa Bora | Recommended | Speed / Accuracy / Staff attitude / System worked smoothly / No corruption requested / Proactive communication / Sensitive handling of refugee case |
| submitter_name | Jina la Mtoa Pongezi | Optional | For acknowledgment |
| submitter_nationality | Utaifa | Optional | Helps institution understand which applicant groups have positive experiences |

---

## AI Conversation Guidance for This Industry

- **Identify travel urgency before anything else.** For all embassy and immigration complaints, the first clarifying question after understanding the issue type should be: "Je, una tarehe ya safari inayokaribia au hali ya dharura?" (Do you have an approaching travel date or emergency?) A person with a flight in 3 days needs a completely different response path than someone managing a months-old permit delay. Collect `travel_urgency_date` immediately if yes.
- **Always ask for the application reference number.** Nearly every embassy and immigration interaction generates a reference number, receipt number, or case number. This field unlocks everything. Ask: "Je, ulikuwa na namba yoyote ya maombi au risiti ulipewa na ubalozi au ofisi ya uhamiaji?" If they don't have it, ask for the date submitted and the type of document applied for — these two fields together are sufficient for most lookups.
- **Confirm whether prior contact with the institution has been made.** Both the EU Ombudsman and Danish embassy complaint frameworks require that the applicant has already attempted to resolve the issue with the institution before a formal complaint is accepted. Ask: "Je, umeshajaribu kuwasiliana moja kwa moja na ubalozi au ofisi ya uhamiaji kuhusu tatizo hili? Ukapata jibu gani?" This also surfaces whether the complaint is at escalation stage.
- **Handle refugee and protection cases with maximum discretion.** When keywords like asylum, refugee, camp, RSD, UNHCR registration, or deportation appear, do not collect more personal data than necessary. Ask for consent before any referral: "Je, unakubali taarifa yako ipelekwe kwa UNHCR au msaada wa kisheria?" Do not push for identity details if the person expresses fear of retaliation.
- **For border crossing incidents, collect location and time.** Border posts (Namanga, Holili, JNIA) have shift records and camera footage that can be used in investigations. The combination of `border_crossing_name` + `date_and_time_of_incident` + `officer_description` is the minimum needed for any meaningful investigation. Ask specifically: "Mpaka ulikuwa gani? Na ilikuwa saa ngapi takriban?"
- **Never ask about visa refusal reasons in a way that implies the citizen was at fault.** Approach as: "Je, ubalozi ulitoa sababu yoyote kwa kukataa maombi yako?" — neutral and factual. The refusal letter, if they have it, is the most important evidence to note.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase |
|----------------------|----------------|
| travel_urgency | "Je, una tarehe ya safari inayokaribia — safari yako ipo lini?" |
| visa_or_permit_type | "Unalalamika kuhusu aina gani ya visa au kibali — kama vile visa ya utalii, kibali cha kazi, au ruhusa ya makazi?" |
| application_reference_number | "Je, una namba ya maombi au kumbukumbu yoyote kutoka ubalozi au ofisi ya uhamiaji?" |
| institution_name | "Ni ubalozi gani au ofisi gani ya uhamiaji unaozungumza nao — na ni nchi gani?" |
| issue_type (bribe) | "Je, mtu yeyote katika ofisi hiyo alikuomba malipo ya ziada — nje ya ada rasmi — ili kukusaidia au kuharakisha mchakato?" |
| prior_contact | "Je, umeshajaribu kuwasiliana na ubalozi au ofisi ya uhamiaji kutatua tatizo hili? Walikusema nini?" |
| losses_incurred | "Je, tatizo hili lilikufanya upoteze pesa — kama tiketi za ndege au malipo ya hoteli ambayo hayarudishwi?" |
| refugee protection_concern | "Je, kuna wasiwasi wowote wa usalama wako au wa familia yako unaohusiana na hali hii?" |
| consent_to_referral | "Je, unakubali taarifa yako ipelekwe kwa UNHCR au msaada wa kisheria ili kupata msaada zaidi?" |
| border incident time | "Mpaka ulikuwa gani hasa? Na ilikuwa saa ngapi na tarehe gani?" |
| nationality | "Una utaifa gani — hii itasaidia kuelewa sheria zinazotumika kwa hali yako?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| travel_urgency = Yes | travel_urgency_date within 5 days | Priority-1; attempt same-day contact with institution; escalate to senior consular officer |
| issue_type | EMB-08 (Detention / Rights Violation) | Emergency — contact Tanzania Legal Aid Authority or UNHCR within 24 hours |
| protection_concern | Yes (refugee context) | Immediate UNHCR referral within 24 hours; document with sensitivity classification |
| bribe_or_corruption_demand | Yes (border or embassy) | Refer to PCCB/TAKUKURU within 48 hours; record officer description and location |
| issue_type | EMB-02 (Unjustified Refusal) + EU institution | Route to EU Ombudsman complaint pathway; verify prior contact was made |
| physical_harm | Yes (border crossing) | Report to Police; refer to Tanzania Human Rights Commission; notify UNHCR if refugee |
| document_lost | Passport or original certificate lost by institution | Urgent — institution required to issue emergency travel document; escalate to head of section |
| number_of_family_members_affected | Multiple (refugee household) | Treat as household case; assign single case worker; avoid multiple separate case numbers |
| issue_type | EMB-10 (Refugee case stalled 12+ months) | Escalate to UNHCR Senior Protection Officer; flag for review |
| visa_or_permit_type | Asylum / Refugee Status | Assign highest sensitivity level; restrict data access; apply anonymization if requested |
| prior_contact | No | Advise citizen to contact institution directly first; provide contact details; set reminder for 10 days |
| losses_incurred | Above TZS 500,000 | Document for potential compensation claim; advise legal review |

---

*Framework sources: EU Ombudsman Guide to Complaints (ombudsman.europa.eu/pdf/en/11469); Danish Embassy Visa Complaint Process (um.dk); WFP-UNHCR Joint Feedback Mechanism SOP Template (April 2022); UNHCR FCRM Minimum Standards (data.unhcr.org doc 79144); IASC AAP Commitments 2017 (reliefweb.int); Sphere Handbook 2018 CHS Commitment 5; Transparency International Complaint Mechanisms Reference Guide (2016); Tanzania Immigration Department / Ministry of Home Affairs regulations.*
