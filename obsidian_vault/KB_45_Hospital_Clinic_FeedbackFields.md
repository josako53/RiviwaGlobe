---
tags: [industry-kb, field-standards, feedback-fields, healthcare]
---
# Hospital / Clinic — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: hospitali, kliniki, zahanati, dispensary, daktari, nurse, mhudhuria, muuguzi, dawa, medicine, upasuaji, surgery, ward, wodi, ICU, OPD, outpatient, inpatient, mgonjwa, patient, appointment, miadi, X-ray, lab test, maabara, blood test, kipimo cha damu, ultrasound, scan, maternity, wazazi, delivery, kujifungua, emergency, dharura, ambulance, gari la wagonjwa, MSD, NHIF, bima ya afya, copayment, discharge, kutolewa hospitalini, referral, rufaa, prescription, dawa ya daktari, pharmacy, famasi, specialist, daktari bingwa, MRI, CT scan, theatre, chumba cha upasuaji, birth certificate, cheti cha kuzaliwa, death certificate, cheti cha kifo, mortuary, chumba cha maiti, MOH, MOHCDGEC, TFDA, medical negligence, uzembe wa kimatibabu, waiting time, muda wa kusubiri, queue, foleni, hospital bed, kitanda cha hospitali

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a clinical negligence complaint (requiring patient ID, admission date, treating clinician, procedure), a billing dispute (requiring NHIF number, invoice reference, amount), and a drug shortage complaint (requiring medicine name, ward, date reported) — all of which have different regulatory escalation paths under the Ministry of Health, TFDA, and NHIF. Without healthcare-specific fields, the AI cannot route, prioritize, or generate actionable incident reports compliant with Tanzania's Health Sector Complaints Management Framework.

## Source Standards

- Tanzania Health Policy 2007 and Tanzania Health Sector Strategic Plan V (2021–2026)
- Ministry of Health, Community Development, Gender, Elderly and Children (MOHCDGEC) Patient Charter 2019
- Tanzania Food and Drug Authority (TFDA) Act, Cap. 219 — adverse drug reaction reporting
- National Health Insurance Fund (NHIF) Act, Cap. 395 and NHIF Regulations 2015
- ISO 10002:2018 — Quality management: guidelines for complaints handling
- WHO Patient Safety Curriculum Guide (2011) — incident classification and reporting
- WHO Conceptual Framework for the International Classification for Patient Safety (ICPS) 2009
- Joint Commission International (JCI) Accreditation Standards for Hospitals, 7th Edition — QPS standards
- NHS Complaints Regulations 2009 (reference standard for complaint field design)
- East African Community Health Sector Protocol — cross-border patient rights

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required by MOHCDGEC Patient Charter; needed to open formal incident report |
| complainant_relationship_to_patient | Uhusiano na mgonjwa | Yes | Complainant may be patient, next of kin, or guardian; affects legal standing and data sharing |
| patient_full_name | Jina kamili la mgonjwa | Yes | Required for clinical record lookup; WHO ICPS requires patient identification in incident reports |
| patient_id_or_file_number | Nambari ya mgonjwa / faili | Yes | Primary clinical identifier; without it, staff cannot locate the patient record |
| patient_date_of_birth | Tarehe ya kuzaliwa ya mgonjwa | Recommended | Age affects clinical risk assessment and complaint severity weighting |
| facility_name | Jina la hospitali / kliniki | Yes | Determines complaint routing and applicable regulatory body (MOHCDGEC, NHIF, TFDA) |
| department_or_ward | Idara / Wodi | Yes | Routes complaint to correct departmental head; enables service-level analysis |
| date_of_incident | Tarehe ya tukio | Yes | Required for complaint limitation period and medical record correlation |
| treating_clinician_name | Jina la daktari / muuguzi aliyehusika | Recommended | Required for clinical review; WHO ICPS incident report field |
| issue_type | Aina ya tatizo | Yes | MOHCDGEC complaint taxonomy drives routing and SLA classification |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2; WHO ICPS requires narrative of what happened |
| nhif_membership_number | Nambari ya NHIF | Conditional | Required for billing complaints involving insurance; NHIF Act requires member identification |
| desired_outcome | Matokeo unayotaka | Yes | ISO 10002:2018 clause 8.3; shapes resolution approach |
| preferred_contact_method | Njia ya mawasiliano unayoipendelea | Yes | Options: SMS / Simu / WhatsApp / Barua pepe |
| consent_to_share_with_clinician | Ridhaa ya kushiriki taarifa na daktari | Yes | Required before sharing complaint details with clinical staff under data protection principles |

### Conditional Fields (collect based on issue type)

**If issue_type = Negligence / Clinical Error / Wrong Treatment:**
Also collect:
- `procedure_or_treatment_involved` — Upasuaji / matibabu yaliyohusika: For clinical review board
- `outcome_to_patient` — Athari kwa mgonjwa: e.g., ulemavu, kifo, kupona polepole — WHO ICPS harm classification
- `witnesses_present` — Shahidi waliopo: Names/roles of staff or family present
- `medical_records_available` — Kumbukumbu za kimatibabu zinapatikana?: Yes/No; critical for clinical review

**If issue_type = Billing / Overcharge / Insurance Claim:**
Also collect:
- `invoice_number` — Nambari ya ankara: For accounts reconciliation
- `amount_charged_tzs` — Kiasi kilichotozwa (TZS)
- `amount_expected_tzs` — Kiasi kilichotarajiwa (TZS)
- `nhif_claim_reference` — Nambari ya madai ya NHIF: Required for NHIF dispute resolution
- `payment_receipt_available` — Je, risiti ya malipo inapatikana?: For evidence

**If issue_type = Drug / Medicine Problem (shortage, wrong drug, expired):**
Also collect:
- `drug_name_generic` — Jina la dawa (la kawaida): Required by TFDA for adverse drug reaction reporting
- `drug_batch_number` — Nambari ya kundi la dawa: Critical for TFDA recall investigations
- `date_dispensed` — Tarehe ya kutoa dawa: For batch traceability
- `adverse_effect_experienced` — Athari mbaya iliyoonekana: TFDA pharmacovigilance reporting requirement

**If issue_type = Emergency / Delayed Treatment:**
Also collect:
- `arrival_time` — Saa ya kuwasili: For triage response time measurement
- `first_seen_by_clinician_time` — Saa ya kuonwa na daktari kwa mara ya kwanza: WHO patient safety standard
- `triage_category_assigned` — Kiwango cha dharura kilichopewa: Red/Yellow/Green

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| HC-01 | clinical_negligence | Wrong diagnosis, wrong treatment, surgical error, missed diagnosis |
| HC-02 | medication_error | Wrong drug, wrong dose, expired medicine, drug interaction |
| HC-03 | billing_overcharge | Incorrect bill, unauthorized charge, NHIF claim dispute |
| HC-04 | delayed_treatment | Long waiting time, delayed emergency response, missed appointment |
| HC-05 | staff_conduct | Rude, abusive, or unprofessional behavior by staff |
| HC-06 | equipment_failure | Malfunctioning diagnostic or treatment equipment |
| HC-07 | hygiene_sanitation | Dirty wards, unclean toilets, poor infection control |
| HC-08 | drug_shortage | Medicine out of stock in hospital or dispensary |
| HC-09 | unauthorized_procedure | Procedure performed without informed consent |
| HC-10 | privacy_breach | Patient information disclosed without consent |
| HC-11 | referral_failure | Referral letter not provided, referral not actioned |
| HC-12 | maternity_complication | Negligence during delivery, newborn harm, maternal injury |
| HC-13 | death_related | Unexpected or unexplained death; post-death grievance |
| HC-14 | discrimination | Patient treated differently based on ability to pay, tribe, gender |
| HC-15 | record_error | Wrong information in patient records; lost records |
| HC-16 | infection_acquired | Hospital-acquired infection (HAI) during stay |
| HC-17 | diagnostic_error | Incorrect lab result, misread X-ray, wrong scan interpretation |

### Resolution Standards for This Industry

- **Facility level:** Patient complaints must be acknowledged within 48 hours; resolved or substantively responded to within 21 days per MOHCDGEC Patient Charter 2019.
- **Clinical negligence:** Requires medical review board investigation. Timeline: 30–60 days. Death cases require coroner involvement.
- **NHIF billing disputes:** NHIF has a dedicated disputes resolution mechanism; must be lodged within 90 days of the claim date.
- **TFDA (drug-related):** Adverse drug reaction reports submitted to TFDA within 15 days of detection; serious reactions within 24 hours.
- **Required documentation for escalation:** Patient file number, date of incident, clinician involved, invoice (if billing), NHIF number (if insured).

### Escalation Triggers

- `issue_type = clinical_negligence` AND `outcome_to_patient` includes death or permanent disability — Immediate escalation to MOHCDGEC Regional Medical Officer and facility CMO
- `issue_type = maternity_complication` AND maternal or neonatal death — Mandatory maternal death review; escalate to MOHCDGEC within 24 hours
- `issue_type = medication_error` AND adverse_effect_experienced is severe — TFDA pharmacovigilance report within 24 hours
- `issue_type = unauthorized_procedure` — Patient rights violation; escalate to MOHCDGEC Patient Rights Unit
- `issue_type = infection_acquired` AND multiple patients affected — Outbreak protocol; escalate to facility Infection Control Committee and MOHCDGEC Disease Surveillance
- `issue_type = discrimination` based on inability to pay — Emergency departments cannot refuse life-saving treatment; legal escalation required

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | Patient Charter supports anonymous suggestions |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up |
| department_targeted | Idara inayohusika | Yes | Routes to correct improvement team |
| suggestion_category | Kategoria ya mapendekezo | Yes | For routing and analysis |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content |
| patient_or_visitor | Mgonjwa / Mgeni / Mfanyakazi | Recommended | Context shapes the suggestion |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| HS-01 | waiting_time_reduction | Kupunguza muda wa kusubiri |
| HS-02 | cleanliness_hygiene | Usafi wa wodi na vyoo |
| HS-03 | staff_friendliness | Ukarimu wa wafanyakazi |
| HS-04 | equipment_upgrade | Kuboresha vifaa vya matibabu |
| HS-05 | drug_availability | Upatikanaji wa dawa |
| HS-06 | billing_transparency | Uwazi wa bili |
| HS-07 | appointment_system | Mfumo wa miadi |
| HS-08 | accessibility_disability | Upatikanaji kwa walemavu |
| HS-09 | digital_services | Huduma za kidijitali (online booking) |
| HS-10 | food_nutrition | Ubora wa chakula cha wagonjwa |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | For call tracking and security |
| patient_id_or_name | Nambari ya mgonjwa au jina | Conditional | Required for patient-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct information source |
| urgency | Kiwango cha haraka | Yes | Standard / Dharura |
| preferred_response_format | Njia unayotaka jibu | Yes | SMS / Simu / WhatsApp |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| appointment_booking | Kupanga miadi | department_targeted, preferred_date |
| test_results | Matokeo ya kipimo | patient_id_or_name, test_type |
| drug_availability | Upatikanaji wa dawa | drug_name_generic |
| nhif_coverage | Dawa / huduma zinazofunikwa na NHIF | nhif_membership_number |
| visiting_hours | Saa za kutembelea | ward_name |
| referral_status | Hali ya rufaa | referral_number |
| bill_explanation | Maelezo ya ankara | invoice_number |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For staff recognition |
| clinician_or_staff_name | Jina la daktari / mfanyakazi aliyepongezwa | Recommended | Enables staff reward programs |
| department | Idara | Yes | Routes to correct manager |
| date_of_interaction | Tarehe ya huduma | Recommended | For performance record correlation |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Uponyaji mzuri / Uangalifu / Upole / Kasi ya huduma |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | JCI QPS standard; patient satisfaction measurement |
| free_text_commendation | Maneno ya pongezi | Optional | Captures narrative detail |

---

## AI Conversation Guidance for This Industry

- **Lead with patient identification, not the complaint.** Ask "Je, unalalamikia huduma uliyopata wewe mwenyewe au kwa niaba ya mtu mwingine?" before diving into the problem — this establishes legal standing and whether a patient file number is needed.
- **Collect the date of incident early.** Healthcare complaints are time-sensitive for both clinical review and regulatory reporting. Ask "Tukio hili lilitokea lini hasa — tarehe na saa ikiwezekana?"
- **For billing complaints, ask for the invoice number before the amount.** The invoice number allows the accounts team to pull the full record immediately.
- **Never diagnose or offer medical opinions.** If the complainant describes symptoms or asks whether treatment was correct, redirect: "Hilo ni swali la kimatibabu ambalo linahitaji daktari kulichunguza — ndiyo maana tunalifikisha kwa timu ya matibabu."
- **For negligence or death complaints, express empathy first.** These are emotionally charged; acknowledge before collecting data: "Tunakusikia na tunakuelewa hali hii ni ngumu sana. Tutasaidia kuhakikisha tatizo hili linashughulikiwa ipasavyo."
- **Collect NHIF number only for billing complaints.** For clinical or conduct complaints, NHIF is irrelevant and asking for it adds unnecessary friction.
- **For drug-related complaints, get the batch number if the packaging is available.** It is critical for TFDA traceability and recall decisions.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Patient name | "Jina kamili la mgonjwa anayehusika ni nani?" |
| File/Patient ID | "Je, una nambari ya faili au nambari ya mgonjwa? Inaweza kuonekana kwenye kadi ya hospitali." |
| Department | "Tatizo lilitokea katika idara gani — OPD, wodi, maabara, dharura, au nyingine?" |
| Date of incident | "Hii ilitokea lini hasa — tarehe na saa ukijua?" |
| Clinician name | "Je, unajua jina la daktari au muuguzi aliyehusika?" |
| NHIF number | "Kama mgonjwa ana bima ya NHIF, tunaweza kupata nambari ya uanachama?" |
| Desired outcome | "Unataka nini kutokea — uchunguzi, msamaha, kurudishiwa pesa, au kitu kingine?" |
| Contact preference | "Ningependa kukusiliana nawe — unapendelea SMS, simu, au WhatsApp?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | clinical_negligence | Create priority incident report; route to CMO and Facility Medical Review Board; acknowledge within 24 hours |
| issue_type | maternity_complication AND maternal/neonatal death | Trigger mandatory maternal death review; notify MOHCDGEC Regional Medical Officer within 24 hours |
| issue_type | medication_error AND adverse_effect_experienced = severe | Submit TFDA pharmacovigilance report within 24 hours; escalate to pharmacy director |
| issue_type | billing_overcharge AND nhif_claim involved | Route to NHIF liaison officer; open NHIF dispute file; advise 90-day lodgement window |
| issue_type | unauthorized_procedure | Escalate to MOHCDGEC Patient Rights Unit; inform patient of right to independent medical review |
| issue_type | infection_acquired AND multiple patients | Activate infection control protocol; notify facility IPC committee and MOHCDGEC surveillance unit |
| issue_type | drug_shortage AND life-saving medicine | Priority alert to facility pharmacist and MSD supply chain; escalate if stock unavailable within 24 hours |
| desired_outcome | Refund AND nhif involved | Route to both facility accounts and NHIF dispute resolution desk |
| issue_type | death_related | Assign most senior complaint officer; family liaison officer to be contacted within 2 hours |
| overall_satisfaction_rating | 5 AND specific clinician named | Forward commendation to HR for staff recognition program |

---

*Sources: MOHCDGEC Patient Charter 2019, Tanzania Health Sector Strategic Plan V (2021–2026), TFDA Act Cap. 219, NHIF Act Cap. 395, ISO 10002:2018, WHO ICPS 2009, WHO Patient Safety Curriculum Guide 2011, JCI Accreditation Standards 7th Edition*
